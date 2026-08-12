
import uuid
from datetime import datetime
from typing import Iterable

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.ledger_entry import EntryCategory, EntryKind, LedgerEntry


async def get_by_business(
    db: AsyncSession,
    business_id: int,
    *,
    kind: EntryKind | None = None,
    category: EntryCategory | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    cursor_id: int | None = None,
) -> list[LedgerEntry]:
    conds = [LedgerEntry.business_id == business_id, LedgerEntry.status != RowStatus.deleted]
    if kind is not None:
        conds.append(LedgerEntry.kind == kind)
    if category is not None:
        conds.append(LedgerEntry.category == category)
    if date_from is not None:
        conds.append(LedgerEntry.recorded_at >= date_from)
    if date_to is not None:
        conds.append(LedgerEntry.recorded_at <= date_to)
    if cursor_id is not None:
        conds.append(LedgerEntry.id < cursor_id)

    stmt = (
        select(LedgerEntry)
        .where(and_(*conds))
        .order_by(LedgerEntry.recorded_at.desc(), LedgerEntry.id.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def find_existing_client_ids(
    db: AsyncSession, business_id: int, client_ids: Iterable[uuid.UUID]
) -> set[uuid.UUID]:
    ids = list(client_ids)
    if not ids:
        return set()
    stmt = select(LedgerEntry.client_entry_id).where(
        LedgerEntry.business_id == business_id,
        LedgerEntry.client_entry_id.in_(ids),
    )
    rows = (await db.execute(stmt)).scalars().all()
    return set(rows)


async def insert_batch_idempotent(
    db: AsyncSession, rows: list[dict]
) -> list[int]:
    """Insert with ON CONFLICT DO NOTHING on (business_id, client_entry_id).
    Returns the ids of *newly inserted* rows only.
    """
    if not rows:
        return []
    stmt = (
        pg_insert(LedgerEntry.__table__)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["business_id", "client_entry_id"])
        .returning(LedgerEntry.__table__.c.id)
    )
    result = await db.execute(stmt)
    return [r[0] for r in result.fetchall()]


async def get_owned_entry(
    db: AsyncSession, entry_id: int, business_id: int
) -> LedgerEntry | None:
    stmt = select(LedgerEntry).where(
        LedgerEntry.id == entry_id,
        LedgerEntry.business_id == business_id,
        LedgerEntry.status != RowStatus.deleted,
    )
    return (await db.execute(stmt)).scalar_one_or_none()
