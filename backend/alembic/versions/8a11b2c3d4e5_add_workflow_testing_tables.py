"""add workflow testing tables

Revision ID: 8a11b2c3d4e5
Revises: db0677f63074
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8a11b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "db0677f63074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("specification_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("graph", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["specification_id"], ["api_specifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workflow_plans_id"), "workflow_plans", ["id"])
    op.create_index(op.f("ix_workflow_plans_specification_id"), "workflow_plans", ["specification_id"])
    op.create_table(
        "workflow_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("endpoint_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("depends_on", sa.JSON(), nullable=False),
        sa.Column("capture_rules", sa.JSON(), nullable=False),
        sa.Column("injection_rules", sa.JSON(), nullable=False),
        sa.Column("is_cleanup", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["endpoint_id"], ["endpoints.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["workflow_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workflow_steps_id"), "workflow_steps", ["id"])
    op.create_index(op.f("ix_workflow_steps_plan_id"), "workflow_steps", ["plan_id"])
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("runtime_context", sa.JSON(), nullable=False),
        sa.Column("step_results", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["workflow_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workflow_runs_id"), "workflow_runs", ["id"])
    op.create_index(op.f("ix_workflow_runs_plan_id"), "workflow_runs", ["plan_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_workflow_runs_plan_id"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_id"), table_name="workflow_runs")
    op.drop_table("workflow_runs")
    op.drop_index(op.f("ix_workflow_steps_plan_id"), table_name="workflow_steps")
    op.drop_index(op.f("ix_workflow_steps_id"), table_name="workflow_steps")
    op.drop_table("workflow_steps")
    op.drop_index(op.f("ix_workflow_plans_specification_id"), table_name="workflow_plans")
    op.drop_index(op.f("ix_workflow_plans_id"), table_name="workflow_plans")
    op.drop_table("workflow_plans")
