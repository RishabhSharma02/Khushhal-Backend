from __future__ import annotations

import enum

from sqlalchemy import BigInteger, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin
from app.models.officer_base import OfficerAuditMixin


class ActionStepImpact(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


action_step_impact_enum = SAEnum(
    ActionStepImpact, name="action_step_impact_enum",
    values_callable=lambda e: [m.value for m in e], native_enum=True, create_type=True,
)


class OfficerActionStep(Base, OfficerAuditMixin, SoftDeleteMixin):
    """An officer-authored step on an enterprise's cash-gap action plan.

    Deliberately separate from the ML-owned `risk_alerts.plan_actions` table
    (see app/models/risk_alert.py) so officer edits here can never be
    overwritten by a scheduled ML recompute.
    """

    __tablename__ = "officer_action_steps"

    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str] = mapped_column(String(400), nullable=False, default="", server_default="")
    impact: Mapped[ActionStepImpact] = mapped_column(action_step_impact_enum, nullable=False)
