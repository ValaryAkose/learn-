from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import ClassLevel, SubjectName
from database import Base


class Topic(Base):
    __tablename__ = "topics"

    __table_args__ = (
        UniqueConstraint(
            "topic_id",
            "subject_name",
            name="uq_topics_topic_subject",
        ),
    )

    topic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    subject_name: Mapped[SubjectName] = mapped_column(
        SQLEnum(SubjectName, name="subject_name"),
        nullable=False,
    )

    class_level: Mapped[ClassLevel] = mapped_column(
        SQLEnum(ClassLevel, name="class_level"),
        nullable=False,
    )

    term: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    parent_topic_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("topics.topic_id"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    sequence_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
