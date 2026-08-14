"""Officer portal month-in-review. Reuses the sector→portal-name/icon maps
from enterprise_service.py so sector labels stay consistent with the
enterprises list.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import insights as insights_repo
from app.repositories.officer import alerts as alerts_repo
from app.repositories.officer import assignments as assignments_repo
from app.repositories.officer import enterprises as enterprises_repo
from app.repositories.officer import ledger as ledger_repo
from app.repositories.officer import visits as visits_repo
from app.schemas.officer.reports import (
    AppAdoptionRead,
    ForecastAccuracyRead,
    ReportSummaryRead,
    SectorScoreRead,
)
from app.services.officer.dashboard_service import _add_months
from app.services.officer.enterprise_service import _SECTOR_ICON, _SECTOR_TO_PORTAL

_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


async def get_reports(db: AsyncSession, officer_id: int) -> ReportSummaryRead:
    business_ids = await assignments_repo.list_assigned_business_ids(db, officer_id)
    this_month = date.today().replace(day=1)
    prev_month = _add_months(this_month, -1)
    next_month = _add_months(this_month, 1)

    scores_this_month: list[int] = []
    scores_prev_month: list[int] = []
    sector_scores: dict[str, list[int]] = {}
    streak_count = 0
    voice_users = 0
    savings_plan_count = 0

    since_week_start = datetime.now(timezone.utc) - timedelta(days=7)
    month_start_dt = datetime(this_month.year, this_month.month, 1, tzinfo=timezone.utc)
    month_end_dt = datetime(next_month.year, next_month.month, 1, tzinfo=timezone.utc)

    for business_id in business_ids:
        pair = await enterprises_repo.get_business_with_owner(db, business_id)
        if pair is None:
            continue
        business, user = pair

        current = await insights_repo.health_at(db, business_id, this_month)
        if current is not None:
            scores_this_month.append(current.score)
            sector_key = _SECTOR_TO_PORTAL.get(business.sector.value, "other")
            sector_scores.setdefault(sector_key, []).append(current.score)
        previous = await insights_repo.health_at(db, business_id, prev_month)
        if previous is not None:
            scores_prev_month.append(previous.score)

        streak = await enterprises_repo.entry_streak_days(db, business_id, since_week_start)
        if streak >= 5:
            streak_count += 1
        if await ledger_repo.has_voice_entry_in_range(db, business_id, month_start_dt, month_end_dt):
            voice_users += 1
        if user.savings_inr > 0:
            savings_plan_count += 1

    average_health_score = round(sum(scores_this_month) / len(scores_this_month)) if scores_this_month else 0
    average_prev = round(sum(scores_prev_month) / len(scores_prev_month)) if scores_prev_month else 0
    average_health_score_delta = average_health_score - average_prev

    flags_resolved = 0
    flags_opened = 0
    flags_raised = 0
    false_alarms = 0
    resolution_days: list[int] = []
    for business_id in business_ids:
        for alert in await alerts_repo.list_for_business(db, business_id):
            if alert.raised_on >= this_month:
                flags_opened += 1
                flags_raised += 1
                if alert.resolved_at is not None and (alert.resolved_at.date() - alert.raised_on).days <= 1:
                    false_alarms += 1
            if alert.resolved_at is not None and alert.resolved_at.date() >= this_month:
                flags_resolved += 1
                resolution_days.append((alert.resolved_at.date() - alert.raised_on).days)

    average_resolution_days = round(sum(resolution_days) / len(resolution_days)) if resolution_days else 0
    flags_that_came_true = flags_raised - false_alarms
    predicted_vs_actual_label = (
        "n/a" if flags_raised == 0 else f"{round(flags_that_came_true / flags_raised * 100)}% validated"
    )

    visits_done = 0
    risk_led_visits = 0
    for visit, _business, _user in await visits_repo.list_for_officer(db, officer_id):
        if visit.occurred_at.date() >= this_month:
            visits_done += 1
            if visit.risk_level is not None and visit.risk_level.value != "healthy":
                risk_led_visits += 1

    sector_rows = [
        SectorScoreRead(
            icon=_SECTOR_ICON.get(
                next(k for k, v in _SECTOR_TO_PORTAL.items() if v == sector_key), "🏢"
            ),
            label=sector_key[:1].upper() + sector_key[1:],
            enterprise_count=len(scores),
            average_score=round(sum(scores) / len(scores)),
        )
        for sector_key, scores in sector_scores.items()
    ]
    sector_rows.sort(key=lambda s: -s.enterprise_count)

    insight = "Not enough data yet to surface a sector insight."
    if sector_rows:
        weakest = min(sector_rows, key=lambda s: s.average_score)
        insight = (
            f"{weakest.label} needs attention — lowest average score at {weakest.average_score}."
        )

    return ReportSummaryRead(
        month_label=f"{_MONTH_NAMES[this_month.month - 1]} {this_month.year}",
        compared_to_label=f"Compared with {_MONTH_NAMES[prev_month.month - 1]}",
        average_health_score=average_health_score,
        average_health_score_delta=average_health_score_delta,
        flags_resolved=flags_resolved,
        flags_opened=flags_opened,
        average_resolution_days=average_resolution_days,
        emis_on_time_percent=100,
        emis_on_time_delta=0,
        visits_done=visits_done,
        risk_led_visits=risk_led_visits,
        sector_scores=sector_rows,
        insight=insight,
        forecast_accuracy=ForecastAccuracyRead(
            predicted_vs_actual_label=predicted_vs_actual_label,
            flags_that_came_true=flags_that_came_true,
            flags_raised=flags_raised,
            false_alarms=false_alarms,
        ),
        app_adoption=AppAdoptionRead(
            enterprises_with_streak=streak_count,
            total_enterprises=len(business_ids),
            voice_entry_users=voice_users,
            active_savings_plans=savings_plan_count,
        ),
    )
