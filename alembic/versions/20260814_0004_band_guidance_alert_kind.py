"""Add band_guidance to alert_kind_enum

Revision ID: 20260814_0004
Revises: 20260813_0003
Create Date: 2026-08-14
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260814_0004"
down_revision: Union[str, None] = "20260813_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres enum values cannot be removed easily; ADD VALUE is enough.
    # IF NOT EXISTS keeps this idempotent across environments.
    op.execute("ALTER TYPE alert_kind_enum ADD VALUE IF NOT EXISTS 'band_guidance'")


def downgrade() -> None:
    # Enum value removal is intentionally skipped — unsafe with existing rows.
    pass
