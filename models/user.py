from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import ClassLevel, ConsentStatus, UserRole
from database import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    learner_code: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    first_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(250),
        nullable=True,
    )

    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role"),
        nullable=False,
    )

    school_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    class_level: Mapped[ClassLevel | None] = mapped_column(
        SQLEnum(ClassLevel, name="class_level"),
        nullable=True,
    )

    class_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    prior_education_background: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    learning_goals: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    device_connectivity: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    consent_status: Mapped[ConsentStatus] = mapped_column(
        SQLEnum(ConsentStatus, name="consent_status"),
        nullable=False,
        default=ConsentStatus.PENDING,
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
