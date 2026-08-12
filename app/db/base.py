"""Declarative base + mixins enforcing the Khushhal schema conventions.

Every table:
  - id BIGINT identity PK
  - creation_date / created_by / updation_date / updated_by
  - status enum (active | inactive | deleted) — soft delete
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class RowStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    deleted = "deleted"


# Reusable enum type — create_type=True so Alembic emits the CREATE TYPE once.
row_status_enum = SAEnum(
    RowStatus,
    name="row_status",
    values_callable=lambda e: [m.value for m in e],
    native_enum=True,
    create_type=True,
)


class Base(DeclarativeBase):
    """Root SQLAlchemy base — all models inherit."""


class AuditMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    creation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    updation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class SoftDeleteMixin:
    status: Mapped[RowStatus] = mapped_column(
        row_status_enum, nullable=False, default=RowStatus.active, server_default=RowStatus.active.value
    )

    @property
    def is_deleted(self) -> bool:
        return self.status == RowStatus.deleted
