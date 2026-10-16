from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from core.enums import PackageStatus, SyncEventType, SyncStatus
from core.exceptions import BusinessRuleError, NotFoundError
from models.sync_event import SyncEvent
from repositories.offline_package_repository import OfflinePackageRepository
from repositories.sync_event_repository import SyncEventRepository
from schemas.sync_event import SyncEventCreate


class SyncEventService:
    def __init__(
        self,
        sync_repo: SyncEventRepository,
        package_repo: OfflinePackageRepository,
        db: Session,
    ) -> None:
        self.repo = sync_repo
        self.package_repo = package_repo
        self.db = db

    def get_event(self, sync_id: UUID) -> SyncEvent:
        event = self.repo.get(sync_id)
        if event is None:
            raise NotFoundError("Sync event not found")
        return event

    def list_events(self, **filters) -> list[SyncEvent]:
        return self.repo.list(**filters)

    def record_event(self, payload: SyncEventCreate) -> tuple[SyncEvent, bool]:
        existing = self.repo.get_by_client_event(
            payload.student_id, payload.client_event_id
        )
        if existing is not None:
            return existing, False

        if not self.repo.student_exists(payload.student_id):
            raise NotFoundError("Student not found")

        values = payload.model_dump()

        if payload.event_type == SyncEventType.PACKAGE_DOWNLOAD:
            package = self.package_repo.get(payload.package_id)
            if package is None:
                raise NotFoundError("Offline package not found")

            if (
                payload.sync_status != SyncStatus.FAILED
                and package.status != PackageStatus.PUBLISHED
            ):
                raise BusinessRuleError("Only published packages can be downloaded")

            if values["package_version"] is None:
                values["package_version"] = package.package_version

            values["processed_at"] = datetime.now(timezone.utc)

        event = self.repo.create(values)

        self.db.commit()

        return event, True
