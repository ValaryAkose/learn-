"""add ai tutor interactions

Revision ID: bdf98ef1db4f
Revises: d86c5fd289da
Create Date: 2026-10-20 14:11:22.231221

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "bdf98ef1db4f"
down_revision: Union[str, Sequence[str], None] = "d86c5fd289da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
