"""Add user alias and update learning models

Revision ID: cd9fa274335b
Revises: 45da12bd2794
Create Date: 2026-10-23 15:53:10.427141

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "cd9fa274335b"
down_revision: Union[str, Sequence[str], None] = "45da12bd2794"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
