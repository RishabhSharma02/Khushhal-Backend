"""officer portal phase 3 — visits

Revision ID: 20260814_0006
Revises: 20260814_0005
Create Date: 2026-08-14
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260815_0008"
down_revision: Union[str, None] = "20260815_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


row_status = postgresql.ENUM("active", "inactive", "deleted", name="row_status", create_type=False)
visit_risk_level_enum = postgresql.ENUM(
    "healthy", "watch", "atRisk", name="visit_risk_level_enum", create_type=False,
)


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("creation_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("officers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updation_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.BigInteger(), sa.ForeignKey("officers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", row_status, nullable=False, server_default="active"),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    visit_risk_level_enum.create(bind, checkfirst=True)

    op.create_table(
        "visits",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("officer_id", sa.BigInteger(), sa.ForeignKey("officers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_id", sa.BigInteger(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agenda", sa.String(length=400), nullable=False),
        sa.Column("risk_level", visit_risk_level_enum, nullable=True),
        *_audit_columns(),
    )
    op.create_index("ix_visits_officer_id", "visits", ["officer_id"])
    op.create_index("ix_visits_business_id", "visits", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_visits_business_id", table_name="visits")
    op.drop_index("ix_visits_officer_id", table_name="visits")
    op.drop_table("visits")

    bind = op.get_bind()
    visit_risk_level_enum.drop(bind, checkfirst=True)
