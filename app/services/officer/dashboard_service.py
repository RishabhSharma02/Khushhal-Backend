"""Officer portal dashboard trend data.

Per-enterprise current state (counts by risk level, risk queue, next visit)
is already loaded client-side from /enterprises and /visits — this endpoint
only covers what genuinely needs server-side aggregation across *time*
(a 6-month score history) or across *all* assigned businesses at once
(open-flag/EMI/visit counts).
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import insights as insights_repo
from app.repositories.officer import alerts as alerts_repo
from app.repositories.officer import assignments as assignments_repo
from app.repositories.officer import visits as visits_repo
from app.schemas.officer.dashboard import DashboardRead


def _add_months(d: date, delta: int) -> date:
    month_index = d.month - 1 + delta
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


async def get_dashboard(db: AsyncSession, officer_id: int) -> DashboardRead:
    business_ids = await assignments_repo.list_assigned_business_ids(db, officer_id)
    this_month = date.today().replace(day=1)

    history: list[int] = []
    for offset in range(5, -1, -1):
        month = _add_months(this_month, -offset)
        scores = []
        for business_id in business_ids:
            row = await insights_repo.health_at(db, business_id, month)
            if row is not None:
                scores.append(row.score)
        history.append(round(sum(scores) / len(scores)) if scores else 0)
    average_score_delta = history[-1] - history[-2] if len(history) >= 2 else 0

    # No missed-EMI signal exists anywhere upstream yet (see
    # enterprise_service.py's emi_on_time note) — 100%/no-change is the
    # honest reading of "every known EMI is on time" when there's at least
    # one business to hold that claim about. With zero, there's nothing to
    # report at all, so it's None (N/A) rather than a vacuous 100%.
    emis_on_time_percent = 100 if business_ids else None
    emis_on_time_delta = 0 if business_ids else None

    today = date.today()
    last_30_start = today - timedelta(days=30)
    open_count = 0
    raised_last_30 = 0
    resolved_last_30 = 0
    for business_id in business_ids:
        for alert in await alerts_repo.list_for_business(db, business_id):
            if alert.resolved_at is None:
                open_count += 1
            if alert.raised_on >= last_30_start:
                raised_last_30 += 1
            if alert.resolved_at is not None and alert.resolved_at.date() >= last_30_start:
                resolved_last_30 += 1

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    visits_done_this_week = 0
    for visit, _business, _user in await visits_repo.list_for_officer(db, officer_id):
        if week_start <= visit.occurred_at.date() <= week_end:
            visits_done_this_week += 1

    return DashboardRead(
        average_score_history=history,
        average_score_delta=average_score_delta,
        emis_on_time_percent=emis_on_time_percent,
        emis_on_time_delta=emis_on_time_delta,
        open_flag_count=open_count,
        open_flag_delta=raised_last_30 - resolved_last_30,
        visits_done_this_week=visits_done_this_week,
        # This app logs visits after the fact rather than scheduling them
        # (see add_visit_dialog.dart) — there's no "planned" concept to
        # report separately, so it mirrors "done".
        visits_planned_this_week=visits_done_this_week,
    )
