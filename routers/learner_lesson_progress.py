from uuid import UUID

from routers.user import get_current_user
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.learner_lesson_progress import (
    LessonProgressResponse,
    LessonProgressUpdate,
)
from services.learner_lesson_progress import (
    LearnerLessonProgressService,
)


router = APIRouter(
    prefix="/lesson-progress",
    tags=["Lesson Progress"],
)


@router.get(
    "/topics/{topic_id}/content/{content_id}",
    response_model=LessonProgressResponse,
)
def get_lesson_progress(
    topic_id: UUID,
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LessonProgressResponse:
    service = LearnerLessonProgressService(db)

    progress = service.get_progress(
        student_id=current_user.user_id,
        topic_id=topic_id,
        content_id=content_id,
    )
    return LessonProgressResponse.model_validate(progress)


@router.post(
    "/topics/{topic_id}/content/{content_id}",
    response_model=LessonProgressResponse,
    status_code=status.HTTP_200_OK,
)
def create_lesson_progress(
    topic_id: UUID,
    content_id: UUID,
    payload: LessonProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LessonProgressResponse:
    service = LearnerLessonProgressService(db)
    progress = service.upsert_progress(
        student_id=current_user.user_id,
        topic_id=topic_id,
        content_id=content_id,
        payload=payload,
    )
    db.commit()
    return LessonProgressResponse.model_validate(progress)


@router.put(
    "/topics/{topic_id}/content/{content_id}",
    response_model=LessonProgressResponse,
    status_code=status.HTTP_200_OK,
)
def save_lesson_progress(
    topic_id: UUID,
    content_id: UUID,
    payload: LessonProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LessonProgressResponse:
    service = LearnerLessonProgressService(db)

    progress = service.upsert_progress(
        student_id=current_user.user_id,
        topic_id=topic_id,
        content_id=content_id,
        payload=payload,
    )
    db.commit()
    return LessonProgressResponse.model_validate(progress)
