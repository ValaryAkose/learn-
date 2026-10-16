from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.enums import SyncEventType, SyncStatus
from models.sync_event import SyncEvent
from models.user import User


class SyncEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, sync_id: UUID) -> SyncEvent | None:
        return self.db.get(SyncEvent, sync_id)

    def get_by_client_event(
        self, student_id: UUID, client_event_id: UUID
    ) -> SyncEvent | None:
        stmt = select(SyncEvent).where(
            SyncEvent.student_id == student_id,
            SyncEvent.client_event_id == client_event_id,
        )
        return self.db.scalars(stmt).first()

    def student_exists(self, student_id: UUID) -> bool:
        """Checks if a student exists using a database query."""
        stmt = select(User).where(User.user_id == student_id)
        return self.db.scalars(stmt.limit(1)).first() is not None

    def list(
        self,
        *,
        student_id: UUID | None = None,
        event_type: SyncEventType | None = None,
        sync_status: SyncStatus | None = None,
        package_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SyncEvent]:
        stmt = select(SyncEvent)
        if student_id is not None:
            stmt = stmt.where(SyncEvent.student_id == student_id)
        if event_type is not None:
            stmt = stmt.where(SyncEvent.event_type == event_type)
        if sync_status is not None:
            stmt = stmt.where(SyncEvent.sync_status == sync_status)
        if package_id is not None:
            stmt = stmt.where(SyncEvent.package_id == package_id)
        stmt = stmt.order_by(SyncEvent.received_at.desc()).limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())

    def create(self, values: dict[str, Any]) -> SyncEvent:
        event = SyncEvent(**values)
        self.db.add(event)
        self.db.flush()
        self.db.refresh(event)
        return event
