"""businesses.officer_id — direct FK to the primary assigned officer

The officer portal tracks an officer's beat via
`officer_enterprise_assignments`; this column is the consumer-facing
inverse — "which officer is the point of contact for this business" —
so Home can render the officer card off a single field on the
`businesses` row without joining through the assignment table.

Revision ID: 20260815_0010
Revises: 20260815_0009
Create Date: 2026-08-15
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260815_0010"
down_revision: Union[str, None] = "20260815_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column(
            "officer_id",
            sa.BigInteger(),
            sa.ForeignKey("officers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_businesses_officer_id", "businesses", ["officer_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_businesses_officer_id", table_name="businesses")
    op.drop_column("businesses", "officer_id")
