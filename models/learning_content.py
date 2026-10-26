from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import ClassLevel, ContentType, QuestionType, SubjectName
from database import Base


class LearningContent(Base):
    __tablename__ = "learning_content"

    content_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    student_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )

    subject_name: Mapped[SubjectName | None] = mapped_column(
        SQLEnum(SubjectName, name="subject_name"),
        nullable=True,
    )

    class_level: Mapped[ClassLevel | None] = mapped_column(
        SQLEnum(ClassLevel, name="class_level"),
        nullable=True,
    )

    content_series_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        default=uuid4,
    )

    topic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("topics.topic_id"),
        nullable=False,
    )

    content_type: Mapped[ContentType] = mapped_column(
        SQLEnum(ContentType, name="content_type"),
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    content_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    student_question: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ai_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    simple_definition: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    official_definition: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    media_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    gemini_file_ref: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    question_type: Mapped[QuestionType | None] = mapped_column(
        SQLEnum(QuestionType, name="question_type"),
        nullable=True,
    )

    answer_options: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    correct_answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    worked_solution: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    content_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    gemini_file_uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
