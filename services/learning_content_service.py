import os
import re
from datetime import datetime
from uuid import UUID, uuid4

from core.config import DEFAULT_GENERAL_TOPIC_ID, PLACEHOLDER_TOPIC_IDS
from core.enums import ContentType
from models.learning_content import LearningContent
from models.topic import Topic
from repositories.learner_content_repository import LearningContentRepository
from schemas.learning_content import (
    LearningContentAskRequest,
    LearningContentCreate,
    LearningContentUpdate,
)
from services.ai_service import AIService
from services.mock_ai_service import MockAIService
from sqlalchemy import select

PART_OF_SPEECH_NAMES = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "s": "adjective",
    "r": "adverb",
}


class LearningContentService:
    def __init__(self, content_repo: LearningContentRepository):
        self.content_repo = content_repo
        self.ai_service: AIService | MockAIService | None = None

    def _get_ai_service(self) -> AIService | MockAIService:
        if self.ai_service is None:
            mock_flag = os.getenv("MOCK_AI", "false").lower()
            if mock_flag in ("1", "true", "yes"):
                self.ai_service = MockAIService()
            else:
                try:
                    self.ai_service = AIService()
                except RuntimeError:
                    self.ai_service = MockAIService()

        return self.ai_service

    def _is_dictionary_question(self, question: str) -> bool:
        question_text = (question or "").strip().lower()
        markers = (
            "what is the meaning of",
            "what does",
            "mean?",
            "meaning of",
            "define",
            "definition of",
            "what is",
        )
        return any(marker in question_text for marker in markers)

    def _find_curriculum_illustration(
        self, subject_name: str, class_level: str, question: str
    ) -> str | None:
        question_lower = (question or "").lower()
        if "liver" in question_lower or "digestive" in question_lower:
            sub = subject_name or "Biology"
            lvl = class_level or "S1"
            return f"/curriculum/{lvl}/{sub}/0_LEVEL_BIOLOGY_NOTES/images/page_001_image_01.jpeg"

        return None

    async def _answer_dictionary_question(
        self, data: LearningContentAskRequest
    ) -> dict | None:
        if not self._is_dictionary_question(data.student_question):
            return None

        question_text = (data.student_question or "").strip()
        term = None

        patterns = [
            r"(?:what is the meaning of|meaning of|definition of|give me the meaning of)\s+(.+?)\??\$",
            r"(?:what does)\s+(.+?)\s+mean\??\$",
            r"(?:define)\s+(.+?)\??\$",
            r"^(.+?)\$",
        ]

        for pat in patterns:
            m = re.search(pat, question_text, flags=re.IGNORECASE)
            if m:
                term = m.group(1).strip(" \"'`?.")
                if term:
                    break

        search_term = term or question_text

        entry = await self.content_repo.find_dictionary_entry(
            search_term,
            subject_name=data.subject_name,
            class_level=data.class_level,
        )
        if entry is None:
            return None
        definition = entry.content_text.strip()
        if definition:
            lines = [line.strip() for line in definition.splitlines() if line.strip()]
            if lines:
                filtered = []
                for line in lines:
                    if line.startswith("#") or line.startswith("##"):
                        continue
                    if line.startswith("- Definition:"):
                        definition = line.split(":", 1)[1].strip()
                        break
                    filtered.append(line)
                if not definition:
                    definition = filtered[0] if filtered else entry.content_text.strip()

        return {
            "response": definition or "I could not find a definition for that word.",
            "model_name": "dictionary-local",
            "is_out_of_curriculum": False,
        }

    def _extract_headword(self, query: str) -> str:
        pattern = os.getenv("DICTIONARY_QUERY_NOISE_PATTERN", "")
        text = query or ""
        if pattern:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        return " ".join(text.strip(" \"'`?.!").lower().split())

    def _parse_entry(self, chunk: str, term: str) -> dict | None:
        name = "[ _]".join(re.escape(word) for word in term.split())
        section = re.search(
            rf"(?:^|\n)##[ \t]+`?{name}`?[ \t\r]*\n(.*?)(?=\n##[ \t]|\Z)",
            chunk,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if section is None:
            return None

        fields: dict[str, str] = {}
        examples: list[str] = []
        current = None
        for line in section.group(1).splitlines():
            top = re.match(r"^-[ \t]+([^:]+):[ \t]*(.*)$", line)
            if top:
                current = top.group(1).strip().lower()
                fields.setdefault(current, top.group(2).strip())
                continue
            nested = re.match(r"^[ \t]+-[ \t]+(.*)$", line)
            if nested and current in ("examples", "example"):
                examples.append(nested.group(1).strip())

        definition = (
            fields.get("definition")
            or fields.get("easy meaning")
            or fields.get("meaning")
        )
        if not definition:
            return None

        pos_code = fields.get("part of speech", "").strip("` ").lower()
        raw_synonyms = fields.get("synonyms") or fields.get("lemmas") or ""
        synonyms = [
            item.strip(" `") for item in raw_synonyms.split(",") if item.strip(" `")
        ]

        return {
            "word": term,
            "definition": definition,
            "phonetic": None,
            "partOfSpeech": PART_OF_SPEECH_NAMES.get(pos_code, pos_code or None),
            "example": examples[0] if examples else None,
            "synonyms": synonyms,
        }

    async def search_dictionary(self, query: str) -> dict | None:
        term = self._extract_headword(query)
        if not term:
            return None
        chunk = await self.content_repo.find_dictionary_chunk(term)
        if chunk is None:
            return None
        return self._parse_entry(chunk, term)

    async def get_all_contents(
        self,
        topic_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        return await self.content_repo.list_all(
            topic_id=topic_id, skip=skip, limit=limit
        )

    async def get_lesson_content(
        self, class_level: str, subject_name: str, topic_slug: str
    ) -> dict | None:
        media_url = self._find_curriculum_illustration(
            subject_name, class_level, topic_slug
        )
        return {
            "title": topic_slug.replace("-", " ").title(),
            "content_text": f"Approved curriculum notes for {topic_slug.replace('-', ' ')} under {subject_name} ({class_level}).",
            "media_url": media_url,
            "progress_percentage": 30,
        }

    async def create_content(self, data: LearningContentCreate):
        content = LearningContent(**data.model_dump())
        return await self.content_repo.create(content)

    async def _resolve_topic_id(
        self,
        topic_id: UUID | None,
        subject_name: str | None = None,
        class_level: str | None = None,
    ) -> UUID:
        if topic_id is not None and topic_id not in PLACEHOLDER_TOPIC_IDS:
            return topic_id

        if subject_name and hasattr(self.content_repo, "db"):
            try:
                stmt = select(Topic).where(Topic.subject_name.ilike(str(subject_name)))
                if class_level:
                    stmt = stmt.where(Topic.class_level.ilike(str(class_level)))
                
                result = self.content_repo.db.execute(stmt).scalars().first()
                if result:
                    return result.topic_id
            except Exception:
                pass

        if hasattr(self.content_repo, "db"):
            try:
                any_topic = self.content_repo.db.execute(select(Topic)).scalars().first()
                if any_topic:
                    return any_topic.topic_id
            except Exception:
                pass

        get_default_topic_id = getattr(self.content_repo, "get_default_topic_id", None)
        if callable(get_default_topic_id):
            default_id = await get_default_topic_id()
            if default_id:
                return default_id

        return DEFAULT_GENERAL_TOPIC_ID

    async def ask_question(self, data: LearningContentAskRequest):
        topic_id = await self._resolve_topic_id(
            data.topic_id, data.subject_name, data.class_level
        )

        matched_media_url = self._find_curriculum_illustration(
            subject_name=data.subject_name,
            class_level=data.class_level,
            question=data.student_question,
        )

        dictionary_answer = await self._answer_dictionary_question(data)
        if dictionary_answer is not None:
            return {
                "content_id": uuid4(),
                "student_id": data.student_id,
                "subject_name": data.subject_name,
                "class_level": data.class_level,
                "content_series_id": None,
                "topic_id": topic_id,
                "content_type": ContentType.QUESTION,
                "title": data.topic_title or "Word meaning",
                "content_text": data.student_question,
                "student_question": data.student_question,
                "ai_response": dictionary_answer["response"],
                "simple_definition": dictionary_answer["response"],
                "official_definition": dictionary_answer["response"],
                "media_url": matched_media_url,
                "gemini_file_ref": None,
                "question_type": None,
                "answer_options": None,
                "correct_answer": None,
                "worked_solution": None,
                "content_data": {
                    "student_question": data.student_question,
                    "ai_response": dictionary_answer["response"],
                    "model_name": dictionary_answer["model_name"],
                    "is_out_of_curriculum": dictionary_answer["is_out_of_curriculum"],
                    "conversation_id": str(data.conversation_id)
                    if data.conversation_id
                    else None,
                    "explanation_mode": data.explanation_mode.value,
                    "source": "dictionary",
                },
                "version": 1,
                "gemini_file_uploaded_at": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

        try:
            ai_service = self._get_ai_service()
            ai_result = await ai_service.generate_tutor_response(
                prompt=data.student_question,
                subject_name=data.subject_name,
                class_level=data.class_level,
                topic_title=data.topic_title,
            )
        except RuntimeError as exc:
            raise RuntimeError(
                "AI tutor is not configured. Set GEMINI_API_KEY and install google-genai."
            ) from exc

        content = LearningContent(
            student_id=data.student_id,
            subject_name=data.subject_name,
            class_level=data.class_level,
            topic_id=topic_id,
            content_type=ContentType.QUESTION,
            title=data.topic_title or "Student question",
            content_text=data.student_question,
            student_question=data.student_question,
            ai_response=ai_result["response"],
            simple_definition=ai_result["response"],
            official_definition=ai_result["response"],
            media_url=matched_media_url,
            content_data={
                "student_question": data.student_question,
                "ai_response": ai_result["response"],
                "model_name": ai_result["model_name"],
                "is_out_of_curriculum": ai_result.get("is_out_of_curriculum", False),
                "conversation_id": str(data.conversation_id)
                if data.conversation_id
                else None,
                "explanation_mode": data.explanation_mode.value,
            },
        )
        if getattr(content, "content_id", None) is None:
            content.content_id = uuid4()

        if getattr(content, "version", None) is None:
            content.version = 1
        now = datetime.utcnow()
        response = {
            "content_id": content.content_id,
            "student_id": content.student_id,
            "subject_name": content.subject_name,
            "class_level": content.class_level,
            "content_series_id": content.content_series_id,
            "topic_id": content.topic_id,
            "content_type": content.content_type,
            "title": content.title,
            "content_text": content.content_text,
            "student_question": content.student_question,
            "ai_response": content.ai_response,
            "simple_definition": content.simple_definition,
            "official_definition": content.official_definition,
            "media_url": content.media_url,
            "gemini_file_ref": content.gemini_file_ref,
            "question_type": content.question_type,
            "answer_options": content.answer_options,
            "correct_answer": content.correct_answer,
            "worked_solution": content.worked_solution,
            "content_data": content.content_data,
            "version": content.version,
            "gemini_file_uploaded_at": None,
            "created_at": now,
            "updated_at": now,
        }

        if isinstance(self.ai_service, MockAIService):
            return response

        created = await self.content_repo.create(content)
        response["content_id"] = getattr(created, "content_id", response["content_id"])
        response["created_at"] = getattr(created, "created_at", response["created_at"])
        response["updated_at"] = getattr(created, "updated_at", response["updated_at"])

        return response

    async def get_content(self, content_id: UUID):
        return await self.content_repo.get_by_id(content_id)

    async def update_content(self, content_id: UUID, data: LearningContentUpdate):
        content = await self.content_repo.get_by_id(content_id)
        if not content:
            return None
        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(content, field, val)
        return await self.content_repo.update(content)

    async def delete_content(self, content_id: UUID):
        return await self.content_repo.delete(content_id)