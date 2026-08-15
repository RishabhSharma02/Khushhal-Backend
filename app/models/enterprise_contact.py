from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin
from app.models.officer_base import OfficerAuditMixin


class EnterpriseContact(Base, OfficerAuditMixin, SoftDeleteMixin):
    """Officer-visible calling details for a business — name/role/phone/
    language/best-time aren't tracked anywhere on `businesses`/`users`, so
    this is genuinely new state layered on top of the existing business.
    One row per business; falls back to the owning `User` when absent (see
    app/services/officer/enterprise_service.py).
    """

    __tablename__ = "enterprise_contacts"

    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(60), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    language: Mapped[str] = mapped_column(String(40), nullable=False)
    best_time: Mapped[str] = mapped_column(String(60), nullable=False, default="", server_default="")

    __table_args__ = (
        UniqueConstraint("business_id", name="uq_enterprise_contacts_business"),
    )
