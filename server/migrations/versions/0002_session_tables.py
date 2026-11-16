"""session tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
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
        "session",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subject_id", sa.Integer(), sa.ForeignKey("subject.id", ondelete="SET NULL")
        ),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(16), server_default="set_up", nullable=False),
        sa.Column("pin_hash", sa.String(255)),
        sa.Column("pin_enc", sa.Text()),
        sa.Column("pin_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("pin_last_sent_at", sa.DateTime()),
        sa.Column("wrong_pins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pin_locked_until", sa.DateTime()),
        _stamp("created_at"),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("ended_at", sa.DateTime()),
        sa.Column("end_reason", sa.String(16)),
        sa.Column("study_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("plan_json", sa.Text()),
        sa.CheckConstraint(
            "type IN ('learn', 'recap', 'test_only')", name="ck_session_type"
        ),
        sa.CheckConstraint(
            "state IN ('set_up', 'running', 'locked', 'ended', 'force_ended', "
            "'cancelled')",
            name="ck_session_state",
        ),
        sa.CheckConstraint(
            "end_reason IN ('pin', 'fallback')", name="ck_session_end_reason"
        ),
    )
    op.create_index("ix_session_subject_id", "session", ["subject_id"])
    op.create_table(
        "session_material",
        sa.Column("session_id", sa.Integer(), _cascade("session.id"), primary_key=True),
        sa.Column(
            "material_id", sa.Integer(), _cascade("material.id"), primary_key=True
        ),
    )
    op.create_table(
        "session_chapter",
        sa.Column("session_id", sa.Integer(), _cascade("session.id"), primary_key=True),
        sa.Column("chapter_id", sa.Integer(), _cascade("chapter.id"), primary_key=True),
    )
    op.create_table(
        "session_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), _cascade("session.id"), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        _stamp("at"),
        sa.Column("data_json", sa.Text()),
        sa.CheckConstraint(
            "type IN ('started', 'left', 'back', 'heartbeat_lost', 'warned', "
            "'locked', 'unlocked', 'wrong_pin', 'pin_locked', 'pin_resent', "
            "'pin_replaced', 'fallback_wrong', 'ended')",
            name="ck_session_event_type",
        ),
    )
    op.create_index("ix_session_event_session_id", "session_event", ["session_id"])
    op.create_table(
        "heartbeat",
        sa.Column("session_id", sa.Integer(), _cascade("session.id"), primary_key=True),
        _stamp("last_at"),
    )
    op.create_table(
        "message",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), _cascade("session.id"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("sources_json", sa.Text()),
        sa.Column("visual_json", sa.Text()),
        sa.Column("outside", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("outside_source_url", sa.Text()),
        sa.Column("retrieval_json", sa.Text()),
        _stamp("created_at"),
        sa.CheckConstraint("role IN ('mentor', 'student')", name="ck_message_role"),
    )
    op.create_index("ix_message_session_id", "message", ["session_id"])


def downgrade() -> None:
    # SQLite's DROP TABLE also drops the table's indexes.
    op.drop_table("message")
    op.drop_table("heartbeat")
    op.drop_table("session_event")
    op.drop_table("session_chapter")
    op.drop_table("session_material")
    op.drop_table("session")
