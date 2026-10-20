from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from core.enums import SyncEventType, SyncStatus
from core.exceptions import BusinessRuleError, NotFoundError
from database import get_db
from repositories.offline_package_repository import OfflinePackageRepository
from repositories.sync_event_repository import SyncEventRepository
from schemas.sync_event import SyncEventCreate, SyncEventResponse
from services.sync_event import SyncEventService

router = APIRouter(prefix="/sync-events", tags=["Sync Events"])


async def get_service(db: Session = Depends(get_db)) -> SyncEventService:
    sync_repo = SyncEventRepository(db)
    package_repo = OfflinePackageRepository(db)
    return SyncEventService(sync_repo, package_repo)


@router.post("", response_model=SyncEventResponse)
async def record_sync_event(
    payload: SyncEventCreate,
    response: Response,
    service: SyncEventService = Depends(get_service),
):
    try:
        event, created = service.record_event(payload)
        if not created:
            response.status_code = status.HTTP_200_OK
        else:
            response.status_code = status.HTTP_201_CREATED
        return event
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (BusinessRuleError, ValueError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.get("", response_model=list[SyncEventResponse])
async def list_sync_events(
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
async def get_sync_event(
    sync_id: UUID, service: SyncEventService = Depends(get_service)
):
    try:
        return service.get_event(sync_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
