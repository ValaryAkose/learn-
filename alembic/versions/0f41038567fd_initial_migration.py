"""initial migration

Revision ID: 0f41038567fd
Revises:
Create Date: 2026-10-22 17:09:03.480739

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "0f41038567fd"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
