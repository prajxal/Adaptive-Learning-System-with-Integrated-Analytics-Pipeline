"""add oauth_states table

Revision ID: 20260331_oauth_states
Revises: 20260331_onboarding
Create Date: 2026-03-31 00:00:00.000000

Replaces the in-process oauth_state_store dict in github_auth.py with a
DB-backed table so OAuth flows work correctly across multiple workers and
survive process restarts.

Schema:
    oauth_states.state      VARCHAR PK — random URL-safe token
    oauth_states.user_id    VARCHAR NOT NULL — internal User.id
    oauth_states.created_at TIMESTAMP NOT NULL DEFAULT now()
    oauth_states.expires_at TIMESTAMP NOT NULL — created_at + 10 min
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260331_oauth_states"
down_revision: Union[str, Sequence[str], None] = "20260331_onboarding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # Check if table already exists
    exists = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'oauth_states'"
        )
    ).fetchone()
    if exists:
        return

    op.create_table(
        "oauth_states",
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("state"),
    )
    op.create_index("ix_oauth_states_state", "oauth_states", ["state"])
    op.create_index("ix_oauth_states_expires_at", "oauth_states", ["expires_at"])


def downgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'oauth_states'"
        )
    ).fetchone()
    if exists:
        op.drop_index("ix_oauth_states_expires_at", table_name="oauth_states")
        op.drop_index("ix_oauth_states_state", table_name="oauth_states")
        op.drop_table("oauth_states")
