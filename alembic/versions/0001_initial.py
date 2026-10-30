"""initial schema: projects, api_specs, endpoints, parameters

Revision ID: 0001
Revises:
Create Date: 2026-10-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target_base_url", sa.String(2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "api_specs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("raw_content", sa.JSON(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "endpoints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_spec_id", sa.Integer(), sa.ForeignKey("api_specs.id"), nullable=False),
        sa.Column("method", sa.String(16), nullable=False),
        sa.Column("path", sa.String(2048), nullable=False),
        sa.Column("operation_id", sa.String(255), nullable=False),
        sa.Column("summary", sa.String(1024), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
    )

    op.create_table(
        "parameters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("endpoint_id", sa.Integer(), sa.ForeignKey("endpoints.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location", sa.String(16), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("schema_json", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("parameters")
    op.drop_table("endpoints")
    op.drop_table("api_specs")
    op.drop_table("projects")
