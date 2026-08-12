from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, SoftDeleteMixin


class SyncEvent(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "sync_events"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    batch_size: Mapped[int] = mapped_column(nullable=False)
    accepted: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    duplicates: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
