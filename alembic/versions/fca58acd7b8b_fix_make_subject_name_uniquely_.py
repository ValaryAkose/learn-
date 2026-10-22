"""fix: make subject_name uniquely constrained

Revision ID: fca58acd7b8b
Revises: 90b6573a97a6
Create Date: 2026-10-22 17:45:36.935956

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = 'fca58acd7b8b'
down_revision: Union[str, Sequence[str], None] = '90b6573a97a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
