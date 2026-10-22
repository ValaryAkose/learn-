from uuid import UUID, uuid4

from sqlalchemy import String, cast, delete, func, or_, select, text, update
from sqlalchemy.orm import Session

from core.enums import SubjectName
from models.ai_tutor_interaction import AITutorInteraction
from models.learner_assessment import LearnerAssessment
from models.learner_lesson_progress import LearnerLessonProgress
from models.learning_content import LearningContent
from models.topic import Topic


class AITutorInteractionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        interaction: AITutorInteraction,
    ) -> dict[str, object]:
        interaction_id = interaction.interaction_id or uuid4()
        statement = text(
            """
            INSERT INTO ai_tutor_interactions (
                interaction_id,
                conversation_id,
                student_id,
                topic_id,
                content_id,
                tutor_type,
                student_query,
                explanation_mode,
                ai_response,
                model_name,
                response_status,
                is_saved_offline
            ) VALUES (
                :interaction_id,
                :conversation_id,
                :student_id,
                :topic_id,
                :content_id,
                CAST(:tutor_type AS tutor_type),
                :student_query,
                CAST(:explanation_mode AS explanation_mode),
                :ai_response,
                :model_name,
                CAST(:response_status AS response_status),
                :is_saved_offline
            )
            RETURNING
                interaction_id,
                conversation_id,
                student_id,
                topic_id,
                content_id,
                lower(CAST(tutor_type AS TEXT)) AS tutor_type,
                student_query,
                lower(CAST(explanation_mode AS TEXT)) AS explanation_mode,
                ai_response,
                model_name,
                lower(CAST(response_status AS TEXT)) AS response_status,
                is_saved_offline,
                created_at
            """
        )
        result = self.db.execute(
            statement,
            {
                "interaction_id": interaction_id,
                "conversation_id": interaction.conversation_id,
                "student_id": interaction.student_id,
                "topic_id": interaction.topic_id,
                "content_id": interaction.content_id,
                "tutor_type": interaction.tutor_type.value,
                "student_query": interaction.student_query,
                "explanation_mode": interaction.explanation_mode.value,
                "ai_response": interaction.ai_response,
                "model_name": interaction.model_name,
                "response_status": interaction.response_status.value,
                "is_saved_offline": interaction.is_saved_offline,
            },
        )
        saved = dict(result.mappings().one())
        self.db.commit()
        return saved

    def get_curriculum_content(
        self,
        content_id: UUID,
    ) -> dict[str, object] | None:
        statement = select(
            LearningContent.content_id,
            LearningContent.topic_id,
        ).where(LearningContent.content_id == content_id)
        row = self.db.execute(statement).mappings().one_or_none()
        return dict(row) if row is not None else None

    @staticmethod
    def _interaction_columns():
        return (
            AITutorInteraction.interaction_id,
            AITutorInteraction.conversation_id,
            AITutorInteraction.student_id,
            AITutorInteraction.topic_id,
            AITutorInteraction.content_id,
            func.lower(cast(AITutorInteraction.tutor_type, String)).label("tutor_type"),
            AITutorInteraction.student_query,
            func.lower(cast(AITutorInteraction.explanation_mode, String)).label(
                "explanation_mode"
            ),
            AITutorInteraction.ai_response,
            AITutorInteraction.model_name,
            func.lower(cast(AITutorInteraction.response_status, String)).label(
                "response_status"
            ),
            AITutorInteraction.is_saved_offline,
            AITutorInteraction.created_at,
        )

    def list_conversation_summaries(
        self,
        student_id: UUID,
        search: str | None = None,
        subject_name: SubjectName | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        statement = (
            select(
                AITutorInteraction.conversation_id,
                AITutorInteraction.topic_id,
                AITutorInteraction.student_query,
                AITutorInteraction.is_saved_offline,
                AITutorInteraction.created_at,
                func.lower(cast(Topic.subject_name, String)).label("subject_name"),
                LearningContent.title,
            )
            .outerjoin(
                LearningContent,
                AITutorInteraction.content_id == LearningContent.content_id,
            )
            .outerjoin(
                Topic,
                Topic.topic_id
                == func.coalesce(
                    AITutorInteraction.topic_id,
                    LearningContent.topic_id,
                ),
            )
            .where(AITutorInteraction.student_id == student_id)
            .order_by(AITutorInteraction.created_at.desc())
        )

        if subject_name is not None:
            statement = statement.where(
                func.lower(cast(Topic.subject_name, String)) == subject_name.value
            )

        if search:
            matching_conversations = select(AITutorInteraction.conversation_id).where(
                AITutorInteraction.student_id == student_id,
                or_(
                    AITutorInteraction.student_query.ilike(f"%{search}%"),
                    AITutorInteraction.ai_response.ilike(f"%{search}%"),
                ),
            )
            statement = statement.where(
                AITutorInteraction.conversation_id.in_(matching_conversations)
            )

        conversations = {}
        for (
            conversation_id,
            topic_id,
            student_query,
            is_saved_offline,
            created_at,
            subject,
            content_title,
        ) in self.db.execute(statement).all():
            summary = conversations.get(conversation_id)
            if summary is None:
                conversations[conversation_id] = {
                    "conversation_id": conversation_id,
                    "topic_id": topic_id,
                    "subject_name": subject,
                    "conversation_title": content_title or student_query,
                    "interaction_count": 1,
                    "created_at": created_at,
                    "is_saved_offline": is_saved_offline,
                }
            else:
                summary["interaction_count"] += 1
                summary["is_saved_offline"] = (
                    summary["is_saved_offline"] and is_saved_offline
                )

        return list(conversations.values())[skip : skip + limit]

    def list_lesson_progress(
        self,
        student_id: UUID,
        subject_name: SubjectName | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        normalized_subject = func.lower(cast(Topic.subject_name, String))
        normalized_status = func.lower(cast(LearnerLessonProgress.status, String))
        statement = (
            select(
                LearnerLessonProgress.lesson_progress_id,
                LearnerLessonProgress.content_id,
                LearnerLessonProgress.topic_id,
                normalized_subject.label("subject_name"),
                Topic.title.label("topic_title"),
                LearningContent.title.label("lesson_title"),
                normalized_status.label("status"),
                LearnerLessonProgress.last_viewed_at,
                LearnerLessonProgress.completed_at,
                LearnerLessonProgress.updated_at,
            )
            .join(Topic, LearnerLessonProgress.topic_id == Topic.topic_id)
            .join(
                LearningContent,
                LearnerLessonProgress.content_id == LearningContent.content_id,
            )
            .where(LearnerLessonProgress.student_id == student_id)
            .order_by(
                func.coalesce(
                    LearnerLessonProgress.last_viewed_at,
                    LearnerLessonProgress.updated_at,
                ).desc()
            )
            .offset(skip)
            .limit(limit)
        )
        if subject_name is not None:
            statement = statement.where(normalized_subject == subject_name.value)
        return [dict(row) for row in self.db.execute(statement).mappings().all()]

    def list_available_quiz_questions(
        self,
        subject_name: SubjectName | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        normalized_subject = func.lower(cast(Topic.subject_name, String))
        normalized_content_type = func.lower(cast(LearningContent.content_type, String))
        normalized_question_type = func.lower(
            cast(LearningContent.question_type, String)
        )
        statement = (
            select(
                LearningContent.content_id,
                LearningContent.content_series_id,
                LearningContent.topic_id,
                normalized_subject.label("subject_name"),
                Topic.title.label("topic_title"),
                LearningContent.title,
                normalized_question_type.label("question_type"),
                LearningContent.content_text.label("question_text"),
                LearningContent.answer_options,
            )
            .join(Topic, LearningContent.topic_id == Topic.topic_id)
            .where(
                normalized_content_type == "question",
                LearningContent.question_type.is_not(None),
                Topic.is_active.is_(True),
            )
            .order_by(Topic.title, LearningContent.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if subject_name is not None:
            statement = statement.where(normalized_subject == subject_name.value)
        return [dict(row) for row in self.db.execute(statement).mappings().all()]

    def list_quiz_attempts(
        self,
        student_id: UUID,
        subject_name: SubjectName | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        normalized_subject = func.lower(cast(LearnerAssessment.subject_name, String))
        normalized_assessment_type = func.lower(
            cast(LearnerAssessment.assessment_type, String)
        )
        normalized_status = func.lower(cast(LearnerAssessment.status, String))
        statement = (
            select(
                LearnerAssessment.assessment_id,
                LearnerAssessment.topic_id,
                normalized_subject.label("subject_name"),
                Topic.title.label("topic_title"),
                normalized_assessment_type.label("assessment_type"),
                LearnerAssessment.attempt_number,
                normalized_status.label("status"),
                LearnerAssessment.started_at,
                LearnerAssessment.completed_at,
            )
            .outerjoin(Topic, LearnerAssessment.topic_id == Topic.topic_id)
            .where(
                LearnerAssessment.student_id == student_id,
                normalized_assessment_type == "quiz",
            )
            .order_by(LearnerAssessment.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if subject_name is not None:
            statement = statement.where(normalized_subject == subject_name.value)
        return [dict(row) for row in self.db.execute(statement).mappings().all()]

    def set_conversation_saved_offline(
        self,
        student_id: UUID,
        conversation_id: UUID,
        is_saved_offline: bool,
    ) -> int:
        statement = (
            update(AITutorInteraction)
            .where(
                AITutorInteraction.student_id == student_id,
                AITutorInteraction.conversation_id == conversation_id,
            )
            .values(is_saved_offline=is_saved_offline)
        )
        result = self.db.execute(statement)
        self.db.commit()
        return result.rowcount or 0

    def get_by_id(
        self,
        interaction_id: UUID,
    ) -> AITutorInteraction | None:
        statement = select(AITutorInteraction).where(
            AITutorInteraction.interaction_id == interaction_id
        )
        return self.db.execute(statement).scalar_one_or_none()

    def get_response_by_id(
        self,
        interaction_id: UUID,
    ) -> dict[str, object] | None:
        statement = select(*self._interaction_columns()).where(
            AITutorInteraction.interaction_id == interaction_id
        )
        row = self.db.execute(statement).mappings().one_or_none()
        return dict(row) if row is not None else None

    def update_by_id(
        self,
        interaction_id: UUID,
        changes: dict[str, object],
    ) -> dict[str, object] | None:
        assignments = {
            "topic_id": "topic_id = :topic_id",
            "content_id": "content_id = :content_id",
            "explanation_mode": (
                "explanation_mode = CAST(:explanation_mode AS explanation_mode)"
            ),
            "is_saved_offline": "is_saved_offline = :is_saved_offline",
        }
        parameters = {"interaction_id": interaction_id}
        set_clauses = []
        for field, value in changes.items():
            set_clauses.append(assignments[field])
            parameters[field] = getattr(value, "value", value)

        if not set_clauses:
            return self.get_response_by_id(interaction_id)

        statement = text(
            f"""
            UPDATE ai_tutor_interactions
            SET {", ".join(set_clauses)}
            WHERE interaction_id = :interaction_id
            RETURNING
                interaction_id,
                conversation_id,
                student_id,
                topic_id,
                content_id,
                lower(CAST(tutor_type AS TEXT)) AS tutor_type,
                student_query,
                lower(CAST(explanation_mode AS TEXT)) AS explanation_mode,
                ai_response,
                model_name,
                lower(CAST(response_status AS TEXT)) AS response_status,
                is_saved_offline,
                created_at
            """
        )
        row = self.db.execute(statement, parameters).mappings().one_or_none()
        self.db.commit()
        return dict(row) if row is not None else None

    def list_by_student(
        self,
        student_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        statement = (
            select(*self._interaction_columns())
            .where(AITutorInteraction.student_id == student_id)
            .order_by(AITutorInteraction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return [dict(row) for row in self.db.execute(statement).mappings().all()]

    def list_by_conversation(
        self,
        conversation_id: UUID,
        student_id: UUID,
    ) -> list[dict[str, object]]:
        statement = (
            select(*self._interaction_columns())
            .where(
                AITutorInteraction.conversation_id == conversation_id,
                AITutorInteraction.student_id == student_id,
            )
            .order_by(AITutorInteraction.created_at.asc())
        )
        return [dict(row) for row in self.db.execute(statement).mappings().all()]

    def search_by_student(
        self,
        student_id: UUID,
        search: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        statement = (
            select(*self._interaction_columns())
            .where(
                AITutorInteraction.student_id == student_id,
                or_(
                    AITutorInteraction.student_query.ilike(f"%{search}%"),
                    AITutorInteraction.ai_response.ilike(f"%{search}%"),
                ),
            )
            .order_by(AITutorInteraction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return [dict(row) for row in self.db.execute(statement).mappings().all()]

    def update(
        self,
        interaction: AITutorInteraction,
    ) -> AITutorInteraction:
        self.db.commit()
        self.db.refresh(interaction)
        return interaction

    def delete(self, interaction_id: UUID) -> bool:
        result = self.db.execute(
            delete(AITutorInteraction).where(
                AITutorInteraction.interaction_id == interaction_id
            )
        )
        self.db.commit()
        return bool(result.rowcount)
