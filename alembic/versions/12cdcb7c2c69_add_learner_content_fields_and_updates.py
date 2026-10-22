"""add learner content fields and updates

Revision ID: 12cdcb7c2c69
Revises: 90b6573a97a6
Create Date: 2026-10-22 13:50:34.063136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12cdcb7c2c69'
down_revision: Union[str, Sequence[str], None] = '90b6573a97a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
