from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, ForeignKey, Numeric, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, SoftDeleteMixin


class Forecast(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "forecasts"

    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    as_on: Mapped[date] = mapped_column(Date, nullable=False)
    horizon: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    cf_pred: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    in_level: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0.0, server_default="0")
    out_level: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0.0, server_default="0")
    is_risk_month: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    __table_args__ = (
        CheckConstraint("horizon >= 1 AND horizon <= 6", name="ck_forecasts_horizon_range"),
        UniqueConstraint("business_id", "as_on", "horizon", name="uq_forecasts_business_month_horizon"),
    )
