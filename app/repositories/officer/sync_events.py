from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.sync_event import SyncEvent


async def last_sync_at(db: AsyncSession, user_id: int) -> datetime | None:
    stmt = select(func.max(SyncEvent.creation_date)).where(
        SyncEvent.user_id == user_id, SyncEvent.status != RowStatus.deleted
    )
    return (await db.execute(stmt)).scalar_one_or_none()
