from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import (
    EvaluationStatus,
    ProgressStatus,
    SubjectName,
)
from database import Base


class LearnerProgress(Base):
    __tablename__ = "learner_progress"

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "topic_id",
            name="uq_learner_progress_student_topic",
        ),
        ForeignKeyConstraint(
            ["topic_id", "subject_name"],
            ["topics.topic_id", "topics.subject_name"],
            name="fk_progress_topic_subject",
        ),
    )

    progress_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    student_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
    )

    subject_name: Mapped[SubjectName] = mapped_column(
        SQLEnum(SubjectName, name="subject_name"),
        nullable=False,
    )

    topic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
    )

    progress_status: Mapped[ProgressStatus] = mapped_column(
        SQLEnum(ProgressStatus, name="progress_status"),
        nullable=False,
        default=ProgressStatus.NOT_STARTED,
    )

    recommendation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    latest_evaluation: Mapped[EvaluationStatus | None] = mapped_column(
        SQLEnum(EvaluationStatus, name="evaluation_status"),
        nullable=True,
    )

    recommended_content_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learning_content.content_id"),
        nullable=True,
    )

    first_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
