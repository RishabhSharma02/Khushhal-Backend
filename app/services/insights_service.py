
import asyncio
import calendar
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.base import RowStatus
from app.ml import features as ml_features
from app.ml import pipeline as ml_pipeline
from app.ml.hindi_labels import hindi_for
from app.models.business import Business
from app.models.forecast import Forecast
from app.models.health_score import HealthScore, RiskLevel, ScoreBand
from app.models.risk_alert import (
    AlertKind,
    AlertSeverity,
    PlanAction,
    PlanActionRole,
    RiskAlert,
)
from app.models.user import User
from app.repositories import insights as insights_repo

log = get_logger(__name__)


_BAND_TO_RISK = {
    "green": RiskLevel.low,
    "amber": RiskLevel.medium,
    "red": RiskLevel.high,
}

_DRIVER_TO_KIND = {
    "liquidity_debt_stress": AlertKind.liquidity_debt_stress,
    "climate_stress_deficit": AlertKind.climate_deficit,
    "climate_stress_excess": AlertKind.climate_excess,
    "market_stress": AlertKind.market_stress,
    "new_business": AlertKind.new_business,
    "band_guidance": AlertKind.band_guidance,
    "savings_low": AlertKind.savings_low,
}


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


def _next_first_of_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


async def _run_score(ctx: ml_pipeline.FeatureContext) -> ml_pipeline.ScoreResult:
    return await asyncio.to_thread(ml_pipeline.score, ctx)


async def stamp_month(
    db: AsyncSession,
    *,
    business: Business,
    user: User,
    as_on: date,
) -> HealthScore:
    """Build features, run the ML pipeline, and persist HealthScore /
    Forecast / RiskAlert / PlanAction rows for this business × month.

    Idempotent on `(business_id, as_on)` — safe to re-run.
    """
    as_on = _first_of_month(as_on)

    # Trailing 6 months' entries feed the feature builder.
    since = _first_of_month(as_on - timedelta(days=190))
    snapshot = await insights_repo.latest_snapshot(db, business.id)
    entries = await insights_repo.trailing_entries(db, business.id, since=since)

    ctx = ml_features.build_feature_context(
        business=business, user=user, snapshot=snapshot, entries=entries, as_on=as_on,
    )

    try:
        result = await _run_score(ctx)
    except Exception as e:
        log.exception("insights_scoring_failed", business_id=business.id, err=str(e))
        raise

    score = ml_features.score_from_probs(result.p_green, result.p_amber, result.p_red)
    risk = _BAND_TO_RISK[result.band]
    band_enum = ScoreBand(result.band)

    # Compute delta vs previous month's score if present.
    prev_month = as_on - timedelta(days=1)
    prev = await insights_repo.health_at(db, business.id, _first_of_month(prev_month))
    delta = (score - prev.score) if prev is not None else None

    # ---- HealthScore (upsert on (business_id, as_on)) ----
    values = dict(
        business_id=business.id,
        as_on=as_on,
        next_update=_next_first_of_month(as_on),
        score=score,
        risk=risk,
        delta=delta,
        days_written=ctx.days_written,
        days_in_month=ctx.days_in_month,
        band=band_enum,
        p_green=round(result.p_green, 3),
        p_amber=round(result.p_amber, 3),
        p_red=round(result.p_red, 3),
        model_version=result.model_version,
        created_by=user.id,
        updated_by=user.id,
    )
    stmt = pg_insert(HealthScore.__table__).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["business_id", "as_on"],
        set_={k: values[k] for k in ("score", "risk", "delta", "days_written", "days_in_month",
                                     "band", "p_green", "p_amber", "p_red", "model_version",
                                     "next_update", "updated_by")},
    )
    await db.execute(stmt)

    # ---- Forecast (upsert per horizon) ----
    max_abs = max((abs(v) for v in result.forecast), default=1.0) or 1.0
    for horizon, cf in enumerate(result.forecast, start=1):
        level = min(max(abs(cf) / max_abs, 0.0), 1.0)
        row = dict(
            business_id=business.id,
            as_on=as_on,
            horizon=horizon,
            cf_pred=round(cf, 2),
            in_level=round(level if cf > 0 else 0.0, 3),
            out_level=round(level if cf < 0 else 0.0, 3),
            is_risk_month=cf < 0,
            created_by=user.id,
            updated_by=user.id,
        )
        fstmt = pg_insert(Forecast.__table__).values(row)
        fstmt = fstmt.on_conflict_do_update(
            index_elements=["business_id", "as_on", "horizon"],
            set_={k: row[k] for k in ("cf_pred", "in_level", "out_level", "is_risk_month", "updated_by")},
        )
        await db.execute(fstmt)

    # ---- RiskAlerts + PlanActions ----
    # Always attach the sector × band playbook so green/amber/red all expose
    # actionables via GET /alerts — not only when a driver overlay fires.
    # Overlay-driven alerts (liquidity, climate, market, new-business) are
    # appended on top with their own kinds.
    overlays = list(result.overlays)
    if result.owner_actions or result.field_officer_actions:
        overlays.insert(
            0,
            ml_pipeline.Overlay(
                driver="band_guidance",
                owner_action=list(result.owner_actions),
                field_officer_action=list(result.field_officer_actions),
            ),
        )

    for overlay in overlays:
        kind = _DRIVER_TO_KIND.get(overlay.driver, AlertKind.savings_low)
        severity = AlertSeverity.urgent if result.band == "red" else AlertSeverity.info

        alert_values = dict(
            business_id=business.id,
            as_on=as_on,
            kind=kind,
            severity=severity,
            driver=overlay.driver,
            has_plan=bool(overlay.owner_action or overlay.field_officer_action),
            raised_on=as_on,
            created_by=user.id,
            updated_by=user.id,
        )
        astmt = pg_insert(RiskAlert.__table__).values(alert_values)
        astmt = astmt.on_conflict_do_update(
            index_elements=["business_id", "as_on", "kind"],
            set_={"severity": severity, "driver": overlay.driver,
                  "has_plan": alert_values["has_plan"], "updated_by": user.id},
        ).returning(RiskAlert.__table__.c.id)
        alert_id = (await db.execute(astmt)).scalar_one()

        # Replace plan actions for this alert (simplest correct behavior for
        # the batch stamp — the framework's action list is deterministic per
        # sector×band so wholesale replace matches what the ML output says).
        await db.execute(
            PlanAction.__table__.delete().where(PlanAction.alert_id == alert_id)
        )
        rows: list[dict] = []
        for i, text in enumerate(overlay.owner_action):
            rows.append({
                "alert_id": alert_id, "role": PlanActionRole.owner,
                "ordinal": i, "label_en": text, "label_hi": hindi_for(text),
                "created_by": user.id, "updated_by": user.id,
            })
        for i, text in enumerate(overlay.field_officer_action):
            rows.append({
                "alert_id": alert_id, "role": PlanActionRole.field_officer,
                "ordinal": i, "label_en": text, "label_hi": hindi_for(text),
                "created_by": user.id, "updated_by": user.id,
            })
        if rows:
            await db.execute(pg_insert(PlanAction.__table__).values(rows))

    # Close out earlier editions. `insights_repo.active_alerts` filters on
    # `resolved_at IS NULL` but not on `as_on`, so without this every month
    # ever stamped keeps piling warnings next to the current forecast.
    await db.execute(
        RiskAlert.__table__.update()
        .where(
            RiskAlert.__table__.c.business_id == business.id,
            RiskAlert.__table__.c.as_on < as_on,
            RiskAlert.__table__.c.resolved_at.is_(None),
        )
        .values(resolved_at=datetime.now(timezone.utc), updated_by=user.id)
    )

    await db.commit()

    stored = await insights_repo.health_at(db, business.id, as_on)
    assert stored is not None
    return stored


async def toggle_plan_action(
    db: AsyncSession, *, action_id: int, done: bool, current: User
) -> PlanAction:
    action = await insights_repo.plan_action(db, action_id)
    if action is None:
        raise NotFoundError("Plan action not found")
    # Enforce ownership via the parent alert → business chain.
    from app.models.business import Business as _B
    row = await db.execute(
        select(_B.user_id).join(RiskAlert, RiskAlert.business_id == _B.id).where(RiskAlert.id == action.alert_id)
    )
    owner_id = row.scalar_one_or_none()
    if owner_id != current.id:
        raise NotFoundError("Plan action not found")

    action.done = done
    action.done_at = datetime.now(timezone.utc) if done else None
    action.updated_by = current.id
    await db.commit()
    await db.refresh(action)
    return action
