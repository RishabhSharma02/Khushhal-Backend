# Khushhal — Backend + Frontend Integration Plan

## Context

Khushhal is a bilingual (Hindi/English), offline-first Flutter app that helps rural micro-business owners (dairy, poultry, food processing, handicrafts, rural retail — SHGs / FPOs / sole owners) track cash flow and get a monthly financial health score with a 6-month forecast and actionable risk alerts.

Today the Flutter app is UI-complete for the core journeys but everything reads from a hardcoded `DemoData` class; there is no HTTP client, no auth screens, and no persistence. A separate `pipeline/` folder already contains a fully trained NABARD risk pipeline (LightGBM cash-flow regression → RandomForest band classifier → JSON-driven action engine) that maps 1:1 onto the app's Home health card, Forecast screen, and Alerts/Plan screens. The `Khushhal-Backend/` folder is an empty FastAPI skeleton on Railway with only `/health`.

Goal: build a production-shaped FastAPI + PostgreSQL backend that (a) authenticates real users via Firebase Phone OTP, (b) persists businesses + ledger entries with an offline-sync path, (c) exposes the trained ML pipeline as the insights service, and (d) wire the Flutter app to it via a repository layer replacing `DemoData`, plus new login/OTP screens.

## Locked decisions

- **Auth:** Firebase Phone OTP in Flutter (real screens 1f–1g3) + Firebase Admin SDK verification in backend. No custom backend JWT layer — Firebase ID token is the session.
- **ML external features:** neutral defaults for v1 (`rain_dev_yr=0`, `tot_chg_3m=0`); derive `savings_months`, `debt_service_cov`, `has_loan`, `is_new_business`, `years_in_operation` from user data. Real climate/market feeds are Phase 3.
- **Compute strategy:** monthly batch stamps `HealthScore`/`Forecast`/`Alert` rows per business; a dev-gated `POST /insights/{businessId}/refresh` endpoint forces recompute for testing.
- **ML packaging:** ship `.joblib`/`.pkl` + `risk_action_framework.json` + `risk_actions.py` inside the backend image at `app/ml/artifacts/`; git-ignore the 280 MB training CSV (kept in `pipeline/` for retraining only). Add pandas / numpy / scikit-learn / lightgbm to `requirements.txt`.
- **Delivery:** three sliced phases (below).

## Architecture (modular monolith, async-first)

```
FastAPI (async def) → SQLAlchemy 2.x AsyncSession → asyncpg → PostgreSQL
                    ↘ Firebase Admin SDK (token verify)
                    ↘ InsightsService → ML pipeline (sync, thread-pooled)
                    ↘ APScheduler (monthly batch stamp)
```

- Route handlers are thin; business logic lives in services; SQL lives in repositories.
- ML inference is CPU-bound sync code (LightGBM/sklearn) — call via `run_in_executor` from async endpoints so the event loop isn't blocked. Load model artifacts once at app startup (module-level singleton wrapped in a class).
- Config via `pydantic-settings` reading `.env`. `.env.example` committed.

### Project structure (`Khushhal-Backend/`)

```
app/
  main.py                  # FastAPI app, lifespan (load ML, init scheduler), CORS, middleware
  core/
    config.py              # Settings (DATABASE_URL, FIREBASE_CREDENTIALS_JSON, ENV, DEV_TOOLS_ENABLED)
    security.py            # Firebase token verification dependency
    logging.py             # structlog config
    exceptions.py          # centralized handlers → RFC7807-style JSON errors
  db/
    session.py             # AsyncEngine + AsyncSession factory
    base.py                # DeclarativeBase + AuditMixin (id BIGINT PK, creation_date, created_by,
                           #   updation_date, updated_by) + SoftDeleteMixin (status enum)
  models/                  # SQLAlchemy 2.x models
    user.py, business.py, ledger_entry.py, monthly_snapshot.py,
    health_score.py, forecast.py, risk_alert.py, plan_action.py, sync_event.py
  schemas/                 # Pydantic v2
    auth.py, user.py, business.py, ledger.py, insights.py, common.py
  repositories/            # data access, one file per aggregate
    users.py, businesses.py, ledger_entries.py, insights.py
  services/                # business logic
    auth_service.py        # find_or_create_user_from_firebase(uid, phone)
    business_service.py
    ledger_service.py      # single POST + batch sync w/ client_entry_id idempotency
    insights_service.py    # feature build, model call, band mapping, alert dedup
  ml/
    artifacts/             # combined_model.pkl, band_classifier_extended.joblib,
                           # risk_action_framework.json (copied from pipeline/)
    risk_actions.py        # copied verbatim from pipeline/
    pipeline.py            # thin wrapper: load_models(), score_business(context) -> dict
    features.py            # build_feature_row(business, entries) — neutral defaults for climate/market
  jobs/
    scheduler.py           # APScheduler AsyncIOScheduler, monthly cron 00:05 on day 1
    stamp_monthly.py       # job: for each active business → build features → score → persist
  api/
    v1/
      __init__.py          # APIRouter(prefix="/api/v1")
      auth.py              # POST /auth/session  (exchange Firebase ID token → me payload)
      users.py             # GET/PATCH /me
      businesses.py        # CRUD + list
      ledger.py            # POST /entries, POST /entries/sync (batch), GET /entries, PATCH /entries/{id}
      insights.py          # GET /health/{bizId}, GET /forecast/{bizId}, GET /alerts/{bizId},
                           # PATCH /alerts/{id}/actions/{actionId}, POST /insights/{bizId}/refresh (dev-gated)
      profile.py           # PATCH /me/savings-loan
alembic/                   # migrations
tests/                     # pytest-asyncio; testcontainers-postgres
  conftest.py              # spins Postgres, applies migrations, seeds Firebase mock
  test_auth.py, test_ledger.py, test_insights.py
.env.example
requirements.txt           # add: sqlalchemy, asyncpg, alembic, pydantic-settings,
                           #      firebase-admin, apscheduler, structlog,
                           #      pandas, numpy, scikit-learn, lightgbm, joblib
requirements-dev.txt       # add: pytest-asyncio, testcontainers[postgres], ruff, mypy
```

## PostgreSQL schema (ERD summary)

### Shared conventions (apply to every table, no exceptions)

- **Primary key:** `id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY` (no UUIDs anywhere).
- **Foreign keys** to other tables are `BIGINT`.
- **Audit columns on every table:**
  - `creation_date TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `created_by BIGINT NULL REFERENCES users(id)` — nullable for system-inserted rows (migrations/seed) and for the `users` row itself on self-signup.
  - `updation_date TIMESTAMPTZ NOT NULL DEFAULT now()` — set on write via SQLAlchemy `onupdate=func.now()` (fallback: `BEFORE UPDATE` trigger).
  - `updated_by BIGINT NULL REFERENCES users(id)`.
- **Soft delete via `status` column** (no `deleted_at`). Column type: `status_enum` with values `active | inactive | deleted`, `NOT NULL DEFAULT 'active'`. All reads filter `status <> 'deleted'` unless a route explicitly opts in via `?include_deleted=true` (admin/debug only). Hard `DELETE` is not used for user-owned aggregates.
- **Implementation:** `app/db/base.py` provides `AuditMixin` + `SoftDeleteMixin`; every model inherits both. `created_by` / `updated_by` are populated in the repository layer from `current_user.id` threaded down from the request.
- Enums are Postgres `CREATE TYPE` — mapped as SQLAlchemy `ENUM(..., create_type=True)`.

Column lists below **omit** the shared audit + status columns for brevity — assume every table has `id BIGINT PK`, `creation_date`, `created_by`, `updation_date`, `updated_by`, `status`.

### Tables

- **users** — `firebase_uid` UNIQUE NOT NULL, `phone_e164` UNIQUE NOT NULL, `name` NULL, `language` `lang_enum` DEFAULT 'hi', `state`/`district`/`village` NULL, `notifications_enabled` BOOL DEFAULT true.
- **businesses** — `user_id` FK→users, `name`, `segment` `segment_enum` (shg|fpo|own), `sector` `sector_enum` (dairy|poultry|food_processing|handicrafts|rural_retail|other), `tenure` `tenure_enum` (under_1|1_to_3|3_to_10|10_plus), `staff_count` INT CHECK ≥1, `is_new_business` BOOL, `years_in_operation` INT.
  - Index: `(user_id) WHERE status <> 'deleted'`.
- **monthly_snapshots** — one-off setup baseline. `business_id` FK, `month` DATE (1st of month), `money_in` `money`, `money_out` `money`, `loan_emi` `money`, `savings` `money`, `basis` `basis_enum` (rough|records). UNIQUE (`business_id`,`month`) WHERE `status <> 'deleted'`.
- **ledger_entries** — `business_id` FK, `user_id` FK (denorm for auth checks), `kind` (`in`|`out`), `amount_inr` INT CHECK >0, `category` `category_enum`, `recorded_at` TIMESTAMPTZ, `source` (`manual`|`voice`), `client_entry_id` UUID (idempotency key from Flutter — the ONLY UUID in the schema, purely for offline dedup), `synced_at` TIMESTAMPTZ.
  - Indexes: `(business_id, recorded_at DESC)`, UNIQUE `(business_id, client_entry_id)`.
- **health_scores** — `business_id` FK, `as_on` DATE, `next_update` DATE, `score` SMALLINT CHECK 0..100, `risk` `risk_enum` (low|medium|high), `delta` SMALLINT NULL, `days_written` SMALLINT, `days_in_month` SMALLINT, `band` `band_enum` (green|amber|red), `p_green`/`p_amber`/`p_red` NUMERIC(4,3), `model_version` TEXT. UNIQUE (`business_id`,`as_on`).
- **forecasts** — `business_id` FK, `as_on` DATE, `horizon` SMALLINT (1..6), `cf_pred` NUMERIC(14,2), `in_level` NUMERIC(4,3), `out_level` NUMERIC(4,3), `is_risk_month` BOOL. UNIQUE (`business_id`,`as_on`,`horizon`).
- **risk_alerts** — `business_id` FK, `as_on` DATE, `kind` `alert_kind_enum` (savings_low|liquidity_debt_stress|climate_deficit|climate_excess|market_stress|new_business), `severity` (`urgent`|`info`), `driver` TEXT, `has_plan` BOOL, `raised_on` DATE, `resolved_at` TIMESTAMPTZ NULL. Index (`business_id`,`raised_on` DESC) partial WHERE `status <> 'deleted' AND resolved_at IS NULL`.
- **plan_actions** — `alert_id` FK ON DELETE CASCADE, `kind` TEXT (matches framework action text or slug), `label_en`/`label_hi` TEXT, `done` BOOL, `done_at` TIMESTAMPTZ.
- **sync_events** — audit only. `user_id`, `batch_size`, `accepted`, `duplicates`. (Still inherits shared columns; `status` typically stays `active`.)

**Note on `client_entry_id`:** this is deliberately UUID because the Flutter client generates it offline before the server assigns a `BIGINT id`. Server PKs remain BIGINT; the UUID is a dedup key only.

## Firebase auth flow

```
Flutter: firebase_auth verifyPhoneNumber → SMS code → signInWithCredential
       → user.getIdToken() → attach as `Authorization: Bearer <idToken>` on every request
Backend: dependency get_current_user()
       → firebase_admin.auth.verify_id_token(token) (async via to_thread)
       → extract uid + phone_number (verified)
       → users.find_or_create_by_firebase_uid(uid, phone)
       → return User row
```

- No backend-issued JWT. If we later need long-lived tokens (Firebase ID tokens expire hourly), Flutter's `firebaseAuth.idTokenChanges()` auto-refreshes; the client interceptor grabs the fresh token per request.
- `POST /api/v1/auth/session` is optional but recommended: it takes an ID token, upserts the user, returns `{ me: UserRead, is_new: bool }` so Flutter can route new users into setup vs existing users into home.
- Dev shim: when `ENV=dev` AND `DEV_TOOLS_ENABLED=true`, accept header `X-Debug-Firebase-Uid` to skip verification — for local backend testing before Flutter Firebase is wired.

## Authorization

- Every business/ledger/insight route depends on `get_current_user` + `require_business_owner(business_id)`.
- `require_business_owner` fetches the business, 404 if missing, 403 if `business.user_id != current_user.id`. Never leak existence.
- No admin roles in v1.

## API inventory (all under `/api/v1`, all `async def`)

| Method | Path | Purpose | Consumed by (Flutter) |
|---|---|---|---|
| POST | `/auth/session` | Verify Firebase ID token, upsert user, return `{ me, is_new }` | 1g3 verify success |
| GET | `/me` | Current user profile | Settings 1x, splash |
| PATCH | `/me` | Update name/language/location/notifications | 1x, LanguageSelectScreen |
| PATCH | `/me/savings-loan` | Update household savings + loan | SavingsLoanScreen 1t |
| POST | `/businesses` | Create business (setup wizard commit) | 1l/1m/1n final step |
| GET | `/businesses` | List user's businesses | HubStep 1j, Home boot |
| GET | `/businesses/{id}` | Business detail | Home 1o |
| PATCH | `/businesses/{id}` | Edit business | 1x businesses list |
| DELETE | `/businesses/{id}` | Soft-delete | 1x |
| POST | `/businesses/{id}/entries` | Create single ledger entry | AddEntryScreen 1p (online) |
| POST | `/businesses/{id}/entries/sync` | Idempotent batch upload (offline queue drain) | SyncScreen 1w, background sync |
| GET | `/businesses/{id}/entries` | Paginated history w/ filters `?kind=&category=&from=&to=&cursor=` | HistoryScreen 1v |
| PATCH | `/businesses/{id}/entries/{entryId}` | Edit entry | 1v long-press |
| GET | `/businesses/{id}/health` | Latest stamped score + prior for delta | Home 1o, 1o2, 1q2 |
| GET | `/businesses/{id}/forecast` | Latest 6-month forecast | ForecastScreen 1q |
| GET | `/businesses/{id}/alerts` | Active alerts (with `has_plan`) | AlertsScreen 1r |
| GET | `/businesses/{id}/alerts/{alertId}` | Alert detail + plan actions | AlertDetailScreen 1s |
| PATCH | `/businesses/{id}/alerts/{alertId}/actions/{actionId}` | Mark action done | 1s |
| POST | `/businesses/{id}/insights/refresh` | **Dev-gated** force recompute | testing only |

Responses use consistent envelope for lists: `{ items: [...], next_cursor: str|null }`. Errors: `{ error: { code, message, details? } }`.

## ML integration

- Copy `pipeline/combined_model.pkl`, `pipeline/band_classifier_extended.joblib`, `pipeline/risk_action_framework.json`, `pipeline/risk_actions.py` into `app/ml/`. Do not copy `final_coldstart_training.csv`.
- `app/ml/pipeline.py` exposes:
  - `load_models()` at startup → holds `regression`, `features_reg`, `band_model`, `band_features` in a module singleton.
  - `score_business(context: FeatureContext) -> ScoreResult` → runs Step 1 (6-month cf_pred), Step 2 (band + probs + engineered features `mean/std/slope/momentum/...` exactly as in `run_full_pipeline.py`), Step 3 (calls `risk_actions.get_actionables(sector, band, ctx)`).
- `app/ml/features.py::build_feature_row(business, entries, external_defaults)` derives the 30+ regression inputs from user data:
  - Cash-flow history: monthly net from `ledger_entries` for the trailing window.
  - `savings_months` = current savings / avg monthly outflow.
  - `debt_service_cov` = monthly net / EMI (NULL if no loan).
  - `has_loan`, `is_new_business`, `years_in_operation` from Business row.
  - Climate / market features → neutral defaults (`rain_dev_yr=0`, `tot_chg_3m=0`, etc.) with clear TODO markers for Phase 3.
- Insights service maps ML output to DB rows:
  - Band `green/amber/red` → risk `low/medium/high`.
  - Score = deterministic function of probabilities (e.g., `round(100*(1*p_green + 0.5*p_amber + 0*p_red))`).
  - `days_written` from actual entry days in current month.
  - Triggered overlays become `risk_alerts` rows (dedup on `(business_id, kind, as_on)`), plan actions inserted from overlay `owner_action` list, localized labels stored in `label_en/label_hi` (Hindi text seeded from the framework's action strings — English exists today; Hindi copy is a translation task tracked in Phase 3).

## Scheduler

- APScheduler `AsyncIOScheduler` started in FastAPI lifespan.
- Cron: `0 5 1 * *` — for every business with ≥1 entry in trailing 6 months, run `insights_service.stamp_month(business_id, as_on=first_of_month)`.
- Job idempotent (UNIQUE on `(business_id, as_on)`); safe to re-run.
- Dev refresh endpoint calls the same `stamp_month` function.

## Frontend integration plan (`Khushhal-Frontend/`)

- **Auth screens (new):** implement designs 1f (phone input) → 1g (OTP entry) → 1g2 (loading) → 1g3 (verified) using `firebase_core` + `firebase_auth`. Wire into router before existing Onboarding, but skip if `FirebaseAuth.instance.currentUser != null`.
- **HTTP layer (new):** add `dio` (interceptors + cancellation). Create `lib/core/network/api_client.dart`:
  - Base URL from `--dart-define=API_BASE_URL=...`.
  - Auth interceptor attaches `await user.getIdToken()` per request.
  - 401 → force `signOut()` and route to login.
  - Retry with exponential backoff on network errors (offline-first).
- **Types (new):** generate Dart models from FastAPI OpenAPI via `openapi-generator` (dio-next template) into `lib/core/api/`. Manual bloc/mapper code sits on top.
- **Repository layer (new):** replace `DemoData` reads with:
  - `AuthRepository`, `UserRepository`, `BusinessRepository`, `LedgerRepository`, `InsightsRepository`.
  - Each repo takes an offline cache (Hive or Isar; Hive recommended — smaller footprint) and the API client. Reads hit cache first, then network refresh; writes go to a local `outbox` box that the sync worker drains.
- **State management:** memory says use `flutter_bloc`. Current frontend uses `ChangeNotifier`/`AppSession`. In Phase 1 we introduce Bloc for the *new* auth + repository-backed features and leave the demo `AppSession` in place for screens not yet re-wired; migrate remaining screens incrementally. (Full rewrite is out of scope — the memory rule is about new code.)
- **Offline sync:** background service (`workmanager` on Android, `BGTaskScheduler` on iOS) plus manual "Sync now" on 1w. Sends the outbox to `/entries/sync` with `client_entry_id` = local UUID for idempotency. Pending entries render with `EntrySyncState.pending`.
- **Do not rewrite:** UI widgets, theme tokens, existing setup screens (1h–1n), Home/Forecast/Alert/History screens. They read from Bloc state fed by the repositories.

## Phased delivery

### Phase 1 — Foundations + core data (backend + Flutter)
Backend: config, `db/session`, base model, User + Business + LedgerEntry models, initial Alembic migration, `POST /auth/session`, `GET/PATCH /me`, businesses CRUD, ledger POST + `POST /entries/sync` + list, Firebase Admin verify dependency, structured logging, CORS, `.env.example`, testcontainers-based tests for auth + businesses + ledger idempotency.
Flutter: add `firebase_core` + `firebase_auth` + `dio` + `hive` + `flutter_bloc`, build screens 1f–1g3, `ApiClient` + interceptors, `AuthBloc`, `AuthRepository`, `BusinessRepository`, `LedgerRepository` w/ outbox, refactor SetupFlow's final commit + AddEntry + SyncScreen to hit backend.

### Phase 2 — Insights service
Backend: copy ML artifacts into `app/ml/`, `pipeline.py` + `features.py`, `InsightsService.stamp_month`, HealthScore/Forecast/RiskAlert/PlanAction models + migration, APScheduler monthly job, GET endpoints for health/forecast/alerts, dev-gated `/insights/refresh`. Backfill script that stamps historical months per business on first run.
Flutter: `InsightsRepository`, `HealthBloc`/`ForecastBloc`/`AlertsBloc`, wire Home 1o (+1o2 pending reveal), ForecastScreen 1q, MonthlyUpdate 1q2, AlertsScreen 1r, AlertDetail 1s to backend.

### Phase 3 — Reference data + hardening
Backend: location reference (states/districts/villages), mandi price cache, real climate feed integration (IMD/OpenWeather) replacing neutral defaults, rate limiting (slowapi), Sentry, request-id middleware, OpenAPI polish, backup + read-replica readiness docs.
Flutter: LocationStep 1h wired to `/locations/*`, SyncScreen 1w polish w/ real queue counts, Hindi translations for plan-action labels, error/empty state audit.

## Testing strategy

- **Unit:** services + feature-builder (`build_feature_row` with deterministic ledger inputs → assert feature vector).
- **API/integration:** pytest-asyncio + `testcontainers[postgres]` + FastAPI `AsyncClient`. Fake Firebase verify by monkeypatching `firebase_admin.auth.verify_id_token` in a fixture. Cover: auth handshake, business ownership, `/entries/sync` idempotency (duplicate `client_entry_id`), pagination cursors, dev-gate on `/insights/refresh`.
- **ML smoke:** load models on cold start, run one `score_business` on a synthetic business, assert schema of output and that Hindi/English fallback works.
- **No Flutter tests written** per memory rule.

## Critical files

- New (backend): everything under `Khushhal-Backend/app/**`, `alembic/**`, updated `main.py`, `requirements.txt`, `.env.example`, `tests/**`.
- Reused: `pipeline/risk_actions.py`, `pipeline/risk_action_framework.json`, `pipeline/combined_model.pkl`, `pipeline/band_classifier_extended.joblib` (copied into `Khushhal-Backend/app/ml/`).
- Modified (frontend): `Khushhal-Frontend/pubspec.yaml`, `lib/main.dart` (router + Firebase init + Bloc providers), `lib/app/session.dart` (progressively deprecated), new `lib/core/network/**`, `lib/core/api/**` (generated), `lib/features/auth/**`, `lib/features/*/data/**` repositories, minimal edits to existing screens to consume Bloc state.
- Unchanged: `Khushhal-Frontend/lib/l10n/**`, all pure-UI widgets, theme tokens.

## Risks & unknowns

- **Feature parity of ML input:** the model was trained on features derived from a specific NABARD synthetic dataset shape. Deriving them from a farmer's real (sparse) ledger will produce out-of-distribution inputs early on. Mitigation: neutral defaults for exogenous features, cold-start heuristic score for businesses with <30 days of data (fall back to setup baseline monthly snapshot), track `model_version` per stamped score so we can invalidate later.
- **LightGBM on Railway RAILPACK:** may need explicit `libomp` in the build image. If Railpack doesn't include it, pin a Docker base with `apt-get install libgomp1`.
- **Image size:** pandas + scikit-learn + lightgbm add ~200 MB. Acceptable; monitor Railway build cache.
- **Firebase project setup:** requires you to create the Firebase project, enable Phone Auth, generate a service account JSON, and provide `FIREBASE_CREDENTIALS_JSON` env var. Testing needs test phone numbers configured in Firebase console.
- **Bloc migration debt:** mixing Bloc for new code and ChangeNotifier for legacy `AppSession` is a temporary state that must be finished in Phase 3.

## Verification

**Phase 1 exit gate:**
1. `cd Khushhal-Backend && uvicorn app.main:app --reload` — `/api/v1/me` returns 401 without token; returns user JSON with a valid Firebase test ID token (or `X-Debug-Firebase-Uid` header in dev).
2. `pytest -q` inside `Khushhal-Backend/` — all tests green, testcontainers spins ephemeral Postgres.
3. `alembic upgrade head` then `alembic downgrade base` clean-round-trip.
4. In Flutter (`cd Khushhal-Frontend && flutter run --dart-define=API_BASE_URL=http://localhost:8000`): fresh install → phone → OTP → new-user path → SetupFlow → HubStep → business persists to Postgres (verify with `psql` `SELECT * FROM businesses`). AddEntry offline (airplane mode) queues in Hive; reconnect + SyncScreen → entries land in `ledger_entries` with idempotency (double-tap sync produces no dupes).

**Phase 2 exit gate:**
1. `POST /api/v1/businesses/{id}/insights/refresh` (dev token) produces rows in `health_scores`, `forecasts` (6), `risk_alerts` (0..N), `plan_actions`.
2. Scheduler dry-run via `python -m app.jobs.stamp_monthly --as-on 2026-08-01` stamps all eligible businesses; re-running is a no-op.
3. Home 1o shows non-demo score, ForecastScreen 1q shows bars matching `forecasts` table, AlertsScreen 1r matches `risk_alerts`, tapping alert on 1s toggles `plan_actions.done` via PATCH.

**Phase 3 exit gate:** Location dropdowns hit backend, real rainfall feed changes overlay firing between neutral-defaults vs real-data runs, rate limits enforced, README covers deploy + retrain workflow.
