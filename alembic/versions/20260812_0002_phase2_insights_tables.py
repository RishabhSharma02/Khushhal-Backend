"""phase 2 insights tables — health_scores, forecasts, risk_alerts, plan_actions

Revision ID: 20260812_0002
Revises: 20260811_0001
Create Date: 2026-08-12
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260812_0002"
down_revision: Union[str, None] = "20260811_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


row_status = postgresql.ENUM("active", "inactive", "deleted", name="row_status", create_type=False)
risk_enum = postgresql.ENUM("low", "medium", "high", name="risk_enum", create_type=False)
band_enum = postgresql.ENUM("green", "amber", "red", name="band_enum", create_type=False)
alert_kind_enum = postgresql.ENUM(
    "savings_low", "liquidity_debt_stress", "climate_deficit",
    "climate_excess", "market_stress", "new_business",
    name="alert_kind_enum", create_type=False,
)
alert_severity_enum = postgresql.ENUM("urgent", "info", name="alert_severity_enum", create_type=False)
plan_action_role_enum = postgresql.ENUM("owner", "field_officer", name="plan_action_role_enum", create_type=False)


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("creation_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updation_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", row_status, nullable=False, server_default="active"),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    risk_enum.create(bind, checkfirst=True)
    band_enum.create(bind, checkfirst=True)
    alert_kind_enum.create(bind, checkfirst=True)
    alert_severity_enum.create(bind, checkfirst=True)
    plan_action_role_enum.create(bind, checkfirst=True)

    op.create_table(
        "health_scores",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("business_id", sa.BigInteger(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("as_on", sa.Date(), nullable=False),
        sa.Column("next_update", sa.Date(), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("risk", risk_enum, nullable=False),
        sa.Column("delta", sa.SmallInteger(), nullable=True),
        sa.Column("days_written", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("days_in_month", sa.SmallInteger(), nullable=False, server_default="30"),
        sa.Column("band", band_enum, nullable=False),
        sa.Column("p_green", sa.Numeric(4, 3), nullable=False),
        sa.Column("p_amber", sa.Numeric(4, 3), nullable=False),
        sa.Column("p_red", sa.Numeric(4, 3), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        *_audit_columns(),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_health_scores_score_range"),
        sa.UniqueConstraint("business_id", "as_on", name="uq_health_scores_business_month"),
    )
    op.create_index("ix_health_scores_business_id", "health_scores", ["business_id"])

    op.create_table(
        "forecasts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("business_id", sa.BigInteger(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("as_on", sa.Date(), nullable=False),
        sa.Column("horizon", sa.SmallInteger(), nullable=False),
        sa.Column("cf_pred", sa.Numeric(14, 2), nullable=False),
        sa.Column("in_level", sa.Numeric(4, 3), nullable=False, server_default="0"),
        sa.Column("out_level", sa.Numeric(4, 3), nullable=False, server_default="0"),
        sa.Column("is_risk_month", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_audit_columns(),
        sa.CheckConstraint("horizon >= 1 AND horizon <= 6", name="ck_forecasts_horizon_range"),
        sa.UniqueConstraint("business_id", "as_on", "horizon", name="uq_forecasts_business_month_horizon"),
    )
    op.create_index("ix_forecasts_business_id", "forecasts", ["business_id"])

    op.create_table(
        "risk_alerts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("business_id", sa.BigInteger(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("as_on", sa.Date(), nullable=False),
        sa.Column("kind", alert_kind_enum, nullable=False),
        sa.Column("severity", alert_severity_enum, nullable=False),
        sa.Column("driver", sa.String(length=64), nullable=False),
        sa.Column("has_plan", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("raised_on", sa.Date(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.UniqueConstraint("business_id", "as_on", "kind", name="uq_risk_alerts_business_month_kind"),
    )
    op.create_index("ix_risk_alerts_business_id", "risk_alerts", ["business_id"])
    op.create_index(
        "ix_risk_alerts_business_raised", "risk_alerts", ["business_id", "raised_on"],
        postgresql_where=sa.text("status <> 'deleted' AND resolved_at IS NULL"),
    )

    op.create_table(
        "plan_actions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("alert_id", sa.BigInteger(), sa.ForeignKey("risk_alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", plan_action_role_enum, nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("label_en", sa.String(length=320), nullable=False),
        sa.Column("label_hi", sa.String(length=320), nullable=True),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
    )
    op.create_index("ix_plan_actions_alert_id", "plan_actions", ["alert_id"])


def downgrade() -> None:
    op.drop_index("ix_plan_actions_alert_id", table_name="plan_actions")
    op.drop_table("plan_actions")

    op.drop_index("ix_risk_alerts_business_raised", table_name="risk_alerts")
    op.drop_index("ix_risk_alerts_business_id", table_name="risk_alerts")
    op.drop_table("risk_alerts")

    op.drop_index("ix_forecasts_business_id", table_name="forecasts")
    op.drop_table("forecasts")

    op.drop_index("ix_health_scores_business_id", table_name="health_scores")
    op.drop_table("health_scores")

    bind = op.get_bind()
    for name in ("plan_action_role_enum", "alert_severity_enum", "alert_kind_enum", "band_enum", "risk_enum"):
        sa.Enum(name=name).drop(bind, checkfirst=True)
