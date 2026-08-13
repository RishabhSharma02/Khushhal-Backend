from __future__ import annotations

import enum

from sqlalchemy import Boolean, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, SoftDeleteMixin


class Language(str, enum.Enum):
    hi = "hi"
    en = "en"


language_enum = SAEnum(
    Language,
    name="lang_enum",
    values_callable=lambda e: [m.value for m in e],
    native_enum=True,
    create_type=True,
)


class User(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "users"

    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    phone_e164: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    language: Mapped[Language] = mapped_column(
        language_enum, nullable=False, default=Language.hi, server_default=Language.hi.value
    )

    state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    village: Mapped[str | None] = mapped_column(String(120), nullable=True)

    savings_inr: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    loan_inr: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)

    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
