import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="DATABASE_URL is not set"
)

BASE = "/api/v1/sync-events"
PACKAGES = "/api/v1/offline-packages"


@pytest.fixture
def student_id():
    from sqlalchemy import text

    from database import get_session_factory

    with get_session_factory()() as db:
        row = db.execute(text("select user_id from users limit 1")).first()
    if row is None:
        pytest.skip("insert one test user into the users table to run this test")
    return str(row[0])


def event_body(student_id, **overrides):
    body = {
        "client_event_id": str(uuid.uuid4()),
        "student_id": student_id,
        "device_id": str(uuid.uuid4()),
        "event_type": "progress_sync",
        "sync_status": "success",
        "records_synced": 3,
        "event_payload": {"records": []},
    }
    body.update(overrides)
    return body


def make_package(client, publish=True):
    body = {
        "subject_name": "biology",
        "class_level": "S1",
        "title": f"Package {uuid.uuid4().hex[:8]}",
        "package_version": "2.0",
        "manifest": [{"content_id": "abc", "version": "1"}],
        "manifest_uri": "https://example.com/packages/x.zip",
        "size_bytes": 10,
        "file_path_url": "packages/x.zip",
        "checksum": "b" * 64,
    }
    package = client.post(PACKAGES, json=body).json()
    if publish:
        assert (
            client.post(f"{PACKAGES}/{package['package_id']}/publish").status_code
            == 200
        )
    return package


def test_list_sync_events(client):
    response = client.get(BASE)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_missing_fields_returns_422(client):
    assert client.post(BASE, json={"sync_status": "success"}).status_code == 422


def test_download_without_package_id_returns_422(client):
    body = event_body(
        str(uuid.uuid4()),
        event_type="package_download",
        records_synced=0,
        event_payload=None,
    )
    assert client.post(BASE, json=body).status_code == 422


def test_download_with_records_synced_returns_422(client):
    body = event_body(
        str(uuid.uuid4()),
        event_type="package_download",
        package_id=str(uuid.uuid4()),
        records_synced=5,
        event_payload=None,
    )
    assert client.post(BASE, json=body).status_code == 422


def test_progress_sync_with_package_returns_422(client):
    body = event_body(str(uuid.uuid4()), package_id=str(uuid.uuid4()))
    assert client.post(BASE, json=body).status_code == 422


def test_negative_records_synced_returns_422(client):
    assert (
        client.post(
            BASE, json=event_body(str(uuid.uuid4()), records_synced=-1)
        ).status_code
        == 422
    )


def test_unknown_student_returns_404(client):
    response = client.post(BASE, json=event_body(str(uuid.uuid4())))
    assert response.status_code == 404


def test_record_progress_sync(client, student_id):
    response = client.post(BASE, json=event_body(student_id))
    assert response.status_code == 201
    data = response.json()
    assert data["sync_id"]
    assert data["received_at"]
    assert data["processed_at"] is None


def test_replayed_event_is_not_saved_twice(client, student_id):
    body = event_body(student_id)
    first = client.post(BASE, json=body)
    second = client.post(BASE, json=body)
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["sync_id"] == first.json()["sync_id"]


def test_get_sync_event(client, student_id):
    created = client.post(BASE, json=event_body(student_id)).json()
    response = client.get(f"{BASE}/{created['sync_id']}")
    assert response.status_code == 200
    assert response.json()["sync_id"] == created["sync_id"]


def test_get_unknown_sync_event_returns_404(client):
    assert client.get(f"{BASE}/{uuid.uuid4()}").status_code == 404


def test_list_filter_by_student(client, student_id):
    created = client.post(BASE, json=event_body(student_id)).json()
    response = client.get(BASE, params={"student_id": student_id, "limit": 200})
    assert response.status_code == 200
    assert created["sync_id"] in [e["sync_id"] for e in response.json()]


def test_download_of_published_package(client, student_id):
    package = make_package(client)
    body = event_body(
        student_id,
        event_type="package_download",
        records_synced=0,
        event_payload=None,
        package_id=package["package_id"],
    )
    response = client.post(BASE, json=body)
    assert response.status_code == 201
    data = response.json()
    assert data["package_version"] == "2.0"
    assert data["processed_at"] is not None


def test_download_of_draft_package_is_rejected(client, student_id):
    package = make_package(client, publish=False)
    body = event_body(
        student_id,
        event_type="package_download",
        records_synced=0,
        event_payload=None,
        package_id=package["package_id"],
    )
    assert client.post(BASE, json=body).status_code == 422


def test_failed_download_of_draft_package_is_still_logged(client, student_id):
    package = make_package(client, publish=False)
    body = event_body(
        student_id,
        event_type="package_download",
        sync_status="failed",
        records_synced=0,
        event_payload=None,
        error_code="NETWORK",
        package_id=package["package_id"],
    )
    assert client.post(BASE, json=body).status_code == 201


def test_download_of_unknown_package_returns_404(client, student_id):
    body = event_body(
        student_id,
        event_type="package_download",
        records_synced=0,
        event_payload=None,
        package_id=str(uuid.uuid4()),
    )
    assert client.post(BASE, json=body).status_code == 404
