"""merge heads

Revision ID: e94d8926c40e
Revises: b71d6a4c2e91, cd9fa274335b
Create Date: 2026-10-25 19:56:14.104348

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "e94d8926c40e"
down_revision: Union[str, Sequence[str], None] = ("b71d6a4c2e91", "cd9fa274335b")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
