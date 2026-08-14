"""officer portal phase 2 — officer_action_steps, contact_log_entries

Revision ID: 20260814_0005
Revises: 20260814_0004
Create Date: 2026-08-14
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260814_0005"
down_revision: Union[str, None] = "20260814_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


row_status = postgresql.ENUM("active", "inactive", "deleted", name="row_status", create_type=False)
action_step_impact_enum = postgresql.ENUM(
    "low", "medium", "high", name="action_step_impact_enum", create_type=False,
)
contact_kind_enum = postgresql.ENUM("visit", "call", name="contact_kind_enum", create_type=False)


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
    action_step_impact_enum.create(bind, checkfirst=True)
    contact_kind_enum.create(bind, checkfirst=True)

    op.create_table(
        "officer_action_steps",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("business_id", sa.BigInteger(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("detail", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("impact", action_step_impact_enum, nullable=False),
        *_audit_columns(),
    )
    op.create_index("ix_officer_action_steps_business_id", "officer_action_steps", ["business_id"])

    op.create_table(
        "contact_log_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("business_id", sa.BigInteger(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", contact_kind_enum, nullable=False),
        sa.Column("note", sa.String(length=500), nullable=False),
        *_audit_columns(),
    )
    op.create_index("ix_contact_log_entries_business_id", "contact_log_entries", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_contact_log_entries_business_id", table_name="contact_log_entries")
    op.drop_table("contact_log_entries")

    op.drop_index("ix_officer_action_steps_business_id", table_name="officer_action_steps")
    op.drop_table("officer_action_steps")

    bind = op.get_bind()
    contact_kind_enum.drop(bind, checkfirst=True)
    action_step_impact_enum.drop(bind, checkfirst=True)
