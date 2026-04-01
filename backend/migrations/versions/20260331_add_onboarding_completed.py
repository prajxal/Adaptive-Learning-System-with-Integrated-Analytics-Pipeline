"""add onboarding_completed to users

Revision ID: 20260331_onboarding
Revises: 20260330_xp_level
Create Date: 2026-03-31 00:00:00.000000

Adds users.onboarding_completed (BOOLEAN NOT NULL DEFAULT FALSE).
Existing rows are backfilled to FALSE (safe default — re-show onboarding
for all existing users is low-risk and guards against stale data).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260331_onboarding"
down_revision: Union[str, Sequence[str], None] = "20260330_xp_level"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(conn, table: str, column: str) -> bool:
    row = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "  AND table_name   = :t "
            "  AND column_name  = :c"
        ),
        {"t": table, "c": column},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("SET statement_timeout = 0"))
    conn.execute(sa.text("SET lock_timeout = 0"))
    try:
        if not _col_exists(conn, "users", "onboarding_completed"):
            op.add_column("users", sa.Column("onboarding_completed", sa.Boolean(), nullable=True))

        conn.execute(
            sa.text("UPDATE users SET onboarding_completed = FALSE WHERE onboarding_completed IS NULL")
        )
        op.alter_column("users", "onboarding_completed", server_default="false", nullable=False)
    finally:
        conn.execute(sa.text("RESET lock_timeout"))
        conn.execute(sa.text("RESET statement_timeout"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("SET statement_timeout = 0"))
    conn.execute(sa.text("SET lock_timeout = 0"))
    try:
        if _col_exists(conn, "users", "onboarding_completed"):
            op.drop_column("users", "onboarding_completed")
    finally:
        conn.execute(sa.text("RESET statement_timeout"))
