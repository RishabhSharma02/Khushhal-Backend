"""officer portal phase 1 — officer_enterprise_assignments, enterprise_contacts

Revision ID: 20260814_0004
Revises: 20260814_0003
Create Date: 2026-08-14
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260814_0004"
down_revision: Union[str, None] = "20260814_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


row_status = postgresql.ENUM("active", "inactive", "deleted", name="row_status", create_type=False)


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("creation_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("officers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updation_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.BigInteger(), sa.ForeignKey("officers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", row_status, nullable=False, server_default="active"),
    ]


def upgrade() -> None:
    op.create_table(
        "officer_enterprise_assignments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("officer_id", sa.BigInteger(), sa.ForeignKey("officers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_id", sa.BigInteger(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        *_audit_columns(),
        sa.UniqueConstraint("officer_id", "business_id", name="uq_officer_enterprise_assignment"),
    )
    op.create_index("ix_officer_enterprise_assignments_officer_id", "officer_enterprise_assignments", ["officer_id"])
    op.create_index("ix_officer_enterprise_assignments_business_id", "officer_enterprise_assignments", ["business_id"])

    op.create_table(
        "enterprise_contacts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("business_id", sa.BigInteger(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=60), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("language", sa.String(length=40), nullable=False),
        sa.Column("best_time", sa.String(length=60), nullable=False, server_default=""),
        *_audit_columns(),
        sa.UniqueConstraint("business_id", name="uq_enterprise_contacts_business"),
    )


def downgrade() -> None:
    op.drop_table("enterprise_contacts")
    op.drop_index("ix_officer_enterprise_assignments_business_id", table_name="officer_enterprise_assignments")
    op.drop_index("ix_officer_enterprise_assignments_officer_id", table_name="officer_enterprise_assignments")
    op.drop_table("officer_enterprise_assignments")
