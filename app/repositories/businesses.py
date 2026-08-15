
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.business import Business
from app.models.monthly_snapshot import MonthlySnapshot
from app.models.officer_assignment import OfficerEnterpriseAssignment


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


async def latest_snapshot(db: AsyncSession, business_id: int) -> MonthlySnapshot | None:
    stmt = (
        select(MonthlySnapshot)
        .where(
            MonthlySnapshot.business_id == business_id,
            MonthlySnapshot.status != RowStatus.deleted,
        )
        .order_by(MonthlySnapshot.month.desc(), MonthlySnapshot.id.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def latest_snapshots_map(db: AsyncSession, business_ids: list[int]) -> dict[int, MonthlySnapshot]:
    """Bulk-fetch the newest snapshot for each of the supplied business ids."""
    if not business_ids:
        return {}
    stmt = (
        select(MonthlySnapshot)
        .where(
            MonthlySnapshot.business_id.in_(business_ids),
            MonthlySnapshot.status != RowStatus.deleted,
        )
        .order_by(MonthlySnapshot.business_id, MonthlySnapshot.month.desc(), MonthlySnapshot.id.desc())
    )
    result: dict[int, MonthlySnapshot] = {}
    for row in (await db.execute(stmt)).scalars().all():
        result.setdefault(row.business_id, row)
    return result


async def assigned_officer_ids_map(
    db: AsyncSession, business_ids: list[int]
) -> dict[int, int]:
    """Earliest active assignment per business.

    `businesses.officer_id` is the consumer-facing denormalized copy, but
    rows assigned before that column was populated (or via the assignment
    table alone) still need GET /businesses to return an officer_id.
    """
    if not business_ids:
        return {}
    stmt = (
        select(
            OfficerEnterpriseAssignment.business_id,
            OfficerEnterpriseAssignment.officer_id,
        )
        .where(
            OfficerEnterpriseAssignment.business_id.in_(business_ids),
            OfficerEnterpriseAssignment.status != RowStatus.deleted,
        )
        .order_by(OfficerEnterpriseAssignment.id.asc())
    )
    result: dict[int, int] = {}
    for business_id, officer_id in (await db.execute(stmt)).all():
        result.setdefault(business_id, officer_id)
    return result
