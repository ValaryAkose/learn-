from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.enums import (
    ClassLevel,
    ContentType,
    ExplanationMode,
    QuestionType,
    SubjectName,
)


class LearningContentBase(BaseModel):
    student_id: UUID | None = None
    subject_name: SubjectName | None = None
    class_level: ClassLevel | None = None
    content_series_id: UUID | None = None
    topic_id: UUID
    content_type: ContentType
    title: str | None = None
    content_text: str
    student_question: str | None = None
    ai_response: str | None = None
    simple_definition: str | None = None
    official_definition: str | None = None
    media_url: str | None = None
    gemini_file_ref: str | None = None
    question_type: QuestionType | None = None
    answer_options: list[dict[str, Any]] | None = None
    correct_answer: str | None = None
    worked_solution: str | None = None
    content_data: dict[str, Any] | None = None
    version: int = 1


class LearningContentCreate(LearningContentBase):
    pass


class LearningContentAskRequest(BaseModel):
    student_id: UUID
    student_question: str = Field(
        ..., min_length=1, description="What do you want to learn today?"
    )
    subject_name: SubjectName
    class_level: ClassLevel
    topic_id: UUID | None = None
    topic_title: str | None = None
    conversation_id: UUID | None = None
    explanation_mode: ExplanationMode = ExplanationMode.SIMPLE


class LearningContentUpdate(BaseModel):
    content_series_id: UUID | None = None
    topic_id: UUID | None = None
    content_type: ContentType | None = None
    title: str | None = None
    content_text: str | None = None
    student_question: str | None = None
    ai_response: str | None = None
    simple_definition: str | None = None
    official_definition: str | None = None
    media_url: str | None = None
    gemini_file_ref: str | None = None
    question_type: QuestionType | None = None
    answer_options: list[dict[str, Any]] | None = None
    correct_answer: str | None = None
    worked_solution: str | None = None
    content_data: dict[str, Any] | None = None
    version: int | None = None


class LearningContentResponse(LearningContentBase):
    content_id: UUID
    gemini_file_uploaded_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DictionarySearchRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, description="Word or phrase to look up in the dictionary"
    )


class DictionarySearchResponse(BaseModel):
    word: str
    definition: str
    phonetic: str | None = None
    partOfSpeech: str | None = None
    example: str | None = None
    synonyms: list[str] | None = []


class PracticeGenerateRequest(BaseModel):
    subject_name: SubjectName
    class_level: ClassLevel
    topic_title: str = Field(..., min_length=1)
    question_count: int = Field(5, ge=1, le=20)


class PracticeSubmissionRequest(BaseModel):
    questions: list[dict[str, Any]]
    student_answers: dict[str, Any]
    actual_duration_seconds: int = Field(..., ge=0)
    target_duration_seconds: int = Field(..., ge=0)
    subject_name: SubjectName | None = None
