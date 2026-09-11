"""add auth profiles and encrypted test identities

Revision ID: e7a4c9d2b631
Revises: d19c2f4e7a10
Create Date: 2026-09-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e7a4c9d2b631"
down_revision = "d19c2f4e7a10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("environment_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("auth_type", sa.String(), nullable=False),
        sa.Column("injection_rules", sa.JSON(), nullable=False),
        sa.Column("login_config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["environment_id"], ["project_environments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_profiles_id"), "auth_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_auth_profiles_environment_id"), "auth_profiles", ["environment_id"], unique=False)
    op.create_table(
        "test_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("auth_profile_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("encrypted_secret", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["auth_profile_id"], ["auth_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_test_identities_id"), "test_identities", ["id"], unique=False)
    op.create_index(op.f("ix_test_identities_auth_profile_id"), "test_identities", ["auth_profile_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_test_identities_auth_profile_id"), table_name="test_identities")
    op.drop_index(op.f("ix_test_identities_id"), table_name="test_identities")
    op.drop_table("test_identities")
    op.drop_index(op.f("ix_auth_profiles_environment_id"), table_name="auth_profiles")
    op.drop_index(op.f("ix_auth_profiles_id"), table_name="auth_profiles")
    op.drop_table("auth_profiles")
