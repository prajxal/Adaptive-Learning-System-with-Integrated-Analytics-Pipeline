"""add xp and level columns to users, user_skills, courses

Revision ID: 20260330_xp_level
Revises: 67604beb8fae
Create Date: 2026-03-30 00:00:00.000000

Adds the foundational XP / Level schema for the Elo → XP migration (Phase 2).
Existing Elo columns are left intact — this migration is purely additive.

New columns:
    users.total_xp          INTEGER NOT NULL DEFAULT 0
    users.current_level     INTEGER NOT NULL DEFAULT 1
    user_skills.xp          INTEGER NOT NULL DEFAULT 0
    user_skills.level       INTEGER NOT NULL DEFAULT 1
    courses.required_level  INTEGER NOT NULL DEFAULT 1

Safe migration pattern used to avoid statement timeouts on large tables:
    Step 1 — add column as nullable with no default (metadata-only, instant)
    Step 2 — backfill existing rows with UPDATE (batched via the ORM)
    Step 3 — set the server default for future inserts
    Step 4 — add NOT NULL constraint (fast path: all rows already non-null)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260330_xp_level"
down_revision: Union[str, Sequence[str], None] = "67604beb8fae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Column specs: (table, column_name, backfill_value)
_INT_COLUMNS = [
    ("users",       "total_xp",       0),
    ("users",       "current_level",  1),
    ("user_skills", "xp",             0),
    ("user_skills", "level",          1),
    ("courses",     "required_level", 1),
]


def _col_info(conn, table: str, column: str) -> dict | None:
    """Return column metadata dict, or None if the column does not exist.

    Checks: exists, is_nullable, has a server default.
    Uses table_schema = 'public' to avoid cross-schema false positives.
    """
    row = conn.execute(
        sa.text(
            "SELECT is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "  AND table_name   = :t "
            "  AND column_name  = :c"
        ),
        {"t": table, "c": column},
    ).fetchone()
    if row is None:
        return None
    return {"nullable": row[0] == "YES", "has_default": row[1] is not None}


def upgrade() -> None:
    """Add XP / Level columns using a per-step idempotent 4-step pattern.

    Each of the 4 steps checks its own precondition so a partially-applied
    migration (e.g. column exists but is still nullable) is safely resumed
    on the next run.

    Uses SET (session-level) rather than SET LOCAL so that role-level
    statement_timeout settings on hosted providers (Supabase, Render) are
    also overridden.
    """
    conn = op.get_bind()

    # Session-level overrides — must disable both timeouts on hosted providers
    # (Supabase, Render) that enforce statement_timeout AND lock_timeout.
    # "SET" (not SET LOCAL) is used so these survive across any implicit
    # transaction boundaries on pooled connections.
    conn.execute(sa.text("SET statement_timeout = 0"))
    conn.execute(sa.text("SET lock_timeout = 0"))

    try:
        for table, column, fill_value in _INT_COLUMNS:
            info = _col_info(conn, table, column)

            # Step 1: add column as nullable with no default (instant DDL)
            if info is None:
                op.add_column(table, sa.Column(column, sa.Integer(), nullable=True))
                info = {"nullable": True, "has_default": False}

            # Step 2: backfill — covers both fresh adds and columns stranded
            #          by a previous failed migration that never set NOT NULL
            conn.execute(
                sa.text(
                    f"UPDATE {table} SET {column} = :v WHERE {column} IS NULL"
                ),
                {"v": fill_value},
            )

            # Step 3: attach server default so future inserts don't need it
            if not info["has_default"]:
                op.alter_column(table, column, server_default=str(fill_value))

            # Step 4: add NOT NULL constraint (fast — no nulls remain after step 2)
            if info["nullable"]:
                op.alter_column(table, column, nullable=False)

    finally:
        conn.execute(sa.text("RESET lock_timeout"))
        conn.execute(sa.text("RESET statement_timeout"))


def downgrade() -> None:
    """Remove XP / Level columns added in upgrade()."""
    conn = op.get_bind()

    conn.execute(sa.text("SET statement_timeout = 0"))
    conn.execute(sa.text("SET lock_timeout = 0"))
    try:
        for table, column, _ in reversed(_INT_COLUMNS):
            if _col_info(conn, table, column) is not None:
                op.drop_column(table, column)
    finally:
        conn.execute(sa.text("RESET statement_timeout"))
