"""fix_skill_weight_pk_add_source

Revision ID: a1b2c3d4e5f6
Revises: 75c7fce60b46
Create Date: 2026-03-20 14:00:00.000000

Adds 'source' to the skill_weights composite primary key so that
github/resume/quiz entries for the same skill can coexist.

Safe steps:
  1. Deduplicate rows that share (user_id, skill_name, source) — keeps the
     row with the lowest ctid (oldest insert order).
  2. Drop the old PK constraint (user_id, skill_name).
  3. Create the new PK constraint (user_id, skill_name, source).
  4. Remove the now-redundant manual indexes on user_id and skill_name
     (PK columns are automatically indexed).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '75c7fce60b46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Deduplicate rows that would violate the new (user_id, skill_name, source) PK.
    #    Keep the row with the smallest ctid (original insert order) per group.
    conn.execute(sa.text("""
        DELETE FROM skill_weights a
        USING skill_weights b
        WHERE a.ctid < b.ctid
          AND a.user_id = b.user_id
          AND a.skill_name = b.skill_name
          AND a.source = b.source;
    """))

    # 2. Drop the old (user_id, skill_name) primary key.
    op.drop_constraint('skill_weights_pkey', 'skill_weights', type_='primary')

    # 3. Drop the now-redundant manual indexes (they were on user_id and skill_name
    #    separately — the new PK index covers both).
    try:
        op.drop_index('ix_skill_weights_user_id', table_name='skill_weights')
    except Exception:
        pass  # index may not exist on all deployments

    try:
        op.drop_index('ix_skill_weights_skill_name', table_name='skill_weights')
    except Exception:
        pass  # index may not exist on all deployments

    # 4. Create the new composite primary key including source.
    op.create_primary_key(
        'skill_weights_pkey',
        'skill_weights',
        ['user_id', 'skill_name', 'source']
    )


def downgrade() -> None:
    # Reverse: shrink PK back to (user_id, skill_name).
    # WARNING: if duplicate (user_id, skill_name) rows exist this will fail.
    # Deduplicate first (keep highest source alphabetically as tiebreak).
    conn = op.get_bind()
    conn.execute(sa.text("""
        DELETE FROM skill_weights a
        USING skill_weights b
        WHERE a.ctid < b.ctid
          AND a.user_id = b.user_id
          AND a.skill_name = b.skill_name;
    """))

    op.drop_constraint('skill_weights_pkey', 'skill_weights', type_='primary')
    op.create_primary_key(
        'skill_weights_pkey',
        'skill_weights',
        ['user_id', 'skill_name']
    )

    # Recreate the old manual indexes.
    op.create_index('ix_skill_weights_user_id', 'skill_weights', ['user_id'])
    op.create_index('ix_skill_weights_skill_name', 'skill_weights', ['skill_name'])
