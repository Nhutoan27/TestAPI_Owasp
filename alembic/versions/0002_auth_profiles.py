"""auth_profiles table

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("login_url", sa.String(2048), nullable=True),
        sa.Column("credentials", sa.JSON(), nullable=False),
        sa.Column("token_path", sa.String(255), nullable=False),
        sa.Column("static_token", sa.String(2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("auth_profiles")
