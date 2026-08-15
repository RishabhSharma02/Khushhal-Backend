from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.contact_log_entry import ContactLogEntry


async def list_for_business(db: AsyncSession, business_id: int) -> list[ContactLogEntry]:
    stmt = (
        select(ContactLogEntry)
        .where(ContactLogEntry.business_id == business_id, ContactLogEntry.status != RowStatus.deleted)
        .order_by(ContactLogEntry.occurred_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())
