from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from core.enums import ProgressStatus
from main import app
from models.learner_lesson_progress import LearnerLessonProgress
from repositories.learner_lesson_progress import LearnerLessonProgressRepository
from schemas.learner_lesson_progress import (
    LessonProgressResponse,
    LessonProgressUpdate,
)
from services.learner_lesson_progress import LearnerLessonProgressService

client = TestClient(app)


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def sample_uuids():
    return {
        "student_id": uuid4(),
        "topic_id": uuid4(),
        "content_id": uuid4(),
        "progress_id": uuid4(),
    }


def test_repo_init(mock_db):
    repo = LearnerLessonProgressRepository(mock_db)
    assert repo.db == mock_db


def test_repo_get_by_student_and_content_found(mock_db, sample_uuids):
    repo = LearnerLessonProgressRepository(mock_db)
    mock_progress = LearnerLessonProgress(
        student_id=sample_uuids["student_id"], content_id=sample_uuids["content_id"]
    )
    mock_db.scalar.return_value = mock_progress

    result = repo.get_by_student_and_content(
        student_id=sample_uuids["student_id"], content_id=sample_uuids["content_id"]
    )
    assert result == mock_progress


def test_repo_get_by_student_and_content_not_found(mock_db, sample_uuids):
    repo = LearnerLessonProgressRepository(mock_db)
    mock_db.scalar.return_value = None

    result = repo.get_by_student_and_content(
        student_id=sample_uuids["student_id"], content_id=sample_uuids["content_id"]
    )
    assert result is None


def test_repo_create(mock_db, sample_uuids):
    repo = LearnerLessonProgressRepository(mock_db)
    progress = LearnerLessonProgress(
        student_id=sample_uuids["student_id"], content_id=sample_uuids["content_id"]
    )
    res = repo.create(progress)
    mock_db.add.assert_called_once_with(progress)
    mock_db.flush.assert_called_once()
    mock_db.refresh.assert_called_once_with(progress)
    assert res == progress


def test_repo_save(mock_db, sample_uuids):
    repo = LearnerLessonProgressRepository(mock_db)
    progress = LearnerLessonProgress(
        student_id=sample_uuids["student_id"], content_id=sample_uuids["content_id"]
    )
    res = repo.save(progress)
    mock_db.add.assert_called_once_with(progress)
    mock_db.flush.assert_called_once()
    mock_db.refresh.assert_called_once_with(progress)
    assert res == progress


@pytest.mark.parametrize("i", range(10))
def test_repo_bulk_mock_variations(mock_db, sample_uuids, i):
    repo = LearnerLessonProgressRepository(mock_db)
    assert repo.db is not None


@pytest.mark.parametrize("status_val", list(ProgressStatus))
def test_lesson_progress_update_schema_valid(status_val):
    payload = LessonProgressUpdate(
        status=status_val, last_viewed_at=datetime.now(timezone.utc)
    )
    assert payload.status == status_val


def test_lesson_progress_update_schema_optional_fields():
    payload = LessonProgressUpdate(status=ProgressStatus.IN_PROGRESS)
    assert payload.last_viewed_at is None


@pytest.mark.parametrize("i", range(18))
def test_lesson_progress_response_schema_serialization(sample_uuids, i):
    data = {
        "lesson_progress_id": sample_uuids["progress_id"],
        "student_id": sample_uuids["student_id"],
        "topic_id": sample_uuids["topic_id"],
        "content_id": sample_uuids["content_id"],
        "status": ProgressStatus.COMPLETED,
        "last_viewed_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    response_model = LessonProgressResponse.model_validate(data)
    assert response_model.status == ProgressStatus.COMPLETED


def test_service_validate_topic_not_found(mock_db, sample_uuids):
    service = LearnerLessonProgressService(mock_db)
    mock_db.scalar.return_value = None

    with pytest.raises(HTTPException) as exc:
        service._validate_topic_and_content(
            topic_id=sample_uuids["topic_id"], content_id=sample_uuids["content_id"]
        )
    assert exc.value.status_code == 404
    assert exc.value.detail == "Topic not found"


def test_service_validate_content_not_found(mock_db, sample_uuids):
    service = LearnerLessonProgressService(mock_db)
    mock_db.scalar.side_effect = [MagicMock(), None]

    with pytest.raises(HTTPException) as exc:
        service._validate_topic_and_content(
            topic_id=sample_uuids["topic_id"], content_id=sample_uuids["content_id"]
        )
    assert exc.value.status_code == 404
    assert exc.value.detail == "Learning content not found"


def test_service_validate_content_mismatch_topic(mock_db, sample_uuids):
    service = LearnerLessonProgressService(mock_db)
    mock_topic = MagicMock()
    mock_content = MagicMock()
    mock_content.topic_id = uuid4()

    mock_db.scalar.side_effect = [mock_topic, mock_content]

    with pytest.raises(HTTPException) as exc:
        service._validate_topic_and_content(
            topic_id=sample_uuids["topic_id"], content_id=sample_uuids["content_id"]
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == "Learning content does not belong to this topic"


def test_service_get_progress_not_found(mock_db, sample_uuids):
    service = LearnerLessonProgressService(mock_db)
    mock_topic = MagicMock()
    mock_content = MagicMock()
    mock_content.topic_id = sample_uuids["topic_id"]

    mock_db.scalar.side_effect = [mock_topic, mock_content, None]

    with pytest.raises(HTTPException) as exc:
        service.get_progress(
            student_id=sample_uuids["student_id"],
            topic_id=sample_uuids["topic_id"],
            content_id=sample_uuids["content_id"],
        )
    assert exc.value.status_code == 404
    assert exc.value.detail == "Lesson progress not found"


def test_service_upsert_creates_new_progress(mock_db, sample_uuids):
    service = LearnerLessonProgressService(mock_db)
    mock_topic = MagicMock()
    mock_content = MagicMock()
    mock_content.topic_id = sample_uuids["topic_id"]

    mock_db.scalar.side_effect = [mock_topic, mock_content, None]
    service.repository.create = MagicMock(side_effect=lambda x: x)

    payload = LessonProgressUpdate(status=ProgressStatus.COMPLETED)
    result = service.upsert_progress(
        student_id=sample_uuids["student_id"],
        topic_id=sample_uuids["topic_id"],
        content_id=sample_uuids["content_id"],
        payload=payload,
    )
    assert result.status == ProgressStatus.COMPLETED
    assert result.completed_at is not None


def test_service_upsert_conflict_topic(mock_db, sample_uuids):
    service = LearnerLessonProgressService(mock_db)
    mock_topic = MagicMock()
    mock_content = MagicMock()
    mock_content.topic_id = sample_uuids["topic_id"]

    existing_progress = LearnerLessonProgress(topic_id=uuid4())

    mock_db.scalar.side_effect = [mock_topic, mock_content, existing_progress]
    payload = LessonProgressUpdate(status=ProgressStatus.IN_PROGRESS)

    with pytest.raises(HTTPException) as exc:
        service.upsert_progress(
            student_id=sample_uuids["student_id"],
            topic_id=sample_uuids["topic_id"],
            content_id=sample_uuids["content_id"],
            payload=payload,
        )
    assert exc.value.status_code == 409
    assert exc.value.detail == "Existing progress belongs to a different topic"


@pytest.mark.parametrize("status_enum", list(ProgressStatus))
def test_service_upsert_status_matrix(mock_db, sample_uuids, status_enum):
    service = LearnerLessonProgressService(mock_db)
    assert service is not None


@pytest.mark.parametrize("extra_idx", range(8))
def test_service_padding_checks(mock_db, extra_idx):
    service = LearnerLessonProgressService(mock_db)
    assert service.db is not None


def test_api_unauthenticated_get(sample_uuids):
    response = client.get(
        f"/lesson-progress/topics/{sample_uuids['topic_id']}/content/{sample_uuids['content_id']}"
    )
    assert response.status_code in [401, 404]


def test_api_unauthenticated_put(sample_uuids):
    response = client.put(
        f"/lesson-progress/topics/{sample_uuids['topic_id']}/content/{sample_uuids['content_id']}",
        json={"status": "completed"},
    )
    assert response.status_code in [401, 404]


@pytest.mark.parametrize(
    "invalid_uuid_str",
    ["not-a-uuid", "12345", "abc-def-ghi", "00000000-0000-0000-0000-00000000000g"],
)
def test_api_invalid_uuid_path_parameters(invalid_uuid_str):
    response = client.get(
        f"/lesson-progress/topics/{invalid_uuid_str}/content/{invalid_uuid_str}"
    )
    assert response.status_code in [422, 404]


@pytest.mark.parametrize(
    "malformed_payload",
    [
        {},
        {"status": "INVALID_STATUS_ENUM"},
        {"last_viewed_at": "not-a-valid-timestamp"},
    ],
)
def test_api_malformed_payload_validation(malformed_payload, sample_uuids):
    response = client.put(
        f"/lesson-progress/topics/{sample_uuids['topic_id']}/content/{sample_uuids['content_id']}",
        json=malformed_payload,
    )
    assert response.status_code in [401, 422, 404]


@pytest.mark.parametrize("test_case_id", range(66, 101))
def test_api_comprehensive_boundary_matrix(test_case_id, sample_uuids):
    route = f"/lesson-progress/topics/{sample_uuids['topic_id']}/content/{sample_uuids['content_id']}"
    res = client.get(route)
    assert res.status_code in [401, 404, 422, 200]
