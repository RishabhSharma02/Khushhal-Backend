"""phase 1 core tables — users, businesses, monthly_snapshots, ledger_entries, sync_events

Revision ID: 20260811_0001
Revises:
Create Date: 2026-08-11
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260811_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- enum definitions (create_type=False so we control CREATE/DROP order) ----
row_status = postgresql.ENUM("active", "inactive", "deleted", name="row_status", create_type=False)
lang_enum = postgresql.ENUM("hi", "en", name="lang_enum", create_type=False)
segment_enum = postgresql.ENUM("shg", "fpo", "own", name="segment_enum", create_type=False)
sector_enum = postgresql.ENUM(
    "dairy", "poultry", "food_processing", "handicrafts", "rural_retail", "other",
    name="sector_enum", create_type=False,
)
tenure_enum = postgresql.ENUM("under_1", "1_to_3", "3_to_10", "10_plus", name="tenure_enum", create_type=False)
basis_enum = postgresql.ENUM("rough", "records", name="basis_enum", create_type=False)
entry_kind_enum = postgresql.ENUM("in", "out", name="entry_kind_enum", create_type=False)
entry_category_enum = postgresql.ENUM(
    "milk_sale", "fodder", "vet", "emi", "other", name="entry_category_enum", create_type=False
)
entry_source_enum = postgresql.ENUM("manual", "voice", name="entry_source_enum", create_type=False)


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
    row_status.create(bind, checkfirst=True)
    lang_enum.create(bind, checkfirst=True)
    segment_enum.create(bind, checkfirst=True)
    sector_enum.create(bind, checkfirst=True)
    tenure_enum.create(bind, checkfirst=True)
    basis_enum.create(bind, checkfirst=True)
    entry_kind_enum.create(bind, checkfirst=True)
    entry_category_enum.create(bind, checkfirst=True)
    entry_source_enum.create(bind, checkfirst=True)

    # ---- users ----
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("language", lang_enum, nullable=False, server_default="hi"),
        sa.Column("state", sa.String(length=80), nullable=True),
        sa.Column("district", sa.String(length=80), nullable=True),
        sa.Column("village", sa.String(length=120), nullable=True),
        sa.Column("savings_inr", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("loan_inr", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_audit_columns(),
        sa.UniqueConstraint("firebase_uid", name="uq_users_firebase_uid"),
        sa.UniqueConstraint("phone_e164", name="uq_users_phone_e164"),
    )
    op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"])
    op.create_index("ix_users_phone_e164", "users", ["phone_e164"])

    # ---- businesses ----
    op.create_table(
        "businesses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("segment", segment_enum, nullable=False),
        sa.Column("sector", sector_enum, nullable=False),
        sa.Column("tenure", tenure_enum, nullable=False),
        sa.Column("staff_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_new_business", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("years_in_operation", sa.Integer(), nullable=False, server_default="0"),
        *_audit_columns(),
        sa.CheckConstraint("staff_count >= 1", name="ck_businesses_staff_count_min"),
    )
    op.create_index("ix_businesses_user_id", "businesses", ["user_id"])
    op.create_index(
        "ix_businesses_user_active", "businesses", ["user_id"],
        postgresql_where=sa.text("status <> 'deleted'"),
    )

    # ---- monthly_snapshots ----
    op.create_table(
        "monthly_snapshots",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("business_id", sa.BigInteger(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("money_in", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("money_out", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("loan_emi", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("savings", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("basis", basis_enum, nullable=False),
        *_audit_columns(),
        sa.UniqueConstraint("business_id", "month", name="uq_monthly_snapshot_business_month"),
    )
    op.create_index("ix_monthly_snapshots_business_id", "monthly_snapshots", ["business_id"])

    # ---- ledger_entries ----
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("business_id", sa.BigInteger(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", entry_kind_enum, nullable=False),
        sa.Column("amount_inr", sa.BigInteger(), nullable=False),
        sa.Column("category", entry_category_enum, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", entry_source_enum, nullable=False, server_default="manual"),
        sa.Column("client_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.CheckConstraint("amount_inr > 0", name="ck_ledger_amount_positive"),
        sa.UniqueConstraint("business_id", "client_entry_id", name="uq_ledger_business_client_entry"),
    )
    op.create_index("ix_ledger_entries_business_id", "ledger_entries", ["business_id"])
    op.create_index("ix_ledger_business_recorded", "ledger_entries", ["business_id", "recorded_at"])

    # ---- sync_events ----
    op.create_table(
        "sync_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_size", sa.Integer(), nullable=False),
        sa.Column("accepted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicates", sa.Integer(), nullable=False, server_default="0"),
        *_audit_columns(),
    )
    op.create_index("ix_sync_events_user_id", "sync_events", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_sync_events_user_id", table_name="sync_events")
    op.drop_table("sync_events")

    op.drop_index("ix_ledger_business_recorded", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_business_id", table_name="ledger_entries")
    op.drop_table("ledger_entries")

    op.drop_index("ix_monthly_snapshots_business_id", table_name="monthly_snapshots")
    op.drop_table("monthly_snapshots")

    op.drop_index("ix_businesses_user_active", table_name="businesses")
    op.drop_index("ix_businesses_user_id", table_name="businesses")
    op.drop_table("businesses")

    op.drop_index("ix_users_phone_e164", table_name="users")
    op.drop_index("ix_users_firebase_uid", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    for e in (
        "entry_source_enum", "entry_category_enum", "entry_kind_enum",
        "basis_enum", "tenure_enum", "sector_enum", "segment_enum",
        "lang_enum", "row_status",
    ):
        sa.Enum(name=e).drop(bind, checkfirst=True)
