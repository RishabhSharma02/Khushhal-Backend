
from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import RowStatus
from app.models.forecast import Forecast
from app.models.health_score import HealthScore
from app.models.ledger_entry import LedgerEntry
from app.models.monthly_snapshot import MonthlySnapshot
from app.models.risk_alert import PlanAction, RiskAlert


async def latest_health(db: AsyncSession, business_id: int) -> HealthScore | None:
    stmt = (
        select(HealthScore)
        .where(HealthScore.business_id == business_id, HealthScore.status != RowStatus.deleted)
        .order_by(HealthScore.as_on.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def health_at(db: AsyncSession, business_id: int, as_on: date) -> HealthScore | None:
    stmt = select(HealthScore).where(
        HealthScore.business_id == business_id,
        HealthScore.as_on == as_on,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def latest_forecast(db: AsyncSession, business_id: int) -> list[Forecast]:
    latest_stmt = (
        select(Forecast.as_on)
        .where(Forecast.business_id == business_id, Forecast.status != RowStatus.deleted)
        .order_by(Forecast.as_on.desc())
        .limit(1)
    )
    latest_month = (await db.execute(latest_stmt)).scalar_one_or_none()
    if latest_month is None:
        return []
    stmt = (
        select(Forecast)
        .where(
            Forecast.business_id == business_id,
            Forecast.as_on == latest_month,
            Forecast.status != RowStatus.deleted,
        )
        .order_by(Forecast.horizon.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def active_alerts(db: AsyncSession, business_id: int) -> list[RiskAlert]:
    stmt = (
        select(RiskAlert)
        .where(
            RiskAlert.business_id == business_id,
            RiskAlert.status != RowStatus.deleted,
            RiskAlert.resolved_at.is_(None),
        )
        .order_by(RiskAlert.raised_on.desc(), RiskAlert.id.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def alert_with_plan(db: AsyncSession, business_id: int, alert_id: int) -> RiskAlert | None:
    stmt = (
        select(RiskAlert)
        .options(selectinload(RiskAlert.plan_actions))
        .where(
            RiskAlert.id == alert_id,
            RiskAlert.business_id == business_id,
            RiskAlert.status != RowStatus.deleted,
        )
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def plan_action(db: AsyncSession, action_id: int) -> PlanAction | None:
    stmt = select(PlanAction).where(PlanAction.id == action_id, PlanAction.status != RowStatus.deleted)
    return (await db.execute(stmt)).scalar_one_or_none()


# Data the InsightsService needs to build a FeatureContext.

async def latest_snapshot(db: AsyncSession, business_id: int) -> MonthlySnapshot | None:
    stmt = (
        select(MonthlySnapshot)
        .where(MonthlySnapshot.business_id == business_id, MonthlySnapshot.status != RowStatus.deleted)
        .order_by(MonthlySnapshot.month.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def trailing_entries(db: AsyncSession, business_id: int, since: date) -> list[LedgerEntry]:
    stmt = (
        select(LedgerEntry)
        .where(
            LedgerEntry.business_id == business_id,
            LedgerEntry.status != RowStatus.deleted,
            LedgerEntry.recorded_at >= since,
        )
        .order_by(LedgerEntry.recorded_at.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def business_ids_with_recent_activity(db: AsyncSession, since: date) -> list[int]:
    """Businesses with ≥1 entry (or monthly snapshot) since `since` — the
    monthly stamp job iterates this list.
    """
    stmt = (
        select(LedgerEntry.business_id)
        .where(LedgerEntry.status != RowStatus.deleted, LedgerEntry.recorded_at >= since)
        .distinct()
    )
    from_entries = [r[0] for r in (await db.execute(stmt)).all()]

    stmt2 = (
        select(MonthlySnapshot.business_id)
        .where(MonthlySnapshot.status != RowStatus.deleted, MonthlySnapshot.month >= since)
        .distinct()
    )
    from_snapshots = [r[0] for r in (await db.execute(stmt2)).all()]

    return sorted(set(from_entries) | set(from_snapshots))
