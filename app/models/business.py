from __future__ import annotations

import enum

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Enum as SAEnum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, SoftDeleteMixin


class BusinessSegment(str, enum.Enum):
    shg = "shg"
    fpo = "fpo"
    own = "own"


class BusinessSector(str, enum.Enum):
    dairy = "dairy"
    poultry = "poultry"
    food_processing = "food_processing"
    handicrafts = "handicrafts"
    rural_retail = "rural_retail"
    other = "other"


class BusinessTenure(str, enum.Enum):
    under_1 = "under_1"
    one_to_three = "1_to_3"
    three_to_ten = "3_to_10"
    ten_plus = "10_plus"


segment_enum = SAEnum(BusinessSegment, name="segment_enum", values_callable=lambda e: [m.value for m in e], native_enum=True, create_type=True)
sector_enum = SAEnum(BusinessSector, name="sector_enum", values_callable=lambda e: [m.value for m in e], native_enum=True, create_type=True)
tenure_enum = SAEnum(BusinessTenure, name="tenure_enum", values_callable=lambda e: [m.value for m in e], native_enum=True, create_type=True)


class Business(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "businesses"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    segment: Mapped[BusinessSegment] = mapped_column(segment_enum, nullable=False)
    sector: Mapped[BusinessSector] = mapped_column(sector_enum, nullable=False)
    tenure: Mapped[BusinessTenure] = mapped_column(tenure_enum, nullable=False)

    staff_count: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")

    # Derived flags used by the ML feature builder
    is_new_business: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    years_in_operation: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")

    # Savings held and loan outstanding for this business. Per business rather
    # than per user: an owner running two ventures keeps their money apart, and
    # the score has to reflect the business being scored.
    savings_inr: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    loan_inr: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")

    __table_args__ = (
        CheckConstraint("staff_count >= 1", name="ck_businesses_staff_count_min"),
        Index("ix_businesses_user_active", "user_id", postgresql_where="status <> 'deleted'"),
    )
