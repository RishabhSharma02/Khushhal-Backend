"""per-business savings and loan on businesses

Revision ID: 20260813_0003
Revises: 20260812_0002
Create Date: 2026-08-13
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0003"
down_revision: Union[str, None] = "20260812_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column("savings_inr", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "businesses",
        sa.Column("loan_inr", sa.BigInteger(), nullable=False, server_default="0"),
    )

    # Backfill so existing owners keep the figures they already see. Savings
    # comes from the business's own setup snapshot where there is one, and
    # falls back to the household row the app wrote before savings was
    # per-business. Outstanding loan only ever lived on the user row.
    op.execute(
        sa.text(
            """
            UPDATE businesses b
               SET savings_inr = COALESCE(
                       (SELECT ms.savings
                          FROM monthly_snapshots ms
                         WHERE ms.business_id = b.id
                           AND ms.status <> 'deleted'
                         ORDER BY ms.month DESC, ms.id DESC
                         LIMIT 1),
                       0),
                   loan_inr = COALESCE((SELECT u.loan_inr FROM users u WHERE u.id = b.user_id), 0)
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE businesses b
               SET savings_inr = COALESCE((SELECT u.savings_inr FROM users u WHERE u.id = b.user_id), 0)
             WHERE b.savings_inr = 0
            """
        )
    )


def downgrade() -> None:
    op.drop_column("businesses", "loan_inr")
    op.drop_column("businesses", "savings_inr")
