from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from repositories.learner_progress_repository import LearnerProgressRepository
from schemas.learners_progress import (
    LearnerProgressCreate,
    LearnerProgressResponse,
)
from services.learner_progress_service import LearnerProgressService

router = APIRouter(prefix="/progress", tags=["learner_progress"])


def get_service(db: Session = Depends(get_db)) -> LearnerProgressService:
    return LearnerProgressService(LearnerProgressRepository(db))


@router.post(
    "/", response_model=LearnerProgressResponse, status_code=status.HTTP_201_CREATED
)
def create_learner_progress(
    payload: LearnerProgressCreate,
    service: LearnerProgressService = Depends(get_service),
):
    return service.create_progress(payload)


@router.get("/", response_model=list[LearnerProgressResponse])
def list_all_progress(
    skip: int = 0,
    limit: int = 100,
    service: LearnerProgressService = Depends(get_service),
):
    return service.list_all_progress(skip=skip, limit=limit)


@router.get("/student/{student_id}", response_model=list[LearnerProgressResponse])
def get_student_progress(
    student_id: UUID,
    service: LearnerProgressService = Depends(get_service),
):
    return service.get_progress(student_id)
