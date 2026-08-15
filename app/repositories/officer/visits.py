from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.business import Business
from app.models.user import User
from app.models.visit import OfficerVisit


async def list_for_officer(db: AsyncSession, officer_id: int) -> list[tuple[OfficerVisit, Business, User]]:
    stmt = (
        select(OfficerVisit, Business, User)
        .join(Business, Business.id == OfficerVisit.business_id)
        .join(User, User.id == Business.user_id)
        .where(OfficerVisit.officer_id == officer_id, OfficerVisit.status != RowStatus.deleted)
        .order_by(OfficerVisit.occurred_at.desc())
    )
    return [(row[0], row[1], row[2]) for row in (await db.execute(stmt)).all()]
