from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import BigInteger, CheckConstraint, Date, Enum as SAEnum, ForeignKey, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, SoftDeleteMixin


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ScoreBand(str, enum.Enum):
    green = "green"
    amber = "amber"
    red = "red"


risk_enum = SAEnum(RiskLevel, name="risk_enum", values_callable=lambda e: [m.value for m in e], native_enum=True, create_type=True)
band_enum = SAEnum(ScoreBand, name="band_enum", values_callable=lambda e: [m.value for m in e], native_enum=True, create_type=True)


class HealthScore(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "health_scores"

    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    as_on: Mapped[date] = mapped_column(Date, nullable=False)
    next_update: Mapped[date] = mapped_column(Date, nullable=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    risk: Mapped[RiskLevel] = mapped_column(risk_enum, nullable=False)
    delta: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    days_written: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    days_in_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=30, server_default="30")
    band: Mapped[ScoreBand] = mapped_column(band_enum, nullable=False)
    p_green: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    p_amber: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    p_red: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_health_scores_score_range"),
        UniqueConstraint("business_id", "as_on", name="uq_health_scores_business_month"),
    )
