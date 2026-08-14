from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.officer_assignment import OfficerEnterpriseAssignment


async def list_assigned_business_ids(db: AsyncSession, officer_id: int) -> list[int]:
    stmt = (
        select(OfficerEnterpriseAssignment.business_id)
        .where(
            OfficerEnterpriseAssignment.officer_id == officer_id,
            OfficerEnterpriseAssignment.status != RowStatus.deleted,
        )
        .order_by(OfficerEnterpriseAssignment.id.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def is_assigned(db: AsyncSession, officer_id: int, business_id: int) -> bool:
    stmt = select(OfficerEnterpriseAssignment.id).where(
        OfficerEnterpriseAssignment.officer_id == officer_id,
        OfficerEnterpriseAssignment.business_id == business_id,
        OfficerEnterpriseAssignment.status != RowStatus.deleted,
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None
