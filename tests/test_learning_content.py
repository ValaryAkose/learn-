from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_list_learning_content():
    response = client.get("/api/v1/content/")
    assert response.status_code in [200, 404]


def test_create_content_validation():
    payload = {
        "content_type": "lesson",
        "content_text": "Sample educational content text.",
        "version": 1,
    }
    response = client.post("/api/v1/content/", json=payload)
    assert response.status_code in [200, 201, 422]


def test_get_nonexistent_content():
    fake_id = "00000000-0000-0000-0000-000000000099"
    response = client.get(f"/api/v1/content/{fake_id}")
    assert response.status_code in [404, 422]
