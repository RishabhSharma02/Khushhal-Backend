from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin
from app.models.officer_base import OfficerAuditMixin


class VisitRiskLevel(str, enum.Enum):
    healthy = "healthy"
    watch = "watch"
    at_risk = "atRisk"


visit_risk_level_enum = SAEnum(
    VisitRiskLevel, name="visit_risk_level_enum",
    values_callable=lambda e: [m.value for m in e], native_enum=True, create_type=True,
)


class OfficerVisit(Base, OfficerAuditMixin, SoftDeleteMixin):
    """A field visit the officer has logged (this app doesn't schedule
    future visits — see add_visit_dialog.dart's docstring — every row here
    is already-happened, status is always implicitly "done").
    """

    __tablename__ = "visits"

    officer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("officers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    agenda: Mapped[str] = mapped_column(String(400), nullable=False)
    risk_level: Mapped[VisitRiskLevel | None] = mapped_column(visit_risk_level_enum, nullable=True)
