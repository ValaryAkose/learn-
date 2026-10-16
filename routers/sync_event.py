from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from core.enums import SyncEventType, SyncStatus
from database import get_db
from repositories.offline_package_repository import OfflinePackageRepository
from repositories.sync_event_repository import SyncEventRepository
from schemas.sync_event import SyncEventCreate, SyncEventResponse
from services.sync_event import SyncEventService

router = APIRouter(prefix="/sync-events", tags=["sync events"])


def get_service(db: Session = Depends(get_db)) -> SyncEventService:
    sync_repo = SyncEventRepository(db)
    package_repo = OfflinePackageRepository(db)
    return SyncEventService(sync_repo, package_repo)


@router.post("", response_model=SyncEventResponse, status_code=status.HTTP_201_CREATED)
def record_sync_event(
    payload: SyncEventCreate,
    response: Response,
    db: Session = Depends(get_db),
    service: SyncEventService = Depends(get_service),
):
    event, created = service.record_event(payload)

    db.commit()

    if not created:
        response.status_code = status.HTTP_200_OK
    return event


@router.get("", response_model=list[SyncEventResponse])
def list_sync_events(
    student_id: UUID | None = None,
    event_type: SyncEventType | None = None,
    sync_status: SyncStatus | None = None,
    package_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: SyncEventService = Depends(get_service),
):
    return service.list_events(
        student_id=student_id,
        event_type=event_type,
        sync_status=sync_status,
        package_id=package_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{sync_id}", response_model=SyncEventResponse)
def get_sync_event(sync_id: UUID, service: SyncEventService = Depends(get_service)):
    return service.get_event(sync_id)
