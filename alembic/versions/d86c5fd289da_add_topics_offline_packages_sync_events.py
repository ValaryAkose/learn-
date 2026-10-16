"""add topics, offline packages, sync events

Revision ID: d86c5fd289da
Revises: a44ff730eba1
Create Date: 2026-10-15 11:48:09.609123

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "d86c5fd289da"
down_revision: Union[str, Sequence[str], None] = "a44ff730eba1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
