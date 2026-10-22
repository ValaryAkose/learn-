from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from database import get_db
from models.learner_lesson_progress import LearnerLessonProgress
from models.learner_assessment import LearnerAssessment
from repositories.learner_content_repository import LearningContentRepository
from schemas.learning_content import (
    DictionarySearchRequest,
    LearningContentAskRequest,
    LearningContentCreate,
    LearningContentResponse,
    LearningContentUpdate,
    PracticeGenerateRequest,
    PracticeSubmissionRequest,
)
from services.learning_content_service import LearningContentService

router = APIRouter(prefix="/content", tags=["Learning Content"])


def get_learning_service(db: AsyncSession = Depends(get_db)) -> LearningContentService:
    return LearningContentService(content_repo=LearningContentRepository(db))


@router.get(
    "/lessons/{class_level}/{subject_name}/{topic_slug}", status_code=status.HTTP_200_OK
)
async def get_lesson_content(
    class_level: str,
    subject_name: str,
    topic_slug: str,
    service: LearningContentService = Depends(get_learning_service),
):
    try:
        lesson = await service.get_lesson_content(class_level, subject_name, topic_slug)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        return lesson
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/student/{student_id}/summary", status_code=status.HTTP_200_OK)
async def get_student_progress_summary(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    try:
        completed_lessons_query = (
            select(func.count())
            .select_from(LearnerLessonProgress)
            .where(
                LearnerLessonProgress.student_id == student_id,
                LearnerLessonProgress.is_completed,
            )
        )
        completed_count = (await db.execute(completed_lessons_query)).scalar() or 0
        avg_score_query = select(func.avg(LearnerAssessment.score)).where(
            LearnerAssessment.student_id == student_id
        )
        avg_score = (await db.execute(avg_score_query)).scalar() or 0.0

        return {
            "lessons_completed": completed_count,
            "hours_learning": round(completed_count * 0.5, 1),
            "average_assessment": round(float(avg_score), 1),
            "learning_streak_days": 5,
            "overall_progress_percentage": min(100, int((completed_count / 35) * 100)),
            "topics_mastered": completed_count,
            "total_topics": 35,
            "gaps_count": 2,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/practice/generate", status_code=status.HTTP_200_OK)
async def generate_practice_questions(
    data: PracticeGenerateRequest,
    service: LearningContentService = Depends(get_learning_service),
):
    try:
        ai_service = service._get_ai_service()
        questions = await ai_service.generate_assessment(
            subject_name=data.subject_name,
            class_level=data.class_level,
            assessment_type="practice",
            topic_title=data.topic_title,
            question_count=data.question_count,
        )
        return {"questions": questions}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/practice/evaluate", status_code=status.HTTP_200_OK)
async def evaluate_practice_submission(
    data: PracticeSubmissionRequest,
    service: LearningContentService = Depends(get_learning_service),
):
    try:
        ai_service = service._get_ai_service()
        result = await ai_service.evaluate_submission(
            questions=data.questions,
            student_answers=data.student_answers,
            actual_duration_seconds=data.actual_duration_seconds,
            target_duration_seconds=data.target_duration_seconds,
            subject_name=data.subject_name,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/dictionary/search",
    status_code=status.HTTP_200_OK,
)
async def dictionary_search(
    payload: DictionarySearchRequest,
    service: LearningContentService = Depends(get_learning_service),
):
    result = await service.search_dictionary(payload.query)
    if result is None:
        return {
            "word": payload.query,
            "definition": "Word not found in dictionary",
            "found": False,
        }
    return result


@router.post(
    "/ask-question",
    response_model=LearningContentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ask_learning_question(
    payload: LearningContentAskRequest,
    service: LearningContentService = Depends(get_learning_service),
):
    return await service.ask_question(payload)


@router.get("/", response_model=list[LearningContentResponse])
async def list_all_learning_content(
    topic_id: UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: LearningContentService = Depends(get_learning_service),
):
    return await service.get_all_contents(topic_id=topic_id, skip=skip, limit=limit)


@router.post(
    "/", response_model=LearningContentResponse, status_code=status.HTTP_201_CREATED
)
async def create_learning_content(
    data: LearningContentCreate,
    service: LearningContentService = Depends(get_learning_service),
):
    return await service.create_content(data)


@router.get("/{content_id}", response_model=LearningContentResponse)
async def get_learning_content(
    content_id: UUID,
    service: LearningContentService = Depends(get_learning_service),
):
    content = await service.get_content(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.patch("/{content_id}", response_model=LearningContentResponse)
async def update_learning_content(
    content_id: UUID,
    data: LearningContentUpdate,
    service: LearningContentService = Depends(get_learning_service),
):
    updated = await service.update_content(content_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Content not found")
    return updated


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_learning_content(
    content_id: UUID,
    service: LearningContentService = Depends(get_learning_service),
):
    if not await service.delete_content(content_id):
        raise HTTPException(status_code=404, detail="Content not found")