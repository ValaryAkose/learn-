from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import ProgressStatus
from database import Base


class LearnerLessonProgress(Base):
    __tablename__ = "learner_lesson_progress"

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "content_id",
            name="uq_learner_lesson_progress_student_content",
        ),
    )

    lesson_progress_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    student_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
    )

    topic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("topics.topic_id"),
        nullable=False,
    )

    content_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learning_content.content_id"),
        nullable=False,
    )

    status: Mapped[ProgressStatus] = mapped_column(
        SQLEnum(
            ProgressStatus,
            name="lesson_progress_status",
        ),
        nullable=False,
        default=ProgressStatus.NOT_STARTED,
    )

    last_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
