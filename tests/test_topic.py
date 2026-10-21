import os
import random
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="DATABASE_URL is not set"
)

BASE = "/api/v1/topics"


def topic_body(**overrides):
    body = {
        "subject_name": "biology",
        "class_level": "S1",
        "term": 1,
        "title": f"Topic {uuid.uuid4().hex[:8]}",
        "sequence_no": random.randint(10_000, 2_000_000_000),
    }
    body.update(overrides)
    return body


def create_topic(client, **overrides):
    response = client.post(BASE, json=topic_body(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def test_list_topics(client):
    response = client.get(BASE)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_topic(client):
    body = topic_body(description="Basic idea")
    response = client.post(BASE, json=body)
    assert response.status_code == 201
    data = response.json()
    assert data["topic_id"]
    assert data["title"] == body["title"]
    assert data["is_active"] is True
    assert data["parent_topic_id"] is None
    assert data["created_at"]


def test_get_topic(client):
    topic = create_topic(client)
    response = client.get(f"{BASE}/{topic['topic_id']}")
    assert response.status_code == 200
    assert response.json()["topic_id"] == topic["topic_id"]


def test_get_unknown_topic_returns_404(client):
    assert client.get(f"{BASE}/{uuid.uuid4()}").status_code == 404


def test_update_topic(client):
    topic = create_topic(client)
    response = client.patch(
        f"{BASE}/{topic['topic_id']}",
        json={"title": "Renamed", "description": "New text"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Renamed"
    assert response.json()["description"] == "New text"


def test_create_topic_missing_title_returns_422(client):
    body = topic_body()
    del body["title"]
    assert client.post(BASE, json=body).status_code == 422


def test_create_topic_invalid_term_returns_422(client):
    assert client.post(BASE, json=topic_body(term=4)).status_code == 422


def test_duplicate_sequence_returns_409(client):
    first = create_topic(client)
    response = client.post(BASE, json=topic_body(sequence_no=first["sequence_no"]))
    assert response.status_code == 409


def test_create_subtopic(client):
    parent = create_topic(client)
    child = create_topic(client, parent_topic_id=parent["topic_id"])
    assert child["parent_topic_id"] == parent["topic_id"]


def test_unknown_parent_returns_404(client):
    response = client.post(BASE, json=topic_body(parent_topic_id=str(uuid.uuid4())))
    assert response.status_code == 404


def test_subtopic_must_match_parent_subject(client):
    parent = create_topic(client, subject_name="biology")
    response = client.post(
        BASE,
        json=topic_body(subject_name="chemistry", parent_topic_id=parent["topic_id"]),
    )
    assert response.status_code == 422


def test_topic_cannot_be_its_own_parent(client):
    topic = create_topic(client)
    response = client.patch(
        f"{BASE}/{topic['topic_id']}", json={"parent_topic_id": topic["topic_id"]}
    )
    assert response.status_code == 422


def test_parent_loop_is_rejected(client):
    a = create_topic(client)
    b = create_topic(client, parent_topic_id=a["topic_id"])
    response = client.patch(
        f"{BASE}/{a['topic_id']}", json={"parent_topic_id": b["topic_id"]}
    )
    assert response.status_code == 422


def test_delete_deactivates_topic(client):
    topic = create_topic(client)
    assert client.delete(f"{BASE}/{topic['topic_id']}").status_code == 204

    response = client.get(f"{BASE}/{topic['topic_id']}")
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    default_ids = [
        t["topic_id"] for t in client.get(BASE, params={"limit": 500}).json()
    ]
    assert topic["topic_id"] not in default_ids
    inactive = client.get(BASE, params={"is_active": False, "limit": 500}).json()
    assert topic["topic_id"] in [t["topic_id"] for t in inactive]
