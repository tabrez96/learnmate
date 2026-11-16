"""test, points and AI usage tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _stamp(name: str) -> sa.Column:
    return sa.Column(
        name, sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False
    )


def _cascade(target: str) -> sa.ForeignKey:
    return sa.ForeignKey(target, ondelete="CASCADE")


def upgrade() -> None:
    op.create_table(
        "test",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id", sa.Integer(), sa.ForeignKey("session.id", ondelete="SET NULL")
        ),
        sa.Column(
            "subject_id", sa.Integer(), sa.ForeignKey("subject.id", ondelete="SET NULL")
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column(
            "status", sa.String(16), server_default="in_progress", nullable=False
        ),
        sa.Column("graded", sa.Boolean(), nullable=False),
        sa.Column("current_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("score_pct", sa.Integer()),
        sa.Column("band", sa.String(1)),
        _stamp("created_at"),
        sa.Column("finished_at", sa.DateTime()),
        sa.CheckConstraint(
            "kind IN ('warmup', 'daily', 'weekly', 'surprise', 'test_only', "
            "'challenge', 'bonus')",
            name="ck_test_kind",
        ),
        sa.CheckConstraint(
            "status IN ('in_progress', 'done', 'missed')", name="ck_test_status"
        ),
        sa.CheckConstraint(
            "band IN ('A', 'B', 'C', 'D', 'E', 'F')", name="ck_test_band"
        ),
    )
    op.create_index("ix_test_session_id", "test", ["session_id"])
    op.create_index("ix_test_subject_id", "test", ["subject_id"])
    op.create_table(
        "question",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("test_id", sa.Integer(), _cascade("test.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options_json", sa.Text(), nullable=False),
        sa.Column("correct_index", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.Text()),
        sa.Column(
            "chunk_id", sa.Integer(), sa.ForeignKey("chunk.id", ondelete="SET NULL")
        ),
        sa.Column("answer_index", sa.Integer()),
        sa.Column("answered_at", sa.DateTime()),
    )
    op.create_index("ix_question_test_id", "question", ["test_id"])
    op.create_index("ix_question_chunk_id", "question", ["chunk_id"])
    op.create_table(
        "points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), _cascade("session.id"), nullable=False),
        sa.Column("reason", sa.String(16), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        _stamp("at"),
        sa.CheckConstraint(
            "reason IN ('warmup', 'quick_check', 'test', 'challenge', 'bonus', "
            "'streak')",
            name="ck_points_reason",
        ),
    )
    op.create_index("ix_points_session_id", "points", ["session_id"])
    op.create_table(
        "outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("buttons_json", sa.Text()),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_try_at", sa.DateTime()),
        sa.CheckConstraint("status IN ('pending', 'sent')", name="ck_outbox_status"),
    )
    op.create_table(
        "llm_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        _stamp("at"),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("web_searches", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.CheckConstraint(
            "purpose IN ('read_page', 'chapters', 'rewrite', 'lesson', 'answer', "
            "'outside', 'questions', 'figures')",
            name="ck_llm_usage_purpose",
        ),
    )
    op.create_table(
        "budget_alert",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.CheckConstraint("level IN (80, 100)", name="ck_budget_alert_level"),
        sa.UniqueConstraint("month", "level", name="uq_budget_alert_month_level"),
    )


def downgrade() -> None:
    # SQLite's DROP TABLE also drops the table's indexes.
    op.drop_table("budget_alert")
    op.drop_table("llm_usage")
    op.drop_table("outbox")
    op.drop_table("points")
    op.drop_table("question")
    op.drop_table("test")
