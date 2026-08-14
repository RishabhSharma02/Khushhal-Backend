from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.contact_log_entry import ContactLogEntry
from app.models.officer import Officer
from app.repositories.officer import assignments as assignments_repo
from app.repositories.officer import contact_log as contact_log_repo
from app.schemas.officer.contact_log import ContactLogEntryCreate


async def _require_assigned(db: AsyncSession, officer_id: int, business_id: int) -> None:
    if not await assignments_repo.is_assigned(db, officer_id, business_id):
        raise NotFoundError("Enterprise not found")


async def list_contact_log(
    db: AsyncSession, officer: Officer, business_id: int
) -> list[ContactLogEntry]:
    await _require_assigned(db, officer.id, business_id)
    return await contact_log_repo.list_for_business(db, business_id)


async def create_contact_log_entry(
    db: AsyncSession, officer: Officer, business_id: int, payload: ContactLogEntryCreate
) -> ContactLogEntry:
    await _require_assigned(db, officer.id, business_id)
    entry = ContactLogEntry(
        business_id=business_id,
        occurred_at=payload.occurred_at,
        kind=payload.kind,
        note=payload.note,
        created_by=officer.id,
        updated_by=officer.id,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
