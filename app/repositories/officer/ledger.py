from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.ledger_entry import EntrySource, LedgerEntry


async def has_voice_entry_in_range(
    db: AsyncSession, business_id: int, start: datetime, end: datetime
) -> bool:
    stmt = (
        select(LedgerEntry.id)
        .where(
            LedgerEntry.business_id == business_id,
            LedgerEntry.source == EntrySource.voice,
            LedgerEntry.recorded_at >= start,
            LedgerEntry.recorded_at <= end,
            LedgerEntry.status != RowStatus.deleted,
        )
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None
