import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.enums import ClassLevel, ContentType, SubjectName
from models.learning_content import LearningContent


def _to_enum(enum_cls, value):
    if value is None:
        return None
    if isinstance(value, enum_cls):
        return value
    text = str(value).strip().lower()
    for member in enum_cls:
        if text in (member.name.lower(), str(member.value).lower()):
            return member
    return None


class LearningContentRepository:
    def __init__(self, db: Session):
        self.db = db

    async def create(self, content: LearningContent) -> LearningContent:
        self.db.add(content)
        self.db.commit()
        try:
            self.db.refresh(content)
        except Exception:
            return content

        return content

    async def get_by_id(self, content_id: UUID) -> LearningContent | None:
        result = self.db.execute(
            select(LearningContent).where(LearningContent.content_id == content_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self, topic_id: UUID | None = None, skip: int = 0, limit: int = 100
    ) -> list[LearningContent]:
        stmt = select(LearningContent)
        if topic_id:
            stmt = stmt.where(LearningContent.topic_id == topic_id)
        stmt = stmt.offset(skip).limit(limit)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_dictionary_entry_by_word(self, word: str) -> LearningContent | None:
        stmt = select(LearningContent).where(LearningContent.title.ilike(word))
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def update(self, content: LearningContent) -> LearningContent:
        self.db.commit()
        self.db.refresh(content)
        return content

    async def delete(self, content_id: UUID) -> bool:
        content = await self.get_by_id(content_id)
        if not content:
            return False
        self.db.delete(content)
        self.db.commit()
        return True

    async def find_dictionary_chunk(self, term: str) -> str | None:
        words = (term or "").lower().split()
        if not words:
            return None

        name = "[ _]".join(re.escape(word) for word in words)
        heading = rf"(^|\n)##[ \t]+`?{name}`?[ \t\r]*(\n|$)"
        stmt = (
            select(LearningContent.content_text)
            .where(LearningContent.content_type == ContentType.GLOSSARY)
            .where(LearningContent.content_text.op("~*")(heading))
            .limit(1)
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def find_dictionary_entry(
        self,
        term: str,
        subject_name: SubjectName | None = None,
        class_level: ClassLevel | None = None,
    ) -> LearningContent | None:
        normalized = re.sub(r"[^a-z0-9\s-]", " ", (term or "").lower())
        normalized = " ".join(normalized.split())
        if not normalized:
            return None

        subject_member = _to_enum(SubjectName, subject_name)
        level_member = _to_enum(ClassLevel, class_level)

        stmt = select(LearningContent).where(
            LearningContent.content_type == ContentType.GLOSSARY
        )
        if subject_member is not None:
            stmt = stmt.where(LearningContent.subject_name == subject_member)
        if level_member is not None:
            stmt = stmt.where(LearningContent.class_level == level_member)

        result = self.db.execute(stmt)
        entries = list(result.scalars().all())

        if not entries and (subject_member is not None or level_member is not None):
            stmt2 = select(LearningContent).where(
                LearningContent.content_type == ContentType.GLOSSARY
            )
            result2 = self.db.execute(stmt2)
            entries = list(result2.scalars().all())

        for entry in entries:
            title = (entry.title or "").lower().replace("_", " ").replace("-", " ")
            if title == normalized or title in normalized or normalized in title:
                return entry

        for entry in entries:
            text = (entry.content_text or "").lower()
            if normalized in text:
                return entry

        return None
