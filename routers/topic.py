from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from core.enums import ClassLevel, SubjectName
from core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from database import get_db
from repositories.topic_repository import TopicRepository
from schemas.topic import TopicCreate, TopicResponse, TopicUpdate
from services.topic import TopicService

router = APIRouter(prefix="/topics", tags=["topics"])


def get_service(db: Session = Depends(get_db)) -> TopicService:
    repo = TopicRepository(db)
    return TopicService(repo)


@router.post("", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(
    payload: TopicCreate,
    service: TopicService = Depends(get_service),
):
    try:
        return service.create_topic(payload)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.get("", response_model=list[TopicResponse])
def list_topics(
    subject_name: SubjectName | None = None,
    class_level: ClassLevel | None = None,
    term: int | None = Query(default=None, ge=1),
    parent_topic_id: UUID | None = None,
    is_active: bool | None = True,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: TopicService = Depends(get_service),
):
    return service.list_topics(
        subject_name=subject_name,
        class_level=class_level,
        term=term,
        parent_topic_id=parent_topic_id,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )


@router.get("/{topic_id}", response_model=TopicResponse)
def get_topic(topic_id: UUID, service: TopicService = Depends(get_service)):
    try:
        return service.get_topic(topic_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{topic_id}", response_model=TopicResponse)
def update_topic(
    topic_id: UUID,
    payload: TopicUpdate,
    service: TopicService = Depends(get_service),
):
    try:
        return service.update_topic(topic_id, payload)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_topic(
    topic_id: UUID,
    service: TopicService = Depends(get_service),
):
    try:
        service.deactivate_topic(topic_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
