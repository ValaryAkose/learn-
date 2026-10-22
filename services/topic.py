from uuid import UUID

from core.enums import ClassLevel, SubjectName
from core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from models.topic import Topic
from repositories.topic_repository import TopicRepository
from schemas.topic import TopicCreate, TopicUpdate


class TopicService:
    def __init__(self, repo: TopicRepository) -> None:
        self.repo = repo

    def get_topic(self, topic_id: UUID) -> Topic:
        topic = self.repo.get(topic_id)
        if topic is None:
            raise NotFoundError("Topic not found")
        return topic

    def list_topics(
        self,
        *,
        subject_name: SubjectName | None,
        class_level: ClassLevel | None,
        term: int | None,
        parent_topic_id: UUID | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> list[Topic]:
        return self.repo.list(
            subject_name=subject_name,
            class_level=class_level,
            term=term,
            parent_topic_id=parent_topic_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

    def create_topic(self, payload: TopicCreate) -> Topic:
        if payload.parent_topic_id is not None:
            parent = self.get_topic(payload.parent_topic_id)
            self._check_parent_matches(
                parent, payload.subject_name, payload.class_level
            )

        existing_combo = self.repo.list(
            subject_name=payload.subject_name,
            class_level=payload.class_level,
            term=None,
            parent_topic_id=None,
            is_active=None,
            limit=1,
            offset=0,
        )
        if existing_combo:
            raise ConflictError(
                f"A topic for {payload.subject_name.value} already exists at level {payload.class_level.value}"
            )

        all_topics = self.repo.list(
            subject_name=None,
            class_level=None,
            term=None,
            parent_topic_id=None,
            is_active=None,
            limit=500,
            offset=0,
        )
        title_matches = [
            t
            for t in all_topics
            if t.title.strip().lower() == payload.title.strip().lower()
        ]
        if title_matches:
            raise ConflictError("That topic title is already in use")

        return self.repo.create(payload.model_dump())

    def update_topic(self, topic_id: UUID, payload: TopicUpdate) -> Topic:
        topic = self.get_topic(topic_id)
        values = payload.model_dump(exclude_unset=True)

        nullable = {"parent_topic_id", "description", "term"}
        values = {k: v for k, v in values.items() if v is not None or k in nullable}

        new_parent_id = values.get("parent_topic_id", topic.parent_topic_id)
        new_subject = values.get("subject_name", topic.subject_name)
        new_level = values.get("class_level", topic.class_level)
        new_title = values.get("title", topic.title)

        if "parent_topic_id" in values and new_parent_id is not None:
            self._check_not_in_own_branch(topic, new_parent_id)

        if "subject_name" in values or "class_level" in values:
            matches = self.repo.list(
                subject_name=new_subject,
                class_level=new_level,
                term=None,
                parent_topic_id=None,
                is_active=None,
                limit=1,
                offset=0,
            )
            if matches and any(m.topic_id != topic_id for m in matches):
                raise ConflictError(
                    f"A topic for {new_subject.value} already exists at level {new_level.value}"
                )

        if (
            "title" in values
            and new_title.strip().lower() != topic.title.strip().lower()
        ):
            all_topics = self.repo.list(
                subject_name=None,
                class_level=None,
                term=None,
                parent_topic_id=None,
                is_active=None,
                limit=500,
                offset=0,
            )
            title_matches = [
                t
                for t in all_topics
                if t.title.strip().lower() == new_title.strip().lower()
                and t.topic_id != topic_id
            ]
            if title_matches:
                raise ConflictError("That topic title is already in use")

        return self.repo.update(topic, values)

    def deactivate_topic(self, topic_id: UUID) -> None:
        topic = self.get_topic(topic_id)
        if topic.is_active:
            self.repo.update(topic, {"is_active": False})

    @staticmethod
    def _check_parent_matches(
        parent: Topic, subject: SubjectName, level: ClassLevel
    ) -> None:
        if parent.subject_name != subject or parent.class_level != level:
            raise BusinessRuleError(
                "A sub-topic must have the same subject and class level as its parent"
            )

    def _check_not_in_own_branch(self, topic: Topic, new_parent_id: UUID) -> None:
        if new_parent_id == topic.topic_id:
            raise BusinessRuleError("A topic cannot be its own parent")

        parent = self.get_topic(new_parent_id)
        self._check_parent_matches(parent, topic.subject_name, topic.class_level)

        seen: set[UUID] = set()
        current: Topic | None = parent
        while current is not None and current.topic_id not in seen:
            if current.topic_id == topic.topic_id:
                raise BusinessRuleError(
                    "That parent would create a loop in the topic tree"
                )
            seen.add(current.topic_id)
            current = (
                self.repo.get(current.parent_topic_id)
                if current.parent_topic_id
                else None
            )
