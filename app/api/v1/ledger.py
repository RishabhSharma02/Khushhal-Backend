
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.ledger_entry import EntryCategory, EntryKind
from app.models.user import User
from app.schemas.common import PageEnvelope
from app.schemas.ledger import (
    LedgerBatchResult,
    LedgerBatchSync,
    LedgerEntryCreate,
    LedgerEntryRead,
    LedgerEntryUpdate,
)
from app.services import ledger_service

router = APIRouter(tags=["ledger"], prefix="/businesses/{business_id}/entries")


@router.post("", response_model=LedgerBatchResult, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_entry(
    request: Request,
    business_id: int,
    payload: LedgerEntryCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> LedgerBatchResult:
    return await ledger_service.create_entry(db, business_id, current, payload)


@router.post("/sync", response_model=LedgerBatchResult)
@limiter.limit("20/minute")
async def sync_entries(
    request: Request,
    business_id: int,
    payload: LedgerBatchSync,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> LedgerBatchResult:
    return await ledger_service.sync_batch(db, business_id, current, payload.entries)


@router.get("", response_model=PageEnvelope[LedgerEntryRead])
async def list_entries(
    business_id: int,
    kind: EntryKind | None = None,
    category: EntryCategory | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: int | None = None,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> PageEnvelope[LedgerEntryRead]:
    items = await ledger_service.list_entries(
        db, business_id, current,
        kind=kind, category=category,
        date_from=date_from, date_to=date_to,
        limit=limit, cursor_id=cursor,
    )
    next_cursor = str(items[-1].id) if len(items) == limit else None
    return PageEnvelope(
        items=[LedgerEntryRead.model_validate(e) for e in items],
        next_cursor=next_cursor,
    )


@router.patch("/{entry_id}", response_model=LedgerEntryRead)
async def patch_entry(
    business_id: int,
    entry_id: int,
    payload: LedgerEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> LedgerEntryRead:
    entry = await ledger_service.update_entry(db, business_id, entry_id, current, payload)
    return LedgerEntryRead.model_validate(entry)
