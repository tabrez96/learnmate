"""material page texts

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "material_page",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "material_id",
            sa.Integer(),
            sa.ForeignKey("material.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chapter_id", sa.Integer(), sa.ForeignKey("chapter.id", ondelete="SET NULL")
        ),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "material_id", "page", name="uq_material_page_material_page"
        ),
    )
    op.create_index("ix_material_page_material_id", "material_page", ["material_id"])
    op.create_index("ix_material_page_chapter_id", "material_page", ["chapter_id"])


def downgrade() -> None:
    # SQLite's DROP TABLE also drops the table's indexes.
    op.drop_table("material_page")
