"""Audit mixin for officer-owned tables.

`AuditMixin` in app/db/base.py hardcodes created_by/updated_by as FKs to
`users.id`, which is correct for the consumer app but wrong for rows an
officer creates. This mirrors that mixin's shape with the FK pointed at
`officers.id` instead, so officer tables never touch db/base.py.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column


class OfficerAuditMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    creation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("officers.id", ondelete="SET NULL"), nullable=True
    )

    updation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("officers.id", ondelete="SET NULL"), nullable=True
    )
