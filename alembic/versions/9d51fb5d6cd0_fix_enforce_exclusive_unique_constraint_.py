"""fix: enforce exclusive unique constraint on subject_name

Revision ID: 9d51fb5d6cd0
Revises: fca58acd7b8b
Create Date: 2026-10-22 17:48:28.445648

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = '9d51fb5d6cd0'
down_revision: Union[str, Sequence[str], None] = 'fca58acd7b8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
