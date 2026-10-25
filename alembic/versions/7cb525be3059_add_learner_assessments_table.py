"""add learner assessments table

Revision ID: 7cb525be3059
Revises: e94d8926c40e
Create Date: 2026-10-25 19:58:17.711035

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "7cb525be3059"
down_revision: Union[str, Sequence[str], None] = "e94d8926c40e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
