import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="DATABASE_URL is not set"
)

BASE = "/api/v1/offline-packages"


def package_body(**overrides):
    body = {
        "subject_name": "biology",
        "class_level": "S1",
        "title": f"Package {uuid.uuid4().hex[:8]}",
        "package_version": "1.0",
        "manifest": [{"content_id": "abc", "version": "1"}],
        "manifest_uri": "https://example.com/packages/bio-s1.zip",
        "size_bytes": 1024,
        "file_path_url": "packages/bio-s1.zip",
        "checksum": "a" * 64,
    }
    body.update(overrides)
    return body


def create_package(client, **overrides):
    response = client.post(BASE, json=package_body(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def test_list_packages_defaults_to_published(client):
    response = client.get(BASE)
    assert response.status_code == 200
    assert all(p["status"] == "published" for p in response.json())


def test_create_package_starts_as_draft(client):
    body = package_body(checksum="A" * 64)
    response = client.post(BASE, json=body)
    assert response.status_code == 201
    data = response.json()
    assert data["package_id"]
    assert data["status"] == "draft"
    assert data["checksum"] == "a" * 64
    assert data["manifest_uri"] == body["manifest_uri"]


def test_status_cannot_be_chosen_on_create(client):
    data = create_package(client, status="published")
    assert data["status"] == "draft"


@pytest.mark.parametrize(
    "override",
    [
        {"checksum": "not-a-hash"},
        {"size_bytes": -1},
        {"manifest_uri": "not a url"},
        {"title": ""},
    ],
)
def test_create_package_validation_errors(client, override):
    assert client.post(BASE, json=package_body(**override)).status_code == 422


def test_create_package_missing_title_returns_422(client):
    body = package_body()
    del body["title"]
    assert client.post(BASE, json=body).status_code == 422


def test_duplicate_title_and_version_returns_409(client):
    first = create_package(client)
    response = client.post(BASE, json=package_body(title=first["title"]))
    assert response.status_code == 409


def test_get_package(client):
    package = create_package(client)
    response = client.get(f"{BASE}/{package['package_id']}")
    assert response.status_code == 200
    assert response.json()["package_id"] == package["package_id"]


def test_get_unknown_package_returns_404(client):
    assert client.get(f"{BASE}/{uuid.uuid4()}").status_code == 404


def test_list_filter_by_status(client):
    package = create_package(client)
    response = client.get(BASE, params={"status": "draft", "limit": 200})
    assert response.status_code == 200
    assert package["package_id"] in [p["package_id"] for p in response.json()]


def test_update_draft_package(client):
    package = create_package(client)
    new_title = f"Renamed {uuid.uuid4().hex[:6]}"

    response = client.patch(
        f"{BASE}/{package['package_id']}", json={"title": new_title, "size_bytes": 2048}
    )
    assert response.status_code == 200
    assert response.json()["title"] == new_title
    assert response.json()["size_bytes"] == 2048


def test_publish_with_empty_manifest_returns_422(client):
    package = create_package(client, manifest=[])
    assert client.post(f"{BASE}/{package['package_id']}/publish").status_code == 422


def test_publish_then_cannot_edit(client):
    package = create_package(client)
    published = client.post(f"{BASE}/{package['package_id']}/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    edit = client.patch(f"{BASE}/{package['package_id']}", json={"title": "Too late"})
    assert edit.status_code == 422


def test_withdraw_is_final(client):
    package = create_package(client)
    pid = package["package_id"]
    assert client.post(f"{BASE}/{pid}/publish").status_code == 200

    withdrawn = client.post(f"{BASE}/{pid}/withdraw")
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"

    assert client.post(f"{BASE}/{pid}/publish").status_code == 422
    assert client.post(f"{BASE}/{pid}/withdraw").status_code == 422


def test_withdraw_draft_package(client):
    package = create_package(client)
    response = client.post(f"{BASE}/{package['package_id']}/withdraw")
    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"
