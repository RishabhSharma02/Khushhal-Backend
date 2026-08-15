from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.officer import alerts as alerts_repo
from app.repositories.officer import assignments as assignments_repo
from app.repositories.officer import enterprises as enterprises_repo
from app.repositories.officer import visits as visits_repo
from app.schemas.officer.profile import CoverageRead


async def get_coverage(db: AsyncSession, officer_id: int) -> CoverageRead:
    business_ids = await assignments_repo.list_assigned_business_ids(db, officer_id)
    village_count = await enterprises_repo.distinct_village_count(db, business_ids)

    today = date.today()
    visits_this_month = 0
    for visit, _business, _user in await visits_repo.list_for_officer(db, officer_id):
        occurred = visit.occurred_at.date()
        if occurred.year == today.year and occurred.month == today.month:
            visits_this_month += 1

    last_30_start = today - timedelta(days=30)
    flags_resolved_last_30_days = 0
    for business_id in business_ids:
        for alert in await alerts_repo.list_for_business(db, business_id):
            if alert.resolved_at is not None and alert.resolved_at.date() >= last_30_start:
                flags_resolved_last_30_days += 1

    return CoverageRead(
        enterprise_count=len(business_ids),
        village_count=village_count,
        visits_this_month=visits_this_month,
        flags_resolved_last_30_days=flags_resolved_last_30_days,
    )
