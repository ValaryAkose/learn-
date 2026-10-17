from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from core.enums import (
    ExplanationMode,
    ResponseStatus,
    SubjectName,
    TutorType,
)
from main import app
from models.ai_tutor_interaction import AITutorInteraction
from repositories.ai_tutor_interactions import AITutorInteractionRepository
from routers.ai_tutor_interactions import get_tutor_interaction_service
from services.ai_tutor_interactions import AITutorInteractionService


class StubTutorRepository:
    def __init__(self):
        self.content_id = uuid4()
        self.topic_id = uuid4()
        self.student_id = uuid4()
        self.created_interaction = None
        self.list_arguments = None
        self.offline_arguments = None
        self.updated_interactions = 2
        self.conversation_interactions = []
        self.activity_arguments = None
        self.create_calls = 0

    def get_curriculum_content(self, content_id: UUID):
        if content_id != self.content_id:
            return None
        return {"content_id": content_id, "topic_id": self.topic_id}

    def create(self, interaction: AITutorInteraction):
        self.create_calls += 1
        interaction.interaction_id = uuid4()
        interaction.created_at = datetime.now(timezone.utc)
        self.created_interaction = interaction
        return interaction

    def list_by_conversation(self, conversation_id: UUID, student_id: UUID):
        return self.conversation_interactions

    def list_lesson_progress(
        self,
        student_id: UUID,
        subject_name=None,
        skip: int = 0,
        limit: int = 100,
    ):
        self.activity_arguments = (student_id, subject_name, skip, limit)
        return [
            {
                "lesson_progress_id": uuid4(),
                "content_id": self.content_id,
                "topic_id": self.topic_id,
                "subject_name": "biology",
                "topic_title": "Cells",
                "lesson_title": "A typical animal cell",
                "status": "completed",
                "last_viewed_at": datetime.now(timezone.utc),
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        ]

    def list_available_quiz_questions(
        self,
        subject_name=None,
        skip: int = 0,
        limit: int = 100,
    ):
        return [
            {
                "content_id": self.content_id,
                "content_series_id": uuid4(),
                "topic_id": self.topic_id,
                "subject_name": "biology",
                "topic_title": "Cells",
                "title": "Cell structure",
                "question_type": "multiple_choice",
                "question_text": "Which part controls the cell?",
                "answer_options": [{"label": "A", "text": "Nucleus"}],
            }
        ]

    def list_quiz_attempts(
        self,
        student_id: UUID,
        subject_name=None,
        skip: int = 0,
        limit: int = 100,
    ):
        return [
            {
                "assessment_id": uuid4(),
                "topic_id": self.topic_id,
                "subject_name": "biology",
                "topic_title": "Cells",
                "assessment_type": "quiz",
                "attempt_number": 1,
                "status": "completed",
                "started_at": datetime.now(timezone.utc),
                "completed_at": datetime.now(timezone.utc),
            }
        ]

    def get_learner_activity(self, student_id, subject_name, skip, limit):
        return self.list_lesson_progress(student_id, subject_name, skip, limit)

    def list_conversation_summaries(
        self,
        student_id: UUID,
        search: str | None = None,
        subject_name: SubjectName | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        self.list_arguments = (student_id, search, subject_name, skip, limit)
        summaries = [
            {
                "conversation_id": uuid4(),
                "topic_id": uuid4(),
                "subject_name": subject,
                "conversation_title": (
                    "A typical animal cell"
                    if subject is SubjectName.BIOLOGY
                    else f"{subject.value.title()} lesson"
                ),
                "interaction_count": 3,
                "created_at": datetime.now(timezone.utc),
                "is_saved_offline": False,
            }
            for subject in SubjectName
        ]
        if subject_name is not None:
            summaries = [
                item for item in summaries if item["subject_name"] is subject_name
            ]
        return summaries

    def set_conversation_saved_offline(
        self,
        student_id: UUID,
        conversation_id: UUID,
        is_saved_offline: bool,
    ) -> int:
        self.offline_arguments = (student_id, conversation_id, is_saved_offline)
        return self.updated_interactions


@pytest.fixture
def tutor_repository_override():
    repository = StubTutorRepository()
    original = app.dependency_overrides.get(get_tutor_interaction_service)
    app.dependency_overrides[get_tutor_interaction_service] = lambda: (
        AITutorInteractionService(repository)
    )
    yield repository
    if original is None:
        app.dependency_overrides.pop(get_tutor_interaction_service, None)
    else:
        app.dependency_overrides[get_tutor_interaction_service] = original


def interaction_body(repository: StubTutorRepository, **overrides):
    body = {
        "student_id": str(repository.student_id),
        "content_id": str(repository.content_id),
        "student_query": "What is an animal cell?",
        "ai_response": "A cell is the basic unit of life.",
        "model_name": "test-model",
    }
    body.update(overrides)
    return body


class RecordingResult:
    def __init__(self, rows=None, inserted=None):
        self.rows = rows or []
        self.inserted = inserted

    def all(self):
        return self.rows

    def mappings(self):
        return self

    def one(self):
        return self.inserted


class RecordingSession:
    def __init__(self, result):
        self.result = result
        self.statement = None
        self.parameters = None
        self.committed = False

    def execute(self, statement, parameters=None):
        self.statement = statement
        self.parameters = parameters
        return self.result

    def commit(self):
        self.committed = True


def test_subject_filter_uses_database_enum_values():
    from sqlalchemy.dialects.postgresql import dialect

    session = RecordingSession(RecordingResult())
    repository = AITutorInteractionRepository(session)
    repository.list_conversation_summaries(
        uuid4(),
        subject_name=SubjectName.BIOLOGY,
    )

    compiled = session.statement.compile(dialect=dialect())
    assert "lower(CAST(topics.subject_name AS VARCHAR))" in str(compiled)
    assert "biology" in compiled.params.values()


def test_learning_activity_queries_read_seeded_rows_with_subject_values():
    from sqlalchemy.dialects.postgresql import dialect

    session = RecordingSession(RecordingResult())
    repository = AITutorInteractionRepository(session)
    student_id = uuid4()

    repository.list_lesson_progress(student_id, SubjectName.BIOLOGY)
    lesson_sql = session.statement.compile(dialect=dialect())
    assert "learner_lesson_progress" in str(lesson_sql)
    assert "biology" in lesson_sql.params.values()

    repository.list_available_quiz_questions(SubjectName.BIOLOGY)
    quiz_sql = session.statement.compile(dialect=dialect())
    assert "learning_content.content_type" in str(quiz_sql)
    assert "question" in quiz_sql.params.values()
    assert "correct_answer" not in str(quiz_sql)

    repository.list_quiz_attempts(student_id, SubjectName.BIOLOGY)
    attempt_sql = session.statement.compile(dialect=dialect())
    assert "learner_assessments" in str(attempt_sql)
    assert "quiz" in attempt_sql.params.values()
    assert "biology" in attempt_sql.params.values()


def test_create_interaction_binds_lowercase_enum_values():
    interaction = AITutorInteraction(
        conversation_id=uuid4(),
        student_id=uuid4(),
        tutor_type=TutorType.SUBJECT,
        student_query="Question",
        explanation_mode=ExplanationMode.STANDARD,
        ai_response="Answer",
        model_name="test-model",
        response_status=ResponseStatus.ANSWERED,
        is_saved_offline=False,
    )
    session = RecordingSession(
        RecordingResult(
            inserted={
                "interaction_id": uuid4(),
                "conversation_id": interaction.conversation_id,
                "student_id": interaction.student_id,
                "topic_id": None,
                "content_id": None,
                "tutor_type": "subject",
                "student_query": interaction.student_query,
                "explanation_mode": "standard",
                "ai_response": interaction.ai_response,
                "model_name": interaction.model_name,
                "response_status": "answered",
                "is_saved_offline": False,
                "created_at": datetime.now(timezone.utc),
            }
        )
    )

    saved = AITutorInteractionRepository(session).create(interaction)

    assert session.parameters["tutor_type"] == "subject"
    assert session.parameters["explanation_mode"] == "standard"
    assert session.parameters["response_status"] == "answered"
    assert saved["tutor_type"] == "subject"
    assert session.committed


def test_create_interaction_links_to_selected_curriculum_content(
    client,
    tutor_repository_override,
):
    repository = tutor_repository_override
    response = client.post(
        "/ai-tutor/interactions",
        json=interaction_body(repository),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["content_id"] == str(repository.content_id)
    assert data["topic_id"] == str(repository.topic_id)
    assert repository.created_interaction.topic_id == repository.topic_id


def test_create_interaction_rejects_content_from_a_different_topic(
    client,
    tutor_repository_override,
):
    repository = tutor_repository_override
    response = client.post(
        "/ai-tutor/interactions",
        json=interaction_body(repository, topic_id=str(uuid4())),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The selected topic does not match the curriculum content"
    )


def test_create_interaction_rejects_unknown_curriculum_content(
    client,
    tutor_repository_override,
):
    response = client.post(
        "/ai-tutor/interactions",
        json=interaction_body(tutor_repository_override, content_id=str(uuid4())),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Curriculum content not found"


def test_open_conversation_returns_table_interaction_fields(
    client,
    tutor_repository_override,
):
    repository = tutor_repository_override
    conversation_id = uuid4()
    repository.conversation_interactions = [
        {
            "interaction_id": uuid4(),
            "conversation_id": conversation_id,
            "student_id": repository.student_id,
            "topic_id": repository.topic_id,
            "content_id": repository.content_id,
            "tutor_type": "subject",
            "student_query": "What is an animal cell?",
            "explanation_mode": "standard",
            "ai_response": "A cell is the basic unit of life.",
            "model_name": "test-model",
            "response_status": "answered",
            "is_saved_offline": False,
            "created_at": datetime.now(timezone.utc),
        }
    ]

    response = client.get(
        f"/ai-tutor/students/{repository.student_id}/conversations/{conversation_id}"
    )

    assert response.status_code == 200
    interaction = response.json()[0]
    assert interaction["student_query"] == "What is an animal cell?"
    assert interaction["ai_response"] == "A cell is the basic unit of life."
    assert interaction["content_id"] == str(repository.content_id)
    assert interaction["response_status"] == "answered"


def test_list_conversations_filters_and_serializes_summary(
    client,
    tutor_repository_override,
):
    repository = tutor_repository_override
    response = client.get(
        f"/ai-tutor/students/{repository.student_id}/conversations",
        params={"q": "animal cell", "subject": "biology", "skip": 1, "limit": 5},
    )

    assert response.status_code == 200
    summary = response.json()[0]
    assert summary["subject_name"] == "biology"
    assert summary["conversation_title"] == "A typical animal cell"
    assert summary["interaction_count"] == 3
    assert repository.list_arguments == (
        repository.student_id,
        "animal cell",
        SubjectName.BIOLOGY,
        1,
        5,
    )


def test_list_conversations_defaults_to_all_five_subjects(
    client,
    tutor_repository_override,
):
    repository = tutor_repository_override
    response = client.get(
        f"/ai-tutor/students/{repository.student_id}/conversations"
    )

    assert response.status_code == 200
    assert {item["subject_name"] for item in response.json()} == {
        "biology",
        "chemistry",
        "mathematics",
        "english",
        "physics",
    }
    assert repository.list_arguments == (
        repository.student_id,
        None,
        None,
        0,
        100,
    )


def test_list_conversations_rejects_unknown_subject(
    client,
    tutor_repository_override,
):
    repository = tutor_repository_override
    response = client.get(
        f"/ai-tutor/students/{repository.student_id}/conversations",
        params={"subject": "astronomy"},
    )

    assert response.status_code == 422
    assert repository.list_arguments is None


def test_learner_activity_reads_existing_records_without_creating_interactions(
    client,
    tutor_repository_override,
):
    repository = tutor_repository_override
    response = client.get(
        f"/ai-tutor/students/{repository.student_id}/activity",
        params={"subject": "biology"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["lesson_progress"][0]["lesson_title"] == "A typical animal cell"
    question = data["available_quiz_questions"][0]
    assert question["question_text"] == "Which part controls the cell?"
    assert "correct_answer" not in question
    assert data["quiz_attempts"][0]["status"] == "completed"
    assert data["tutor_conversations"][0]["subject_name"] == "biology"
    assert repository.activity_arguments == (
        repository.student_id,
        SubjectName.BIOLOGY,
        0,
        100,
    )
    assert repository.create_calls == 0


def test_save_conversation_offline_updates_all_interactions(
    client,
    tutor_repository_override,
):
    repository = tutor_repository_override
    conversation_id = uuid4()
    repository.conversation_interactions = [
        {
            "interaction_id": uuid4(),
            "conversation_id": conversation_id,
            "student_id": repository.student_id,
            "topic_id": repository.topic_id,
            "content_id": repository.content_id,
            "tutor_type": "subject",
            "student_query": "What is an animal cell?",
            "explanation_mode": "standard",
            "ai_response": "A cell is the basic unit of life.",
            "model_name": "test-model",
            "response_status": "answered",
            "is_saved_offline": True,
            "created_at": datetime.now(timezone.utc),
        },
        {
            "interaction_id": uuid4(),
            "conversation_id": conversation_id,
            "student_id": repository.student_id,
            "topic_id": repository.topic_id,
            "content_id": repository.content_id,
            "tutor_type": "subject",
            "student_query": "What does the nucleus do?",
            "explanation_mode": "standard",
            "ai_response": "It helps control cell activity.",
            "model_name": "test-model",
            "response_status": "answered",
            "is_saved_offline": True,
            "created_at": datetime.now(timezone.utc),
        },
    ]
    response = client.patch(
        f"/ai-tutor/students/{repository.student_id}/conversations/{conversation_id}/offline",
        json={"is_saved_offline": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["student_id"] == str(repository.student_id)
    assert payload["conversation_id"] == str(conversation_id)
    assert payload["is_saved_offline"] is True
    assert payload["interaction_count"] == 2
    assert len(payload["interactions"]) == 2
    assert payload["interactions"][0]["student_query"] == "What is an animal cell?"
    assert repository.offline_arguments == (
        repository.student_id,
        conversation_id,
        True,
    )


def test_save_unknown_conversation_offline_returns_404(
    client,
    tutor_repository_override,
):
    repository = tutor_repository_override
    repository.updated_interactions = 0
    response = client.patch(
        f"/ai-tutor/students/{repository.student_id}/conversations/{uuid4()}/offline",
        json={"is_saved_offline": True},
    )

    assert response.status_code == 404
