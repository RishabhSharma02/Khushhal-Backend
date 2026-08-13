from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import BigInteger, Date, Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, SoftDeleteMixin


class MoneyBasis(str, enum.Enum):
    rough = "rough"
    records = "records"


basis_enum = SAEnum(
    MoneyBasis, name="basis_enum", values_callable=lambda e: [m.value for m in e], native_enum=True, create_type=True
)


class MonthlySnapshot(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "monthly_snapshots"

    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    month: Mapped[date] = mapped_column(Date, nullable=False)

    money_in: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    money_out: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    loan_emi: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    savings: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")

    basis: Mapped[MoneyBasis] = mapped_column(basis_enum, nullable=False)

    __table_args__ = (
        UniqueConstraint("business_id", "month", name="uq_monthly_snapshot_business_month"),
    )
