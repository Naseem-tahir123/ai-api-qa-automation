"""add specification sources and project environments

Revision ID: d19c2f4e7a10
Revises: c3503a09f8d6
Create Date: 2026-09-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d19c2f4e7a10"
down_revision = "c3503a09f8d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "api_specifications",
        sa.Column("source_type", sa.String(), nullable=False, server_default="file"),
    )
    op.add_column("api_specifications", sa.Column("source_url", sa.String(), nullable=True))
    op.create_table(
        "project_environments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("is_production", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verify_tls", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_environments_id"), "project_environments", ["id"], unique=False)
    op.create_index(op.f("ix_project_environments_project_id"), "project_environments", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_environments_project_id"), table_name="project_environments")
    op.drop_index(op.f("ix_project_environments_id"), table_name="project_environments")
    op.drop_table("project_environments")
    op.drop_column("api_specifications", "source_url")
    op.drop_column("api_specifications", "source_type")
