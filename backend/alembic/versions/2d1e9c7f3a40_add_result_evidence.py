"""add structured execution evidence

Revision ID: 2d1e9c7f3a40
Revises: 9a1c48e7b2d0
"""
from alembic import op
import sqlalchemy as sa

revision = "2d1e9c7f3a40"
down_revision = "9a1c48e7b2d0"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("test_results", sa.Column("failure_classification", sa.String(), nullable=True))
    op.add_column("test_results", sa.Column("request_metadata", sa.JSON(), nullable=True))
    op.add_column("test_results", sa.Column("response_metadata", sa.JSON(), nullable=True))

def downgrade() -> None:
    op.drop_column("test_results", "response_metadata")
    op.drop_column("test_results", "request_metadata")
    op.drop_column("test_results", "failure_classification")
