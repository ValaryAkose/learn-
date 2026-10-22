from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.enums import ClassLevel, SubjectName
from models.topic import Topic


class TopicRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, topic_id: UUID) -> Topic | None:
        return self.db.get(Topic, topic_id)

    def sequence_taken(
        self,
        subject_name: SubjectName,
        class_level: ClassLevel,
        parent_topic_id: UUID | None,
        sequence_no: int,
        exclude_id: UUID | None = None,
    ) -> bool:
        stmt = select(Topic.topic_id).where(
            Topic.subject_name == subject_name,
            Topic.class_level == class_level,
            Topic.sequence_no == sequence_no,
        )
        if parent_topic_id is None:
            stmt = stmt.where(Topic.parent_topic_id.is_(None))
        else:
            stmt = stmt.where(Topic.parent_topic_id == parent_topic_id)
        if exclude_id is not None:
            stmt = stmt.where(Topic.topic_id != exclude_id)
        return self.db.scalars(stmt.limit(1)).first() is not None

    def list(
        self,
        *,
        subject_name: SubjectName | None = None,
        class_level: ClassLevel | None = None,
        term: int | None = None,
        parent_topic_id: UUID | None = None,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Topic]:
        stmt = select(Topic)
        if subject_name is not None:
            stmt = stmt.where(Topic.subject_name == subject_name)
        if class_level is not None:
            stmt = stmt.where(Topic.class_level == class_level)
        if term is not None:
            stmt = stmt.where(Topic.term == term)
        if parent_topic_id is not None:
            stmt = stmt.where(Topic.parent_topic_id == parent_topic_id)
        if is_active is not None:
            stmt = stmt.where(Topic.is_active == is_active)
        stmt = stmt.order_by(Topic.sequence_no).limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())

    def create(self, values: dict[str, Any]) -> Topic:
        topic = Topic(**values)
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)
        return topic

    def update(self, topic: Topic, values: dict[str, Any]) -> Topic:
        for field, value in values.items():
            setattr(topic, field, value)
        self.db.commit()
        self.db.refresh(topic)
        return topic
