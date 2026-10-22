from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from database import get_db
from core.enums import SubjectName
from repositories.ai_tutor_interactions import AITutorInteractionRepository
from schemas.ai_tutor_interactions import (
    AITutorConversationOfflineUpdate,
    AITutorConversationOfflineResponse,
    AITutorConversationSummary,
    AITutorInteractionCreate,
    AITutorInteractionResponse,
    AITutorInteractionUpdate,
    LearnerActivityFeed,
)
from services.ai_tutor_interactions import AITutorInteractionService


router = APIRouter(prefix="/ai-tutor", tags=["AI Tutor"])


def get_ai_tutor(
    db: Session = Depends(get_db),
) -> AITutorInteractionService:
    repository = AITutorInteractionRepository(db)
    return AITutorInteractionService(repository)


@router.post(
    "/interactions",
    response_model=AITutorInteractionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_interaction(
    data: AITutorInteractionCreate,
    tutor: AITutorInteractionService = Depends(get_ai_tutor),
):
    return tutor.create_interaction(data)


@router.get(
    "/interactions/{interaction_id}",
    response_model=AITutorInteractionResponse,
)
def get_interaction(
    interaction_id: UUID,
    tutor: AITutorInteractionService = Depends(get_ai_tutor),
):
    return tutor.get_interaction(interaction_id)


@router.get(
    "/students/{student_id}/interactions",
    response_model=list[AITutorInteractionResponse],
)
def list_student_interactions(
    student_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tutor: AITutorInteractionService = Depends(get_ai_tutor),
):
    return tutor.list_student_interactions(
        student_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/students/{student_id}/conversations/{conversation_id}",
    response_model=list[AITutorInteractionResponse],
)
def get_conversation(
    student_id: UUID,
    conversation_id: UUID,
    tutor: AITutorInteractionService = Depends(get_ai_tutor),
):
    return tutor.get_conversation(
        conversation_id,
        student_id,
    )


@router.get(
    "/students/{student_id}/conversations",
    response_model=list[AITutorConversationSummary],
)
def list_conversations(
    student_id: UUID,
    q: str | None = Query(None, min_length=1, max_length=200),
    subject: SubjectName | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tutor: AITutorInteractionService = Depends(get_ai_tutor),
):
    return tutor.list_conversation_summaries(
        student_id,
        search=q,
        subject_name=subject,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/students/{student_id}/activity",
    response_model=LearnerActivityFeed,
)
def get_learner_activity(
    student_id: UUID,
    subject: SubjectName | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tutor: AITutorInteractionService = Depends(get_ai_tutor),
):
    return tutor.get_learner_activity(
        student_id,
        subject_name=subject,
        skip=skip,
        limit=limit,
    )


@router.patch(
    "/students/{student_id}/conversations/{conversation_id}/save-for-offline-use",
    response_model=AITutorConversationOfflineResponse,
)
def set_conversation_offline(
    student_id: UUID,
    conversation_id: UUID,
    data: AITutorConversationOfflineUpdate,
    tutor: AITutorInteractionService = Depends(get_ai_tutor),
):
    return tutor.set_conversation_saved_offline(
        student_id,
        conversation_id,
        data.is_saved_offline,
    )


@router.get(
    "/students/{student_id}/search",
    response_model=list[AITutorInteractionResponse],
)
def search_interactions(
    student_id: UUID,
    q: str = Query(..., min_length=1, max_length=200),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tutor: AITutorInteractionService = Depends(get_ai_tutor),
):
    return tutor.search_interactions(
        student_id,
        q,
        skip=skip,
        limit=limit,
    )


@router.patch(
    "/interactions/{interaction_id}",
    response_model=AITutorInteractionResponse,
)
def update_interaction(
    interaction_id: UUID,
    data: AITutorInteractionUpdate,
    tutor: AITutorInteractionService = Depends(get_ai_tutor),
):
    return tutor.update_interaction(interaction_id, data)


@router.delete(
    "/interactions/{interaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_interaction(
    interaction_id: UUID,
    tutor: AITutorInteractionService = Depends(get_ai_tutor),
):
    tutor.delete_interaction(interaction_id)
