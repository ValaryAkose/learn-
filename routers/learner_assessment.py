from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.enums import ClassLevel, SubjectName
from database import get_db
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
    student_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    service: LearnerAssessmentService = Depends(get_assessment_service),
):
    return await service.list_assessments(student_id, skip, limit)


@router.get(
    "/students/{student_id}/recent-results",
    response_model=list[LearnerAssessmentResponse],
)
async def list_recent_results(
    student_id: UUID,
    limit: int = 5,
    service: LearnerAssessmentService = Depends(get_assessment_service),
):
    return await service.list_recent_results(student_id, limit)


@router.get("/lessons", response_model=list[LearnerLessonOption])
async def list_available_lessons(
    subject_name: SubjectName,
    class_level: ClassLevel,
    service: LearnerAssessmentService = Depends(get_assessment_service),
):
    return await service.list_available_lessons(subject_name, class_level)


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
