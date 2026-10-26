from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from core.enums import EvaluationStatus, ProgressStatus, SubjectName


class LearnerProgressBase(BaseModel):
    student_id: UUID
    topic_id: UUID
    subject_name: SubjectName
    completion_percentage: int = 0


class LearnerProgressCreate(LearnerProgressBase):
    pass


class LearnerProgressUpdate(BaseModel):
    progress_status: ProgressStatus | None = None
    latest_evaluation: EvaluationStatus | None = None
    recommendation_reason: str | None = None
    completion_percentage: int | None = None


class LearnerProgressResponse(LearnerProgressBase):
    progress_id: UUID
    progress_status: ProgressStatus
    latest_evaluation: EvaluationStatus | None = None
    recommendation_reason: str | None = None
    first_activity_at: datetime | None = None
    last_activity_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
