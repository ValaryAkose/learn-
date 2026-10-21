"""add topics, offline packages, sync events

Revision ID: 90b6573a97a6
Revises: d86c5fd289da
Create Date: 2026-10-15 14:26:16.517705

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "90b6573a97a6"
down_revision: Union[str, Sequence[str], None] = "d86c5fd289da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
