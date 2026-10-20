from datetime import datetime, timezone
from uuid import UUID

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
    ) -> None:
        self.repo = sync_repo
        self.package_repo = package_repo

    def get_event(self, sync_id: UUID) -> SyncEvent:
        event = self.repo.get(sync_id)
        if event is None:
            raise NotFoundError("Sync event not found")
        return event

    def list_events(self, **filters) -> list[SyncEvent]:
        return self.repo.list(**filters)

    def record_event(self, payload: SyncEventCreate) -> tuple[SyncEvent, bool]:
        if payload.event_type == SyncEventType.PACKAGE_DOWNLOAD:
            if payload.package_id is None:
                raise BusinessRuleError("package_id is required for package downloads")
            if payload.records_synced != 0:
                raise BusinessRuleError(
                    "records_synced must be 0 for package downloads"
                )
            if payload.event_payload is not None:
                raise BusinessRuleError(
                    "event_payload must be empty for package downloads"
                )
        elif payload.event_type == SyncEventType.PROGRESS_SYNC:
            if payload.package_id is not None:
                raise BusinessRuleError(
                    "package_id cannot be provided for progress syncs"
                )

        if payload.records_synced < 0:
            raise BusinessRuleError("records_synced cannot be negative")

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

        if not self.repo.student_exists(payload.student_id):
            raise NotFoundError("Student not found")

        existing = self.repo.get_by_client_event(
            payload.student_id, payload.client_event_id
        )
        if existing is not None:
            return existing, False

        event = self.repo.create(values)

        return event, True
