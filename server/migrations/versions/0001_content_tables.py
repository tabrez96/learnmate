"""content tables

Revision ID: 0001
Revises:
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_created_at = lambda: sa.Column(
    "created_at",
    sa.DateTime(),
    server_default=sa.func.current_timestamp(),
    nullable=False,
)


def _cascade(target: str) -> sa.ForeignKey:
    return sa.ForeignKey(target, ondelete="CASCADE")


def upgrade() -> None:
    op.create_table(
        "family",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("child_name", sa.String(100), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger()),
        sa.Column("telegram_link_code", sa.String(32)),
        sa.Column("fallback_hash", sa.String(255)),
        sa.Column("fallback_wrong", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fallback_locked_until", sa.DateTime()),
        sa.Column(
            "outside_books_allowed",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "inactivity_warn_s", sa.Integer(), server_default="240", nullable=False
        ),
        sa.Column(
            "inactivity_lock_s", sa.Integer(), server_default="300", nullable=False
        ),
        _created_at(),
    )
    op.create_table(
        "subject",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(50), nullable=False),
        _created_at(),
    )
    op.create_table(
        "material",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), _cascade("subject.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("status", sa.String(16), server_default="reading", nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("pages_total", sa.Integer()),
        sa.Column("pages_read", sa.Integer(), server_default="0", nullable=False),
        sa.Column("chapters_hint", sa.Text()),
        _created_at(),
        sa.CheckConstraint("kind IN ('upload', 'classroom')", name="ck_material_kind"),
        sa.CheckConstraint(
            "status IN ('reading', 'ready', 'failed')", name="ck_material_status"
        ),
    )
    op.create_index("ix_material_subject_id", "material", ["subject_id"])
    op.create_table(
        "material_file",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("material_id", sa.Integer(), _cascade("material.id"), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("mime", sa.String(100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
    )
    op.create_index("ix_material_file_material_id", "material_file", ["material_id"])
    op.create_table(
        "chapter",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("material_id", sa.Integer(), _cascade("material.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index("ix_chapter_material_id", "chapter", ["material_id"])
    op.create_table(
        "figure",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("material_id", sa.Integer(), _cascade("material.id"), nullable=False),
        sa.Column("chapter_id", sa.Integer(), _cascade("chapter.id")),
        sa.Column("page", sa.Integer()),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
    )
    op.create_index("ix_figure_material_id", "figure", ["material_id"])
    op.create_index("ix_figure_chapter_id", "figure", ["chapter_id"])
    op.create_table(
        "chunk",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("material_id", sa.Integer(), _cascade("material.id"), nullable=False),
        sa.Column("chapter_id", sa.Integer(), _cascade("chapter.id")),
        sa.Column("page", sa.Integer()),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), server_default="text", nullable=False),
        sa.Column("figure_id", sa.Integer(), _cascade("figure.id")),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", sa.LargeBinary()),
        sa.Column("embed_model", sa.String(100)),
        sa.CheckConstraint("kind IN ('text', 'figure')", name="ck_chunk_kind"),
    )
    op.create_index("ix_chunk_material_id", "chunk", ["material_id"])
    op.create_index("ix_chunk_chapter_id", "chunk", ["chapter_id"])
    op.create_table(
        "exam",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), _cascade("subject.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.UniqueConstraint("subject_id", "date", name="uq_exam_subject_date"),
    )
    op.create_index("ix_exam_subject_id", "exam", ["subject_id"])

    op.execute(
        "CREATE VIRTUAL TABLE chunk_fts USING fts5("
        "text, content='chunk', content_rowid='id', tokenize='porter unicode61')"
    )
    op.execute(
        "CREATE TRIGGER chunk_fts_ai AFTER INSERT ON chunk BEGIN "
        "INSERT INTO chunk_fts(rowid, text) VALUES (new.id, new.text); END"
    )
    op.execute(
        "CREATE TRIGGER chunk_fts_ad AFTER DELETE ON chunk BEGIN "
        "INSERT INTO chunk_fts(chunk_fts, rowid, text) "
        "VALUES ('delete', old.id, old.text); END"
    )
    # UPDATE OF text, so re-embedding a chunk does not rewrite the index.
    op.execute(
        "CREATE TRIGGER chunk_fts_au AFTER UPDATE OF text ON chunk BEGIN "
        "INSERT INTO chunk_fts(chunk_fts, rowid, text) "
        "VALUES ('delete', old.id, old.text); "
        "INSERT INTO chunk_fts(rowid, text) VALUES (new.id, new.text); END"
    )


def downgrade() -> None:
    raise NotImplementedError("forward-only; restore from backup instead")
