import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.ledger_entry import EntryCategory, EntryKind, EntrySource
from app.schemas.common import ORMModel


class LedgerEntryCreate(BaseModel):
    client_entry_id: uuid.UUID
    kind: EntryKind
    amount_inr: int = Field(gt=0)
    category: EntryCategory
    recorded_at: datetime
    source: EntrySource = EntrySource.manual


class LedgerBatchSync(BaseModel):
    entries: list[LedgerEntryCreate] = Field(min_length=1, max_length=500)


class LedgerBatchResult(BaseModel):
    accepted: int
    duplicates: int
    accepted_ids: list[int]


class LedgerEntryUpdate(BaseModel):
    amount_inr: int | None = Field(default=None, gt=0)
    category: EntryCategory | None = None
    recorded_at: datetime | None = None


class LedgerEntryRead(ORMModel):
    id: int
    business_id: int
    client_entry_id: uuid.UUID
    kind: EntryKind
    amount_inr: int
    category: EntryCategory
    recorded_at: datetime
    source: EntrySource
    synced_at: datetime | None
