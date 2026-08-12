from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, SoftDeleteMixin


class AlertKind(str, enum.Enum):
    savings_low = "savings_low"
    liquidity_debt_stress = "liquidity_debt_stress"
    climate_deficit = "climate_deficit"
    climate_excess = "climate_excess"
    market_stress = "market_stress"
    new_business = "new_business"


class AlertSeverity(str, enum.Enum):
    urgent = "urgent"
    info = "info"


alert_kind_enum = SAEnum(AlertKind, name="alert_kind_enum", values_callable=lambda e: [m.value for m in e], native_enum=True, create_type=True)
severity_enum = SAEnum(AlertSeverity, name="alert_severity_enum", values_callable=lambda e: [m.value for m in e], native_enum=True, create_type=True)


class RiskAlert(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "risk_alerts"

    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    as_on: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[AlertKind] = mapped_column(alert_kind_enum, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(severity_enum, nullable=False)
    driver: Mapped[str] = mapped_column(String(64), nullable=False)
    has_plan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    raised_on: Mapped[date] = mapped_column(Date, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    plan_actions: Mapped[list["PlanAction"]] = relationship(
        "PlanAction", back_populates="alert", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("business_id", "as_on", "kind", name="uq_risk_alerts_business_month_kind"),
    )


class PlanActionRole(str, enum.Enum):
    owner = "owner"
    field_officer = "field_officer"


action_role_enum = SAEnum(PlanActionRole, name="plan_action_role_enum", values_callable=lambda e: [m.value for m in e], native_enum=True, create_type=True)


class PlanAction(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "plan_actions"

    alert_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("risk_alerts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[PlanActionRole] = mapped_column(action_role_enum, nullable=False)
    ordinal: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    label_en: Mapped[str] = mapped_column(String(320), nullable=False)
    label_hi: Mapped[str | None] = mapped_column(String(320), nullable=True)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    alert: Mapped[RiskAlert] = relationship("RiskAlert", back_populates="plan_actions")
