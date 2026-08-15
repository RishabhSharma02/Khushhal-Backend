from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.action_step import OfficerActionStep


async def list_for_business(db: AsyncSession, business_id: int) -> list[OfficerActionStep]:
    stmt = (
        select(OfficerActionStep)
        .where(OfficerActionStep.business_id == business_id, OfficerActionStep.status != RowStatus.deleted)
        .order_by(OfficerActionStep.ordinal.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_owned(db: AsyncSession, step_id: int, business_id: int) -> OfficerActionStep | None:
    stmt = select(OfficerActionStep).where(
        OfficerActionStep.id == step_id,
        OfficerActionStep.business_id == business_id,
        OfficerActionStep.status != RowStatus.deleted,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def next_ordinal(db: AsyncSession, business_id: int) -> int:
    stmt = select(func.coalesce(func.max(OfficerActionStep.ordinal), 0)).where(
        OfficerActionStep.business_id == business_id, OfficerActionStep.status != RowStatus.deleted
    )
    return int((await db.execute(stmt)).scalar_one()) + 1
