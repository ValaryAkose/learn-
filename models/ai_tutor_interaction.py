from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import (
    ExplanationMode,
    ResponseStatus,
    TutorType,
)
from database import Base


class AITutorInteraction(Base):
    __tablename__ = "ai_tutor_interactions"

    interaction_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    conversation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
    )

    student_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
    )

    topic_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("topics.topic_id"),
        nullable=True,
    )

    content_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learning_content.content_id"),
        nullable=True,
    )

    tutor_type: Mapped[TutorType] = mapped_column(
        SQLEnum(
            TutorType,
            name="tutor_type",
            values_callable=lambda e: [item.value for item in e],
        ),
        nullable=False,
    )

    student_query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    explanation_mode: Mapped[ExplanationMode] = mapped_column(
        SQLEnum(
            ExplanationMode,
            name="explanation_mode",
            values_callable=lambda e: [item.value for item in e],
        ),
        nullable=False,
    )

    ai_response: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    model_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    response_status: Mapped[ResponseStatus] = mapped_column(
        SQLEnum(
            ResponseStatus,
            name="response_status",
            values_callable=lambda e: [item.value for item in e],
        ),
        nullable=False,
        default=ResponseStatus.ANSWERED,
    )

    is_saved_offline: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
