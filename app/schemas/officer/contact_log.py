from datetime import datetime

from pydantic import BaseModel, Field

from app.models.contact_log_entry import ContactKind
from app.schemas.common import ORMModel


class ContactLogEntryRead(ORMModel):
    id: int
    occurred_at: datetime
    kind: str
    note: str


class ContactLogEntryCreate(BaseModel):
    occurred_at: datetime
    # Typed as the enum (not str) — see ActionStepCreate's note on why an
    # invalid value must be rejected here, not in the service layer.
    kind: ContactKind
    note: str = Field(min_length=1, max_length=500)
