"""Assembles the officer portal's `Enterprise` shape from the *existing*
customer-side tables (businesses, users, health_scores, forecasts,
risk_alerts, monthly_snapshots, ledger_entries — all read-only, via
app.repositories.insights / app.repositories.businesses) plus the two new
officer-only tables (assignments, contacts).

Not optimized for scale (one set of queries per business) — fine for the
officer counts in play today; the API shape here won't need to change if a
bulk/joined version replaces this later.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.business import Business
from app.models.health_score import HealthScore, ScoreBand
from app.models.monthly_snapshot import MonthlySnapshot
from app.models.risk_alert import RiskAlert
from app.models.user import User
from app.repositories import businesses as businesses_repo
from app.repositories import insights as insights_repo
from app.repositories.officer import assignments as assignments_repo
from app.repositories.officer import enterprises as enterprises_repo
from app.schemas.officer.enterprises import (
    CashFlowMonthRead,
    DataQualityRead,
    EnterpriseContactRead,
    EnterpriseFinancialsRead,
    EnterpriseRead,
)

_SECTOR_TO_PORTAL = {
    "dairy": "dairy",
    "poultry": "poultry",
    "food_processing": "foodProcessing",
    "handicrafts": "crafts",
    "rural_retail": "shop",
    "other": "other",
}
_SECTOR_ICON = {
    "dairy": "🐄",
    "poultry": "🐔",
    "food_processing": "🏭",
    "handicrafts": "🧵",
    "rural_retail": "🏪",
    "other": "🏢",
}
_BAND_TO_RISK_LEVEL = {
    ScoreBand.green: "healthy",
    ScoreBand.amber: "watch",
    ScoreBand.red: "atRisk",
}
_MONTH_LABELS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _month_label(d: date) -> str:
    return f"{_MONTH_LABELS[d.month - 1]} '{d.year % 100:02d}"


async def _require_assigned(db: AsyncSession, officer_id: int, business_id: int) -> None:
    if not await assignments_repo.is_assigned(db, officer_id, business_id):
        raise NotFoundError("Enterprise not found")


def _contact(business: Business, user: User, row) -> EnterpriseContactRead:
    if row is not None:
        return EnterpriseContactRead(
            name=row.name, role=row.role, phone=row.phone,
            language=row.language, best_time=row.best_time,
        )
    return EnterpriseContactRead(
        name=user.name or business.name,
        role="owner",
        phone=user.phone_e164,
        language="Hindi" if user.language.value == "hi" else "English",
        best_time="",
    )


def _sync_fields(last_entry: datetime | None, business: Business) -> tuple[int | None, int | None]:
    now = datetime.now(timezone.utc)
    if last_entry is None:
        stale_days = (now.date() - business.creation_date.date()).days
        return None, max(stale_days, 0)
    delta = now - last_entry
    if delta.days >= 7:
        return None, delta.days
    return int(delta.total_seconds() // 3600), None


async def _assemble(
    db: AsyncSession, business: Business, user: User,
) -> EnterpriseRead:
    health: HealthScore | None = await insights_repo.latest_health(db, business.id)
    alerts: list[RiskAlert] = await insights_repo.active_alerts(db, business.id)
    snapshot: MonthlySnapshot | None = await businesses_repo.latest_snapshot(db, business.id)
    contact_row = await enterprises_repo.get_contact(db, business.id)
    cash_on_hand = await enterprises_repo.cash_on_hand(db, business.id)
    last_entry = await enterprises_repo.last_entry_at(db, business.id)

    last_sync_hours_ago, stale_days = _sync_fields(last_entry, business)

    established_year = date.today().year - business.years_in_operation

    return EnterpriseRead(
        id=str(business.id),
        name=business.name,
        icon=_SECTOR_ICON.get(business.sector.value, "🏢"),
        segment=business.segment.value,
        sector=_SECTOR_TO_PORTAL.get(business.sector.value, "other"),
        village=user.village or "",
        established_year=established_year,
        staff_count=business.staff_count,
        member_since=business.creation_date.date(),
        contact=_contact(business, user, contact_row),
        health_score=health.score if health else 0,
        score_rising=bool(health and health.delta is not None and health.delta > 0),
        risk_level=_BAND_TO_RISK_LEVEL.get(health.band, "watch") if health else "watch",
        flag_summary=alerts[0].driver if alerts else None,
        financials=EnterpriseFinancialsRead(
            cash_on_hand_inr=cash_on_hand,
            month_net_inr=(snapshot.money_in - snapshot.money_out) if snapshot else 0,
            savings_inr=user.savings_inr,
            loan_left_inr=user.loan_inr,
            emi_inr=snapshot.loan_emi if snapshot else 0,
            # No missed-EMI signal exists yet anywhere upstream — placeholder
            # until one does (e.g. a ledger category or a dedicated column).
            emi_on_time=True,
        ),
        last_sync_hours_ago=last_sync_hours_ago,
        stale_days=stale_days,
    )


async def list_enterprises(db: AsyncSession, officer_id: int) -> list[EnterpriseRead]:
    business_ids = await assignments_repo.list_assigned_business_ids(db, officer_id)
    results: list[EnterpriseRead] = []
    for business_id in business_ids:
        pair = await enterprises_repo.get_business_with_owner(db, business_id)
        if pair is None:
            continue
        results.append(await _assemble(db, *pair))
    return results


async def get_enterprise(db: AsyncSession, officer_id: int, business_id: int) -> EnterpriseRead:
    await _require_assigned(db, officer_id, business_id)
    pair = await enterprises_repo.get_business_with_owner(db, business_id)
    if pair is None:
        raise NotFoundError("Enterprise not found")
    return await _assemble(db, *pair)


async def get_cash_flow(db: AsyncSession, officer_id: int, business_id: int) -> list[CashFlowMonthRead]:
    await _require_assigned(db, officer_id, business_id)

    snapshots = await enterprises_repo.list_recent_snapshots(db, business_id, limit=6)
    months = [
        CashFlowMonthRead(
            label=_month_label(s.month),
            money_in_inr=s.money_in,
            money_out_inr=s.money_out,
            is_forecast=False,
            is_flagged=False,
        )
        for s in snapshots
    ]

    avg_out = (
        sum(s.money_out for s in snapshots) // len(snapshots) if snapshots else 0
    )
    forecasts = await insights_repo.latest_forecast(db, business_id)
    for f in sorted(forecasts, key=lambda row: row.horizon):
        # forecasts only carries a net cf_pred, not a rupee in/out split —
        # hold money_out at the recent average and derive money_in from the
        # identity net = in - out, so the predicted net stays accurate.
        money_out = avg_out
        money_in = money_out + int(f.cf_pred)
        label_date = date(f.as_on.year, f.as_on.month, 1)
        for _ in range(f.horizon):
            if label_date.month == 12:
                label_date = date(label_date.year + 1, 1, 1)
            else:
                label_date = date(label_date.year, label_date.month + 1, 1)
        months.append(
            CashFlowMonthRead(
                label=_month_label(label_date),
                money_in_inr=money_in,
                money_out_inr=money_out,
                is_forecast=True,
                is_flagged=f.is_risk_month,
            )
        )

    return months


async def get_data_quality(db: AsyncSession, officer_id: int, business_id: int) -> DataQualityRead:
    await _require_assigned(db, officer_id, business_id)

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    since = today - timedelta(days=7)
    streak = await enterprises_repo.entry_streak_days(db, business_id, since)

    health = await insights_repo.latest_health(db, business_id)
    if health is None:
        confidence = 50
    else:
        by_band = {
            ScoreBand.green: health.p_green,
            ScoreBand.amber: health.p_amber,
            ScoreBand.red: health.p_red,
        }
        confidence = round(float(by_band[health.band]) * 100)

    return DataQualityRead(
        entry_streak_days_per_week=min(streak, 7),
        forecast_confidence_percent=confidence,
    )
