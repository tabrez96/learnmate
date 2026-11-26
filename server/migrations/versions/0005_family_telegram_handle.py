"""family telegram handle

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("family", sa.Column("telegram_handle", sa.String(64)))


def downgrade() -> None:
    with op.batch_alter_table("family") as b:
        b.drop_column("telegram_handle")
