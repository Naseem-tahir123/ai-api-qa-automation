"""merge multiple heads

Revision ID: db0677f63074
Revises: 71d303c080d9, add_refresh_reset_tokens
Create Date: 2026-08-22 12:11:20.424075

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db0677f63074'
down_revision: Union[str, Sequence[str], None] = ('71d303c080d9', 'add_refresh_reset_tokens')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
