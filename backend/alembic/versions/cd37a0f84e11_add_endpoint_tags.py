"""persist OpenAPI operation tags

Revision ID: cd37a0f84e11
Revises: 2d1e9c7f3a40
"""
from alembic import op
import sqlalchemy as sa

revision = "cd37a0f84e11"
down_revision = "2d1e9c7f3a40"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("endpoints", sa.Column("tags", sa.JSON(), nullable=True))

def downgrade() -> None:
    op.drop_column("endpoints", "tags")
