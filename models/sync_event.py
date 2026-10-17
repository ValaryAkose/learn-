from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import SyncEventType, SyncStatus
from database import Base


class SyncEvent(Base):
    __tablename__ = "sync_events"

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "client_event_id",
            name="uq_sync_event_student_client_event",
        ),
    )

    sync_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    client_event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        default=uuid4,
    )

    student_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
    )

    device_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
    )

    event_type: Mapped[SyncEventType] = mapped_column(
        SQLEnum(
            SyncEventType,
            name="sync_event_type",
            values_callable=lambda e: [item.value for item in e],
        ),
        nullable=False,
    )

    sync_status: Mapped[SyncStatus] = mapped_column(
        SQLEnum(
            SyncStatus,
            name="sync_status",
            values_callable=lambda e: [item.value for item in e],
        ),
        nullable=False,
    )

    records_synced: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    package_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("offline_packages.package_id"),
        nullable=True,
    )

    package_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    event_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    client_occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
