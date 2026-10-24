from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.enums import ClassLevel, ContentType, SubjectName
from database import get_db
from models.learning_content import LearningContent
from models.topic import Topic
from repositories.learner_assessment import LearnerAssessmentRepository
from schemas.learner_assessment import (
    LearnerAssessmentCreate,
    LearnerAssessmentSubmit,
    LearnerAssessmentUpdate,
    LearnerAssessmentResponse,
    LearnerLessonOption,
)
from services.ai_service import AIService
from services.learner_assessment import LearnerAssessmentService


router = APIRouter(prefix="/assessments", tags=["Assessments"])


def get_assessment_service(
    db: Session = Depends(get_db),
) -> LearnerAssessmentService:
    return LearnerAssessmentService(
        assessment_repo=LearnerAssessmentRepository(db),
        ai_service=AIService(),
    )


@router.post(
    "/start",
    response_model=LearnerAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_assessment(
    data: LearnerAssessmentCreate,
    service: LearnerAssessmentService = Depends(get_assessment_service),
):
    return await service.start_assessment(data)


@router.post(
    "/{assessment_id}/submit",
    response_model=LearnerAssessmentResponse,
)
async def submit_assessment(
    assessment_id: UUID,
    submit_data: LearnerAssessmentSubmit,
    service: LearnerAssessmentService = Depends(get_assessment_service),
):
    return await service.submit_assessment(assessment_id, submit_data)


@router.get("/", response_model=list[LearnerAssessmentResponse])
async def list_assessments(
    student_id: UUID | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: LearnerAssessmentService = Depends(get_assessment_service),
):
    return await service.list_assessments(student_id, skip, limit)


@router.get(
    "/students/{student_id}/recent-results",
    response_model=list[LearnerAssessmentResponse],
)
async def list_recent_results(
    student_id: UUID,
    limit: int = Query(default=5, ge=1, le=50),
    service: LearnerAssessmentService = Depends(get_assessment_service),
):
    return await service.list_recent_results(student_id, limit)


@router.get("/lessons", response_model=list[LearnerLessonOption])
def list_available_lessons(
    subject_name: SubjectName,
    class_level: ClassLevel,
    db: Session = Depends(get_db),
) -> list[LearnerLessonOption]:
    statement = (
        select(LearningContent, Topic)
        .join(Topic, LearningContent.topic_id == Topic.topic_id)
        .where(
            LearningContent.content_type == ContentType.LESSON,
            Topic.subject_name == subject_name,
            Topic.class_level == class_level,
            Topic.is_active.is_(True),
        )
        .order_by(LearningContent.title)
    )
    return [
        LearnerLessonOption(
            content_id=content.content_id,
            topic_id=topic.topic_id,
            title=content.title or "Untitled lesson",
            subject_name=topic.subject_name,
            class_level=topic.class_level,
            simple_definition=content.simple_definition,
        )
        for content, topic in db.execute(statement).all()
    ]


@router.get(
    "/{assessment_id}",
    response_model=LearnerAssessmentResponse,
)
async def get_assessment(
    assessment_id: UUID,
    service: LearnerAssessmentService = Depends(get_assessment_service),
):
    return await service.get_assessment(assessment_id)


@router.patch(
    "/{assessment_id}",
    response_model=LearnerAssessmentResponse,
)
async def update_assessment(
    assessment_id: UUID,
    data: LearnerAssessmentUpdate,
    service: LearnerAssessmentService = Depends(get_assessment_service),
):
    return await service.update_assessment(assessment_id, data)
