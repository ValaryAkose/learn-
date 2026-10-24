from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.enums import ProgressStatus


class LessonProgressUpdate(BaseModel):
    """Fields the learner is allowed to update."""

    status: ProgressStatus
    last_viewed_at: datetime | None = None


class LessonProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lesson_progress_id: UUID
    student_id: UUID
    topic_id: UUID
    content_id: UUID
    status: ProgressStatus
    last_viewed_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime
