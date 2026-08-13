
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.ledger_entry import EntryCategory, EntryKind, LedgerEntry
from app.models.sync_event import SyncEvent
from app.models.user import User
from app.repositories import ledger_entries as ledger_repo
from app.schemas.ledger import LedgerBatchResult, LedgerEntryCreate, LedgerEntryUpdate
from app.services import business_service


async def _rows_for_insert(
    entries: list[LedgerEntryCreate], business_id: int, user_id: int
) -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {
            "business_id": business_id,
            "user_id": user_id,
            "kind": e.kind.value,
            "amount_inr": e.amount_inr,
            "category": e.category.value,
            "recorded_at": e.recorded_at,
            "source": e.source.value,
            "client_entry_id": e.client_entry_id,
            "synced_at": now,
            "created_by": user_id,
            "updated_by": user_id,
        }
        for e in entries
    ]


async def create_entry(
    db: AsyncSession, business_id: int, current: User, payload: LedgerEntryCreate
) -> LedgerBatchResult:
    await business_service.require_owned(db, business_id, current)
    rows = await _rows_for_insert([payload], business_id, current.id)
    inserted_ids = await ledger_repo.insert_batch_idempotent(db, rows)
    result = LedgerBatchResult(
        accepted=len(inserted_ids),
        duplicates=1 - len(inserted_ids),
        accepted_ids=inserted_ids,
    )
    await db.commit()
    return result


async def sync_batch(
    db: AsyncSession, business_id: int, current: User, entries: list[LedgerEntryCreate]
) -> LedgerBatchResult:
    await business_service.require_owned(db, business_id, current)
    rows = await _rows_for_insert(entries, business_id, current.id)
    inserted_ids = await ledger_repo.insert_batch_idempotent(db, rows)

    db.add(SyncEvent(
        user_id=current.id,
        batch_size=len(entries),
        accepted=len(inserted_ids),
        duplicates=len(entries) - len(inserted_ids),
        created_by=current.id,
        updated_by=current.id,
    ))
    await db.commit()
    return LedgerBatchResult(
        accepted=len(inserted_ids),
        duplicates=len(entries) - len(inserted_ids),
        accepted_ids=inserted_ids,
    )


async def list_entries(
    db: AsyncSession,
    business_id: int,
    current: User,
    *,
    kind: EntryKind | None,
    category: EntryCategory | None,
    date_from: datetime | None,
    date_to: datetime | None,
    limit: int,
    cursor_id: int | None,
) -> list[LedgerEntry]:
    await business_service.require_owned(db, business_id, current)
    return await ledger_repo.get_by_business(
        db,
        business_id,
        kind=kind,
        category=category,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        cursor_id=cursor_id,
    )


async def update_entry(
    db: AsyncSession,
    business_id: int,
    entry_id: int,
    current: User,
    payload: LedgerEntryUpdate,
) -> LedgerEntry:
    await business_service.require_owned(db, business_id, current)
    entry = await ledger_repo.get_owned_entry(db, entry_id, business_id)
    if entry is None:
        raise NotFoundError("Entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    entry.updated_by = current.id
    await db.commit()
    await db.refresh(entry)
    return entry
