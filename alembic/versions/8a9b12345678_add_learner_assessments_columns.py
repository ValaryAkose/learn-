"""add learner assessments columns

Revision ID: 8a9b12345678
Revises: 7cb525be3059
Create Date: 2026-10-25 20:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8a9b12345678"
down_revision: Union[str, Sequence[str], None] = "7cb525be3059"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "learner_assessments",
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "learner_assessments",
        sa.Column("target_duration_seconds", sa.Integer(), nullable=True),
    )
    op.add_column(
        "learner_assessments",
        sa.Column("actual_duration_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "learner_assessments",
        sa.Column("accuracy_percentage", sa.Float(), nullable=True),
    )
    op.add_column(
        "learner_assessments", sa.Column("speed_percentage", sa.Float(), nullable=True)
    )
    op.add_column(
        "learner_assessments", sa.Column("identified_gaps", sa.Text(), nullable=True)
    )
    op.add_column(
        "learner_assessments",
        sa.Column(
            "recommendations", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "learner_assessments",
        sa.Column("client_submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "learner_assessments",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("learner_assessments", "completed_at")
    op.drop_column("learner_assessments", "client_submitted_at")
    op.drop_column("learner_assessments", "recommendations")
    op.drop_column("learner_assessments", "identified_gaps")
    op.drop_column("learner_assessments", "speed_percentage")
    op.drop_column("learner_assessments", "accuracy_percentage")
    op.drop_column("learner_assessments", "actual_duration_seconds")
    op.drop_column("learner_assessments", "target_duration_seconds")
    op.drop_column("learner_assessments", "answers")
