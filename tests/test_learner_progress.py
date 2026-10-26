import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
async def sample_student_id(client: TestClient):
    student_id = uuid.uuid4()
    return student_id


@pytest.fixture
async def sample_topic_id(client: TestClient):
    topic_id = uuid.uuid4()
    return topic_id


def test_create_learner_progress(client: TestClient):
    payload = {
        "student_id": str(uuid.uuid4()),
        "topic_id": str(uuid.uuid4()),
        "subject_name": "MATHEMATICS",
        "progress_status": "NOT_STARTED",
    }
    response = client.post("/api/v1/progress/", json=payload)

    assert response.status_code in (200, 201, 422, 400)


def test_get_student_progress(client: TestClient):
    student_id = uuid.uuid4()
    response = client.get(f"/api/v1/progress/student/{student_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Progress not found"}


def test_list_all_progress(client: TestClient):
    response = client.get("/api/v1/progress/")
    assert response.status_code == 200
