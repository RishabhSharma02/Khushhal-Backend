# Khushhal Backend

Async FastAPI + PostgreSQL service backing the Khushhal Flutter app.
Authentication is Firebase Phone OTP (verified server-side via Firebase
Admin SDK); insights are computed by the trained NABARD risk pipeline
bundled under `app/ml/artifacts/`.

## Local development

**Requirements:** Python 3.11+, PostgreSQL 15+, `libomp` (macOS-only,
needed by LightGBM: `brew install libomp`).

```bash
cd Khushhal-Backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

# Config
cp .env.example .env
# Point DATABASE_URL at a local Postgres and (optionally) drop a Firebase
# Admin JSON into FIREBASE_CREDENTIALS_JSON. Leave the latter blank in dev
# and use `X-Debug-Firebase-Uid: <any-string>` on requests — the backend
# accepts that header when DEV_TOOLS_ENABLED=true.

# Schema
.venv/bin/alembic upgrade head

# Run
.venv/bin/uvicorn app.main:app --reload
# Open http://localhost:8000/docs
```

### Environment

| Var | Default | Notes |
|-----|---------|-------|
| `ENV` | `dev` | `dev` / `staging` / `prod` |
| `DEV_TOOLS_ENABLED` | `false` | Enables `X-Debug-Firebase-Uid` header shim + `POST /insights/refresh` |
| `DATABASE_URL` | `postgresql+asyncpg://khushhal:khushhal@localhost:5432/khushhal` | Async DSN — must use `+asyncpg` |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated |
| `FIREBASE_CREDENTIALS_JSON` | empty | Full JSON of the service account (single line) |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

## Architecture

Modular monolith, async-first:

```
FastAPI (async def)  →  SQLAlchemy 2.x AsyncSession  →  asyncpg  →  PostgreSQL
                    ↘  Firebase Admin SDK (token verify)
                    ↘  InsightsService  →  ML pipeline (sklearn/LightGBM, thread-pooled)
                    ↘  APScheduler (monthly stamp cron)
```

- Route handlers are thin; business logic in `services/`; SQL in `repositories/`.
- ML inference is CPU-bound and called via `asyncio.to_thread`.
- All tables use BIGINT identity PKs, `creation_date/created_by/updation_date/updated_by`, and soft-delete via a `status` enum (`active | inactive | deleted`).
- Errors are always `{"error": {"code", "message", "details"?}}`.
- Every response echoes an `X-Request-ID` header (accepted from the caller when present).
- Rate limits apply per-IP in prod (10/min on `/auth/session`, 60/min on entry writes, 20/min on batch sync, 10/min on dev refresh).

## Alembic

```bash
# apply latest
.venv/bin/alembic upgrade head

# create a new revision (autogenerate against current models)
.venv/bin/alembic revision --autogenerate -m "add X"

# roll back one step
.venv/bin/alembic downgrade -1
```

The migrations under `alembic/versions/` are hand-written to keep enums
and audit columns consistent — prefer editing them by hand for new tables.

## ML pipeline

Artifacts under `app/ml/artifacts/`:

- `combined_model.pkl` — LightGBM 6-month cash-flow regression
- `band_classifier_extended.joblib` — RandomForest green/amber/red classifier
- `risk_action_framework.json` — sector × band × driver action library
- `sector_templates.json` — per-sector medians derived from the training
  CSV so the 280 MB CSV never ships in the container

To retrain, re-run `pipeline/run_full_pipeline.py` and re-generate
`sector_templates.json` (see `plan.md` for the one-liner).

## Monthly stamp job

Runs automatically at `00:05 UTC on the 1st` via APScheduler. Manual:

```bash
.venv/bin/python -m app.jobs.stamp_monthly            # today's first-of-month
.venv/bin/python -m app.jobs.stamp_monthly 2026-08-01 # explicit date
```

Idempotent — safe to re-run. Dev-only convenience: `POST /api/v1/businesses/{id}/insights/refresh` scores one business synchronously.

## Deploy (Railway)

`Procfile` + `railway.json` are in the repo. Railpack builds the image;
because the image installs LightGBM you may need to pin a base image with
`libomp` — Railpack currently bundles `libgomp1`. If a build fails with
`OSError: dlopen(...libomp.dylib)`, switch to a Dockerfile:

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
```

### Env vars to set in Railway

`ENV=prod`, `DEV_TOOLS_ENABLED=false`, `DATABASE_URL=<railway-pg>`,
`FIREBASE_CREDENTIALS_JSON=<full-json>`, `CORS_ORIGINS=<app-origins>`,
`LOG_LEVEL=INFO`.

## Backup + read-replica readiness

- Postgres backups: schedule daily `pg_dump` (Railway plugin or an external
  cron). Test the restore path quarterly.
- The app uses `pool_pre_ping=True` and a modest pool (10 + 20 overflow) —
  fine for a single instance. Scaling horizontally is trivial because the
  service is stateless; APScheduler in each pod would fire the monthly job
  N times per stamp, so promote scheduling to a single dedicated worker
  when you scale (`SCHEDULER_ENABLED=false` on the web pods, `true` on the
  worker).
- Read replicas: `DATABASE_URL_RO` is not implemented today — when needed,
  swap `SessionLocal` for two factories (`primary`, `read_only`) and route
  GET endpoints through the read-only factory.

## Testing

Tests under `tests/` are not populated yet — the project convention is to
add integration tests with pytest-asyncio + testcontainers when specific
behaviour needs to be pinned down.
