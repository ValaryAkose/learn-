from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from core.enums import AssessmentStatus, AssessmentType, ClassLevel, SubjectName


class LearnerAssessmentCreate(BaseModel):
    student_id: UUID
    subject_name: SubjectName
    assessment_type: AssessmentType
    content_id: UUID | None = None
    topic_id: UUID | None = None

    client_attempt_id: UUID = Field(default_factory=uuid4)
    question_count: int = Field(default=3, ge=1, le=50)
    target_duration_seconds: int | None = Field(
        default=None,
        gt=0,
    )


class LearnerAssessmentSubmit(BaseModel):
    answers: dict[str, Any] = Field(min_length=1)
    client_submitted_at: datetime | None = None


class LearnerLessonOption(BaseModel):
    content_id: UUID
    topic_id: UUID
    title: str
    subject_name: SubjectName
    class_level: ClassLevel
    simple_definition: str | None = None


class LearnerAssessmentUpdate(BaseModel):
    status: AssessmentStatus | None = None
    identified_gaps: str | None = None
    recommendations: list[dict[str, Any]] | None = None


class LearnerAssessmentResponse(BaseModel):
    assessment_id: UUID
    student_id: UUID
    topic_id: UUID | None
    client_attempt_id: UUID

    assessment_type: AssessmentType
    assessment_version: int
    attempt_number: int
    subject_name: SubjectName
    status: AssessmentStatus

    question_snapshot: list[dict[str, Any]]
    answers: list[dict[str, Any]]
    identified_gaps: str | None
    recommendations: list[dict[str, Any]]

    target_duration_seconds: int | None
    actual_duration_seconds: float | None
    accuracy_percentage: float | None
    speed_percentage: float | None

    started_at: datetime
    client_submitted_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
