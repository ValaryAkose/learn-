from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.enums import ClassLevel, SubjectName


class TopicBase(BaseModel):
    subject_name: SubjectName
    class_level: ClassLevel
    term: Optional[int] = Field(default=None, ge=1, le=3)
    parent_topic_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=150)
    sequence_no: int = Field(..., ge=1)
    description: Optional[str] = None
    is_active: bool = True


class TopicCreate(TopicBase):
    pass


class TopicUpdate(BaseModel):
    term: Optional[int] = Field(default=None, ge=1, le=3)
    parent_topic_id: Optional[UUID] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    sequence_no: Optional[int] = Field(default=None, ge=1)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TopicResponse(TopicBase):
    model_config = ConfigDict(from_attributes=True)

    topic_id: UUID
    created_at: datetime
