"""merge heads

Revision ID: 45da12bd2794
Revises: 0f41038567fd, 9d51fb5d6cd0, bdf98ef1db4f
Create Date: 2026-10-23 14:22:42.063792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45da12bd2794'
down_revision: Union[str, Sequence[str], None] = ('0f41038567fd', '9d51fb5d6cd0', 'bdf98ef1db4f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
