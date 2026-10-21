from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from core.enums import SyncEventType, SyncStatus
from schemas.sync_event import SyncEventCreate, SyncEventResponse
from services.sync_event import SyncEventService
from database import get_db
from sqlalchemy.orm import Session
from repositories.sync_event_repository import SyncEventRepository
from repositories.offline_package_repository import OfflinePackageRepository

router = APIRouter(prefix="/sync-events", tags=["Sync Events"])


def get_service(db: Session = Depends(get_db)) -> SyncEventService:
    sync_repo = SyncEventRepository(db)
    package_repo = OfflinePackageRepository(db)
    return SyncEventService(sync_repo, package_repo)


@router.post("", response_model=SyncEventResponse, status_code=status.HTTP_201_CREATED)
def record_sync_event(
    payload: SyncEventCreate,
    service: SyncEventService = Depends(get_service),
):

    event, _ = service.record_event(payload)
    return event


@router.get("", response_model=list[SyncEventResponse])
def list_sync_events(
    student_id: Optional[UUID] = Query(None),
    event_type: Optional[SyncEventType] = Query(None),
    sync_status: Optional[SyncStatus] = Query(None),
    package_id: Optional[UUID] = Query(None),
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
