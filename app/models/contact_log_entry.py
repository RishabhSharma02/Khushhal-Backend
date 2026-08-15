from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin
from app.models.officer_base import OfficerAuditMixin


class ContactKind(str, enum.Enum):
    visit = "visit"
    call = "call"


contact_kind_enum = SAEnum(
    ContactKind, name="contact_kind_enum",
    values_callable=lambda e: [m.value for m in e], native_enum=True, create_type=True,
)


class ContactLogEntry(Base, OfficerAuditMixin, SoftDeleteMixin):
    """An officer's visit/call note against an enterprise — new state, no
    equivalent exists on the customer-side tables.
    """

    __tablename__ = "contact_log_entries"

    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kind: Mapped[ContactKind] = mapped_column(contact_kind_enum, nullable=False)
    note: Mapped[str] = mapped_column(String(500), nullable=False)
