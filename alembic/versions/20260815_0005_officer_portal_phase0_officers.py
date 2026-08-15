"""officer portal phase 0 — officers table

Revision ID: 20260814_0003
Revises: 20260812_0002
Create Date: 2026-08-14
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260815_0005"
down_revision: Union[str, None] = "20260814_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


row_status = postgresql.ENUM("active", "inactive", "deleted", name="row_status", create_type=False)


def upgrade() -> None:
    op.create_table(
        "officers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("employee_id", sa.String(length=40), nullable=False),
        sa.Column("employee_id_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mobile_e164", sa.String(length=20), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=True),
        sa.Column("pincode", sa.String(length=10), nullable=True),
        sa.Column("block", sa.String(length=80), nullable=True),
        sa.Column("state", sa.String(length=80), nullable=True),
        sa.Column("device_label", sa.String(length=120), nullable=True),
        sa.Column("creation_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("updation_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("status", row_status, nullable=False, server_default="active"),
        sa.UniqueConstraint("firebase_uid", name="uq_officers_firebase_uid"),
        sa.UniqueConstraint("employee_id", name="uq_officers_employee_id"),
        sa.UniqueConstraint("mobile_e164", name="uq_officers_mobile_e164"),
    )
    op.create_index("ix_officers_firebase_uid", "officers", ["firebase_uid"])
    op.create_index("ix_officers_employee_id", "officers", ["employee_id"])
    op.create_index("ix_officers_mobile_e164", "officers", ["mobile_e164"])

    # Self-referencing audit FKs — added after table creation since the table
    # must exist first (mirrors how AuditMixin's users.id FK works: officers
    # audit each other and themselves, same as users do in phase 1).
    op.create_foreign_key(
        "fk_officers_created_by_officers", "officers", "officers",
        ["created_by"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_officers_updated_by_officers", "officers", "officers",
        ["updated_by"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_officers_updated_by_officers", "officers", type_="foreignkey")
    op.drop_constraint("fk_officers_created_by_officers", "officers", type_="foreignkey")
    op.drop_index("ix_officers_mobile_e164", table_name="officers")
    op.drop_index("ix_officers_employee_id", table_name="officers")
    op.drop_index("ix_officers_firebase_uid", table_name="officers")
    op.drop_table("officers")
