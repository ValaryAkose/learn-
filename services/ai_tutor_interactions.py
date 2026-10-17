from uuid import UUID, uuid4

from core.exceptions import BusinessRuleError, NotFoundError
from models.ai_tutor_interaction import AITutorInteraction
from repositories.ai_tutor_interactions import AITutorInteractionRepository
from schemas.ai_tutor_interactions import (
    AITutorConversationSummary,
    AITutorConversationOfflineResponse,
    AITutorInteractionCreate,
    AITutorInteractionResponse,
    AITutorInteractionUpdate,
    AvailableQuizQuestion,
    LearnerActivityFeed,
    LearnerLessonActivity,
    LearnerQuizAttempt,
)


class AITutorInteractionService:
    def __init__(self, repository: AITutorInteractionRepository):
        self.repository = repository

    def create_interaction(
        self,
        data: AITutorInteractionCreate,
    ) -> AITutorInteractionResponse:
        topic_id = data.topic_id
        if data.content_id is not None:
            content = self.repository.get_curriculum_content(data.content_id)
            if content is None:
                raise NotFoundError("Curriculum content not found")
            content_topic_id = content["topic_id"]
            if topic_id is not None and topic_id != content_topic_id:
                raise BusinessRuleError(
                    "The selected topic does not match the curriculum content"
                )
            topic_id = content_topic_id

        interaction = AITutorInteraction(
            conversation_id=data.conversation_id or uuid4(),
            student_id=data.student_id,
            topic_id=topic_id,
            content_id=data.content_id,
            tutor_type=data.tutor_type,
            student_query=data.student_query,
            explanation_mode=data.explanation_mode,
            ai_response=data.ai_response,
            model_name=data.model_name,
            response_status=data.response_status,
            is_saved_offline=data.is_saved_offline,
        )

        saved = self.repository.create(interaction)
        return AITutorInteractionResponse.model_validate(saved)

    def list_conversation_summaries(
        self,
        student_id: UUID,
        search: str | None = None,
        subject_name=None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AITutorConversationSummary]:
        summaries = self.repository.list_conversation_summaries(
            student_id,
            search=search,
            subject_name=subject_name,
            skip=skip,
            limit=limit,
        )
        return [AITutorConversationSummary.model_validate(item) for item in summaries]

    def get_learner_activity(
        self,
        student_id: UUID,
        subject_name=None,
        skip: int = 0,
        limit: int = 100,
    ) -> LearnerActivityFeed:
        return LearnerActivityFeed(
            lesson_progress=[
                LearnerLessonActivity.model_validate(item)
                for item in self.repository.list_lesson_progress(
                    student_id,
                    subject_name=subject_name,
                    skip=skip,
                    limit=limit,
                )
            ],
            available_quiz_questions=[
                AvailableQuizQuestion.model_validate(item)
                for item in self.repository.list_available_quiz_questions(
                    subject_name=subject_name,
                    skip=skip,
                    limit=limit,
                )
            ],
            quiz_attempts=[
                LearnerQuizAttempt.model_validate(item)
                for item in self.repository.list_quiz_attempts(
                    student_id,
                    subject_name=subject_name,
                    skip=skip,
                    limit=limit,
                )
            ],
            tutor_conversations=self.list_conversation_summaries(
                student_id,
                subject_name=subject_name,
                skip=skip,
                limit=limit,
            ),
        )

    def set_conversation_saved_offline(
        self,
        student_id: UUID,
        conversation_id: UUID,
        is_saved_offline: bool,
    ) -> AITutorConversationOfflineResponse | None:
        updated_count = self.repository.set_conversation_saved_offline(
            student_id,
            conversation_id,
            is_saved_offline,
        )
        if updated_count == 0:
            return None

        interactions = self.repository.list_by_conversation(
            conversation_id,
            student_id,
        )
        return AITutorConversationOfflineResponse(
            student_id=student_id,
            conversation_id=conversation_id,
            is_saved_offline=is_saved_offline,
            interaction_count=updated_count,
            interactions=[
                AITutorInteractionResponse.model_validate(item) for item in interactions
            ],
        )

    def get_interaction(
        self,
        interaction_id: UUID,
    ) -> AITutorInteractionResponse | None:
        interaction = self.repository.get_response_by_id(interaction_id)

        if interaction is None:
            return None

        return AITutorInteractionResponse.model_validate(interaction)

    def list_student_interactions(
        self,
        student_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AITutorInteractionResponse]:
        interactions = self.repository.list_by_student(
            student_id,
            skip=skip,
            limit=limit,
        )
        return [
            AITutorInteractionResponse.model_validate(item) for item in interactions
        ]

    def get_conversation(
        self,
        conversation_id: UUID,
        student_id: UUID,
    ) -> list[AITutorInteractionResponse]:
        interactions = self.repository.list_by_conversation(
            conversation_id,
            student_id,
        )
        return [
            AITutorInteractionResponse.model_validate(item) for item in interactions
        ]

    def search_interactions(
        self,
        student_id: UUID,
        search: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AITutorInteractionResponse]:
        interactions = self.repository.search_by_student(
            student_id,
            search,
            skip=skip,
            limit=limit,
        )
        return [
            AITutorInteractionResponse.model_validate(item) for item in interactions
        ]

    def update_interaction(
        self,
        interaction_id: UUID,
        data: AITutorInteractionUpdate,
    ) -> AITutorInteractionResponse | None:
        updated = self.repository.update_by_id(
            interaction_id,
            data.model_dump(exclude_unset=True),
        )
        if updated is None:
            return None
        return AITutorInteractionResponse.model_validate(updated)

    def delete_interaction(self, interaction_id: UUID) -> bool:
        return self.repository.delete(interaction_id)
