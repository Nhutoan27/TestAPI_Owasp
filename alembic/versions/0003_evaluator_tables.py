"""test_cases, scan_runs, test_results, evidence, findings

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "test_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("endpoint_id", sa.Integer(), sa.ForeignKey("endpoints.id"), nullable=True),
        sa.Column("owasp_id", sa.String(32), nullable=False),
        sa.Column("check_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "scan_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "test_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scan_run_id", sa.Integer(), sa.ForeignKey("scan_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("test_case_id", sa.Integer(), sa.ForeignKey("test_cases.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("severity_base", sa.String(16), nullable=True),
        sa.Column("severity_ai", sa.String(16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "test_result_id",
            sa.Integer(),
            sa.ForeignKey("test_results.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("data", sa.JSON(), nullable=False),
    )

    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "test_result_id",
            sa.Integer(),
            sa.ForeignKey("test_results.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("owasp_id", sa.String(32), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.String(4096), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("findings")
    op.drop_table("evidence")
    op.drop_table("test_results")
    op.drop_table("scan_runs")
    op.drop_table("test_cases")
