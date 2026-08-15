from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.business import Business
from app.models.enterprise_contact import EnterpriseContact
from app.models.ledger_entry import EntryKind, LedgerEntry
from app.models.monthly_snapshot import MonthlySnapshot
from app.models.user import User


async def get_business_with_owner(db: AsyncSession, business_id: int) -> tuple[Business, User] | None:
    stmt = (
        select(Business, User)
        .join(User, User.id == Business.user_id)
        .where(Business.id == business_id, Business.status != RowStatus.deleted)
    )
    row = (await db.execute(stmt)).first()
    return (row[0], row[1]) if row is not None else None


async def get_contact(db: AsyncSession, business_id: int) -> EnterpriseContact | None:
    stmt = select(EnterpriseContact).where(
        EnterpriseContact.business_id == business_id,
        EnterpriseContact.status != RowStatus.deleted,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def cash_on_hand(db: AsyncSession, business_id: int) -> int:
    signed = case((LedgerEntry.kind == EntryKind.in_, LedgerEntry.amount_inr), else_=-LedgerEntry.amount_inr)
    stmt = select(func.coalesce(func.sum(signed), 0)).where(
        LedgerEntry.business_id == business_id,
        LedgerEntry.status != RowStatus.deleted,
    )
    return int((await db.execute(stmt)).scalar_one())


async def last_entry_at(db: AsyncSession, business_id: int) -> datetime | None:
    stmt = select(func.max(LedgerEntry.recorded_at)).where(
        LedgerEntry.business_id == business_id,
        LedgerEntry.status != RowStatus.deleted,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def entry_streak_days(db: AsyncSession, business_id: int, since: datetime) -> int:
    """Distinct calendar days with at least one entry since [since]."""
    stmt = select(func.count(func.distinct(func.date(LedgerEntry.recorded_at)))).where(
        LedgerEntry.business_id == business_id,
        LedgerEntry.status != RowStatus.deleted,
        LedgerEntry.recorded_at >= since,
    )
    return int((await db.execute(stmt)).scalar_one())


async def distinct_village_count(db: AsyncSession, business_ids: list[int]) -> int:
    """Distinct owner villages among the given businesses — the Profile
    screen's "My coverage" tile. Villages aren't on `businesses` itself,
    only on the owning `users` row.
    """
    if not business_ids:
        return 0
    stmt = (
        select(func.count(func.distinct(User.village)))
        .select_from(Business)
        .join(User, User.id == Business.user_id)
        .where(Business.id.in_(business_ids), User.village.isnot(None))
    )
    return int((await db.execute(stmt)).scalar_one())


async def list_recent_snapshots(db: AsyncSession, business_id: int, limit: int = 6) -> list[MonthlySnapshot]:
    """Oldest-first, most recent [limit] months — for the cash-flow chart's
    actuals half.
    """
    stmt = (
        select(MonthlySnapshot)
        .where(MonthlySnapshot.business_id == business_id, MonthlySnapshot.status != RowStatus.deleted)
        .order_by(MonthlySnapshot.month.desc())
        .limit(limit)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    rows.reverse()
    return rows
