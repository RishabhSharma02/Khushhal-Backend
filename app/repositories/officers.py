from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.officer import Officer


async def get(db: AsyncSession, officer_id: int) -> Officer | None:
    stmt = select(Officer).where(
        Officer.id == officer_id,
        Officer.status != RowStatus.deleted,
    )
    return (await db.execute(stmt)).scalar_one_or_none()
