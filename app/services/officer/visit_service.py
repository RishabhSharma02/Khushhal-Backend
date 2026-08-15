from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.business import Business
from app.models.officer import Officer
from app.models.user import User
from app.models.visit import OfficerVisit
from app.repositories.officer import assignments as assignments_repo
from app.repositories.officer import enterprises as enterprises_repo
from app.repositories.officer import visits as visits_repo
from app.schemas.officer.visits import VisitCreate, VisitRead


def _to_read(visit: OfficerVisit, business: Business, user: User) -> VisitRead:
    return VisitRead(
        id=visit.id,
        enterprise_id=str(business.id),
        enterprise_name=business.name,
        village=user.village or "",
        date=visit.occurred_at,
        agenda=visit.agenda,
        status="done",
        risk_level=visit.risk_level.value if visit.risk_level else None,
        distance_km=None,
    )


async def list_visits(db: AsyncSession, officer: Officer) -> list[VisitRead]:
    rows = await visits_repo.list_for_officer(db, officer.id)
    return [_to_read(visit, business, user) for visit, business, user in rows]


async def create_visit(db: AsyncSession, officer: Officer, payload: VisitCreate) -> VisitRead:
    if not await assignments_repo.is_assigned(db, officer.id, payload.business_id):
        raise NotFoundError("Enterprise not found")

    pair = await enterprises_repo.get_business_with_owner(db, payload.business_id)
    if pair is None:
        raise NotFoundError("Enterprise not found")
    business, user = pair

    visit = OfficerVisit(
        officer_id=officer.id,
        business_id=payload.business_id,
        occurred_at=payload.date,
        agenda=payload.agenda,
        risk_level=payload.risk_level,
        created_by=officer.id,
        updated_by=officer.id,
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)

    return _to_read(visit, business, user)
