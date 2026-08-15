"""officer portal — mobile_e164 becomes optional (auth is email/password,
not phone-based; mobile is now contact-only, addable later via profile edit)

Revision ID: 20260814_0007
Revises: 20260814_0006
Create Date: 2026-08-14
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260815_0009"
down_revision: Union[str, None] = "20260815_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("officers", "mobile_e164", existing_type=sa.String(length=20), nullable=True)


def downgrade() -> None:
    op.alter_column("officers", "mobile_e164", existing_type=sa.String(length=20), nullable=False)
