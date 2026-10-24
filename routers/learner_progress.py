from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
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
    repo = LearnerProgressRepository(db)
    return LearnerProgressService(repo)


@router.post(
    "/", response_model=LearnerProgressResponse, status_code=status.HTTP_201_CREATED
)
def create_learner_progress(
    payload: LearnerProgressCreate,
    service: LearnerProgressService = Depends(get_service),
):
    try:
        progress = service.create_progress(payload)
        return progress
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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
    progress = service.get_progress(student_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    return progress
