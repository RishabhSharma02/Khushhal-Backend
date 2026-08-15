from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.officer import Officer
from app.models.officer_assignment import OfficerEnterpriseAssignment


async def create(
    db: AsyncSession, *, officer_id: int, business_id: int
) -> OfficerEnterpriseAssignment:
    assignment = OfficerEnterpriseAssignment(officer_id=officer_id, business_id=business_id)
    db.add(assignment)
    await db.flush()
    # No admin/actor identity exists for an automatic assignment — same
    # self-referential convention as officer self-registration.
    assignment.created_by = officer_id
    assignment.updated_by = officer_id
    await db.flush()
    return assignment


async def least_loaded_officer(db: AsyncSession, *, state: str | None) -> Officer | None:
    """The active officer with the fewest active enterprise assignments,
    optionally restricted to officers whose `state` matches (case/whitespace
    insensitive). Ties break on officer id (earliest-provisioned first) so
    results are deterministic. Returns `None` if no officer matches.
    """
    load = (
        select(
            OfficerEnterpriseAssignment.officer_id.label("officer_id"),
            func.count(OfficerEnterpriseAssignment.id).label("load"),
        )
        .where(OfficerEnterpriseAssignment.status != RowStatus.deleted)
        .group_by(OfficerEnterpriseAssignment.officer_id)
        .subquery()
    )
    load_count = func.coalesce(load.c.load, 0)
    stmt = (
        select(Officer)
        .outerjoin(load, load.c.officer_id == Officer.id)
        .where(Officer.status != RowStatus.deleted)
        .order_by(load_count.asc(), Officer.id.asc())
        .limit(1)
    )
    if state:
        stmt = stmt.where(func.lower(Officer.state) == state.strip().lower())
    return (await db.execute(stmt)).scalar_one_or_none()


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
