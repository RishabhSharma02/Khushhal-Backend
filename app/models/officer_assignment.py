from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin
from app.models.officer_base import OfficerAuditMixin


class OfficerEnterpriseAssignment(Base, OfficerAuditMixin, SoftDeleteMixin):
    """Defines an officer's beat — which existing `businesses` rows they can
    see/act on through the officer API. Read-only against `businesses`;
    this table is the only new state.
    """

    __tablename__ = "officer_enterprise_assignments"

    officer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("officers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint("officer_id", "business_id", name="uq_officer_enterprise_assignment"),
    )
