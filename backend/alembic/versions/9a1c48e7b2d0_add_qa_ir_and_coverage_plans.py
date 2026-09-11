"""add persisted QA IR snapshots and coverage plans

Revision ID: 9a1c48e7b2d0
Revises: e7a4c9d2b631
"""
from alembic import op
import sqlalchemy as sa

revision = "9a1c48e7b2d0"
down_revision = "e7a4c9d2b631"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "qa_ir_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("specification_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["specification_id"], ["api_specifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("specification_id"),
    )
    op.create_index("ix_qa_ir_snapshots_specification_id", "qa_ir_snapshots", ["specification_id"])
    op.create_index("ix_qa_ir_snapshots_fingerprint", "qa_ir_snapshots", ["fingerprint"])
    op.create_table(
        "coverage_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("specification_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["specification_id"], ["api_specifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coverage_plans_specification_id", "coverage_plans", ["specification_id"])
    op.create_index("ix_coverage_plans_fingerprint", "coverage_plans", ["fingerprint"])


def downgrade() -> None:
    op.drop_table("coverage_plans")
    op.drop_table("qa_ir_snapshots")
