"""drop_skill_profile_skill_id_fk

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-20 14:05:00.000000

Removes the foreign key constraint on skill_profiles.skill_id → courses.id.

The skill synthesizer writes roadmap identifiers (e.g. "python-developer",
"javascript") that are not guaranteed to be valid courses.id values.
The FK was silently blocking inserts.

No data is dropped. Only the constraint is removed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop only the FK constraint — column and data are preserved.
    op.drop_constraint(
        'skill_profiles_skill_id_fkey',
        'skill_profiles',
        type_='foreignkey'
    )


def downgrade() -> None:
    # Recreate the FK (will fail if orphan rows exist — safe to ignore in dev).
    op.create_foreign_key(
        'skill_profiles_skill_id_fkey',
        'skill_profiles',
        'courses',
        ['skill_id'],
        ['id'],
        ondelete='CASCADE'
    )
