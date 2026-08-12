
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.business import Business
from app.models.monthly_snapshot import MonthlySnapshot


async def list_for_user(db: AsyncSession, user_id: int) -> list[Business]:
    stmt = (
        select(Business)
        .where(Business.user_id == user_id, Business.status != RowStatus.deleted)
        .order_by(Business.id.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_owned(db: AsyncSession, business_id: int, user_id: int) -> Business | None:
    stmt = select(Business).where(
        Business.id == business_id,
        Business.user_id == user_id,
        Business.status != RowStatus.deleted,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def create(db: AsyncSession, business: Business) -> Business:
    db.add(business)
    await db.flush()
    return business


async def create_snapshot(db: AsyncSession, snapshot: MonthlySnapshot) -> MonthlySnapshot:
    db.add(snapshot)
    await db.flush()
    return snapshot
