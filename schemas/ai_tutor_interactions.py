from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.enums import (
    AssessmentStatus,
    AssessmentType,
    ExplanationMode,
    ProgressStatus,
    QuestionType,
    ResponseStatus,
    SubjectName,
    TutorType,
)


class AITutorInteractionCreate(BaseModel):
    student_id: UUID
    conversation_id: UUID | None = None
    topic_id: UUID | None = None
    content_id: UUID | None = None

    tutor_type: TutorType = TutorType.SUBJECT
    student_query: str = Field(min_length=1)
    explanation_mode: ExplanationMode = ExplanationMode.STANDARD

    ai_response: str = Field(min_length=1)
    model_name: str = Field(min_length=1, max_length=50)

    response_status: ResponseStatus = ResponseStatus.ANSWERED
    is_saved_offline: bool = False


class AITutorInteractionUpdate(BaseModel):
    topic_id: UUID | None = None
    content_id: UUID | None = None
    explanation_mode: ExplanationMode | None = None
    is_saved_offline: bool | None = None


class AITutorInteractionResponse(BaseModel):
    interaction_id: UUID
    conversation_id: UUID
    student_id: UUID
    topic_id: UUID | None
    content_id: UUID | None

    tutor_type: TutorType
    student_query: str
    explanation_mode: ExplanationMode
    ai_response: str
    model_name: str
    response_status: ResponseStatus
    is_saved_offline: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AITutorConversationSummary(BaseModel):
    conversation_id: UUID
    topic_id: UUID | None
    subject_name: SubjectName | None
    conversation_title: str
    interaction_count: int
    created_at: datetime
    is_saved_offline: bool


class AITutorConversationOfflineUpdate(BaseModel):
    is_saved_offline: bool


class AITutorConversationOfflineResponse(BaseModel):
    student_id: UUID
    conversation_id: UUID
    is_saved_offline: bool
    interaction_count: int
    interactions: list[AITutorInteractionResponse]


class LearnerLessonActivity(BaseModel):
    lesson_progress_id: UUID
    content_id: UUID
    topic_id: UUID
    subject_name: SubjectName
    topic_title: str
    lesson_title: str | None
    status: ProgressStatus
    last_viewed_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime


class AvailableQuizQuestion(BaseModel):
    content_id: UUID
    content_series_id: UUID
    topic_id: UUID
    subject_name: SubjectName
    topic_title: str
    title: str | None
    question_type: QuestionType
    question_text: str
    answer_options: list[dict] | None


class LearnerQuizAttempt(BaseModel):
    assessment_id: UUID
    topic_id: UUID | None
    subject_name: SubjectName
    topic_title: str | None
    assessment_type: AssessmentType
    attempt_number: int
    status: AssessmentStatus
    started_at: datetime
    completed_at: datetime | None


class LearnerActivityFeed(BaseModel):
    lesson_progress: list[LearnerLessonActivity]
    available_quiz_questions: list[AvailableQuizQuestion]
    quiz_attempts: list[LearnerQuizAttempt]
    tutor_conversations: list[AITutorConversationSummary]
