from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin
from app.models.officer_base import OfficerAuditMixin


class Officer(Base, OfficerAuditMixin, SoftDeleteMixin):
    __tablename__ = "officers"

    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    employee_id_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # Nullable: only used for contact/SMS purposes, not sign-in (that's
    # email/password) — an officer can add it later via profile edit.
    mobile_e164: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)

    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    block: Mapped[str | None] = mapped_column(String(80), nullable=True)
    state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    device_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
