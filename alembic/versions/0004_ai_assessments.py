"""ai_assessments table

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "finding_id", sa.Integer(), sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("severity_original", sa.String(16), nullable=False),
        sa.Column("severity_suggested", sa.String(16), nullable=False),
        sa.Column("reasoning", sa.String(4096), nullable=False),
        sa.Column("raw_output", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_assessments")
