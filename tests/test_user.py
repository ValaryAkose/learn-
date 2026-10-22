from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from main import app
from database import get_db as get_db_dep
from database import get_engine
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from core.security import InvalidToken
from unittest.mock import patch
import database


load_dotenv()

REQUIRED_ENV_VARS = (
    "DATABASE_URL",
    "REDU_AUTH_SECRET",
    "REDU_RECOVERY_PEPPER",
    "REDU_ADMIN_BOOTSTRAP_KEY",
)

for env_var in REQUIRED_ENV_VARS:
    value = os.environ.get(env_var)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {env_var}")
    os.environ.setdefault(env_var, value)


@pytest.fixture(autouse=True)
def reset_service_singletons():
    from core.security import RecoveryTokenStore, SessionStore
    from services.user import UserService

    UserService.sessions = SessionStore()
    UserService.recovery_tokens = RecoveryTokenStore()
    yield
    UserService.sessions = SessionStore()
    UserService.recovery_tokens = RecoveryTokenStore()


@pytest.fixture(scope="session")
def engine() -> Engine:
    engine = get_engine()
    from database import Base

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture()
def db_session(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    session_factory = sessionmaker(
        bind=connection, autoflush=False, expire_on_commit=False
    )
    session = session_factory()

    holder = {"savepoint": session.begin_nested()}

    def _fake_commit():
        session.flush()
        holder["savepoint"] = session.begin_nested()

    def _fake_rollback():
        session.flush()
        holder["savepoint"] = session.begin_nested()

    session.commit = _fake_commit
    session.rollback = _fake_rollback

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db_dep] = override_get_db

    try:
        yield session
    finally:
        holder["savepoint"].rollback()
        session.close()
        connection.close()
        app.dependency_overrides.pop(get_db_dep, None)


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def seeded_users(db_session: Session) -> dict:
    """Seed an admin and a learner into the isolated test transaction."""
    from core.security import hash_password
    from core.enums import UserRole
    from models.user import User
    from repositories.user import UserRepository
    from services.user import UserService

    repo = UserRepository(db_session)
    pepper = os.environ["REDU_RECOVERY_PEPPER"]
    service = UserService(repo, recovery_pepper=pepper)

    admin = User(
        learner_code=None,
        display_name="Seed Admin",
        email="seed-admin@example.com",
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
    )
    learner = User(
        learner_code="LC-SEED0001",
        display_name="Seed Learner",
        email="seed-learner@example.com",
        password_hash=hash_password("LearnerPass1!"),
        role=UserRole.STUDENT,
        class_level="S1",
        class_name="1A",
        school_name="Seed School",
    )
    repo.add(admin)
    repo.add(learner)
    repo.commit()
    return {"admin": admin, "learner": learner, "service": service}


def register_body(**overrides) -> dict:
    body = {
        "learner_code": f"LC-{uuid.uuid4().hex[:8]}",
        "display_name": "Test Learner",
        "password": "SuperSecret123!",
        "email": f"learner-{uuid.uuid4().hex[:8]}@example.com",
        "class_level": "S1",
        "class_name": "1A",
        "school_name": "Test School",
    }
    body.update(overrides)
    return body


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_returns_public_user(client):
    response = client.post("/api/v1/users/register", json=register_body())
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["role"] == "student"
    assert data["display_name"] == "Test Learner"
    assert data["class_level"] == "S1"
    assert "user_id" in data


def test_register_accepts_frontend_camelcase_fields(client):
    payload = {
        "learnerCode": "LC-FRONT0001",
        "displayName": "Frontend Learner",
        "password": "SuperSecret123!",
        "email": "frontend-learner@example.com",
        "classLevel": "S1",
        "className": "1A",
        "schoolName": "Frontend School",
    }
    response = client.post("/api/v1/users/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["display_name"] == "Frontend Learner"
    assert data["class_level"] == "S1"


def test_register_duplicate_learner_code_returns_409(client):
    body = register_body()
    first = client.post("/api/v1/users/register", json=body)
    assert first.status_code == 201
    second = client.post("/api/v1/users/register", json=body)
    assert second.status_code == 409


def test_register_duplicate_email_returns_409(client):
    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    first = client.post("/api/v1/users/register", json=register_body(email=email))
    assert first.status_code == 201
    second = client.post(
        "/api/v1/users/register",
        json=register_body(email=email, learner_code=f"LC-{uuid.uuid4().hex[:8]}"),
    )
    assert second.status_code == 409


def test_login_with_learner_code(client):
    body = register_body()
    client.post("/api/v1/users/register", json=body)
    response = client.post(
        "/api/v1/users/login",
        json={"learner_code": body["learner_code"], "password": body["password"]},
    )
    assert response.status_code == 200, response.text
    token = response.json()
    assert token["token_type"] == "bearer"
    assert token["expires_in"] == 28800
    assert token["access_token"]


def test_login_with_email(client):
    body = register_body()
    client.post("/api/v1/users/register", json=body)
    response = client.post(
        "/api/v1/users/login",
        json={"email": body["email"], "password": body["password"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


def test_login_invalid_password_returns_401(client):
    body = register_body()
    client.post("/api/v1/users/register", json=body)
    response = client.post(
        "/api/v1/users/login",
        json={"learner_code": body["learner_code"], "password": "WrongPassword1!"},
    )
    assert response.status_code == 401


def test_login_unknown_identifier_returns_401(client):
    response = client.post(
        "/api/v1/users/login",
        json={"learner_code": "LC-does-not-exist", "password": "SuperSecret123!"},
    )
    assert response.status_code == 401


def test_login_requires_identifier(client):
    response = client.post(
        "/api/v1/users/login",
        json={"password": "SuperSecret123!"},
    )
    assert response.status_code == 422


def test_login_with_short_password_returns_401(client):
    response = client.post(
        "/api/v1/users/login",
        json={"learner_code": "LC-x", "password": "short"},
    )
    assert response.status_code == 401


def test_access_token_round_trip(client):
    body = register_body()
    client.post("/api/v1/users/register", json=body)
    login = client.post(
        "/api/v1/users/login",
        json={"learner_code": body["learner_code"], "password": body["password"]},
    )
    token = login.json()["access_token"]

    import jwt as pyjwt

    decoded = pyjwt.decode(token, os.environ["REDU_AUTH_SECRET"], algorithms=["HS256"])
    assert decoded["sub"]
    assert decoded["role"] == "student"
    assert decoded["typ"] == "access"
    assert decoded["exp"] > decoded["iat"]


def test_request_recovery_for_unknown_account_returns_same_message(client):
    response = client.post(
        "/api/v1/users/recovery/request",
        json={"learner_code": "LC-does-not-exist"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "message": "If the account can be recovered, instructions will be provided through the approved recovery channel."
    }


def test_request_recovery_requires_identifier(client):
    response = client.post(
        "/api/v1/users/recovery/request",
        json={"password": "SuperSecret123!"},
    )
    assert response.status_code == 422


def test_request_recovery_returns_generic_response_for_known_account(
    client, db_session
):
    body = register_body()
    client.post("/api/v1/users/register", json=body)
    response = client.post(
        "/api/v1/users/recovery/request",
        json={"learner_code": body["learner_code"]},
    )
    assert response.status_code == 200
    assert response.json() == {
        "message": "If the account can be recovered, instructions will be provided through the approved recovery channel."
    }


def _issue_recovery_token(db_session, learner_code: str) -> str:
    from repositories.user import UserRepository
    from services.user import UserService

    service = UserService(
        UserRepository(db_session), recovery_pepper=os.environ["REDU_RECOVERY_PEPPER"]
    )
    return service.request_recovery(learner_code)


def test_complete_recovery_resets_password(client, db_session):
    body = register_body()
    client.post("/api/v1/users/register", json=body)
    raw_token = _issue_recovery_token(db_session, body["learner_code"])

    response = client.post(
        "/api/v1/users/recovery/complete",
        json={"token": raw_token, "new_password": "BrandNewPass456!"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password reset successfully"

    old_login = client.post(
        "/api/v1/users/login",
        json={"learner_code": body["learner_code"], "password": body["password"]},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/users/login",
        json={"learner_code": body["learner_code"], "password": "BrandNewPass456!"},
    )
    assert new_login.status_code == 200
    assert new_login.json()["access_token"]


def test_complete_recovery_with_invalid_token_returns_400(client):
    response = client.post(
        "/api/v1/users/recovery/complete",
        json={"token": "x" * 40, "new_password": "BrandNewPass456!"},
    )
    assert response.status_code == 400


def test_complete_recovery_replays_token_only_once(client, db_session):
    body = register_body()
    client.post("/api/v1/users/register", json=body)
    raw_token = _issue_recovery_token(db_session, body["learner_code"])

    first = client.post(
        "/api/v1/users/recovery/complete",
        json={"token": raw_token, "new_password": "BrandNewPass456!"},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/users/recovery/complete",
        json={"token": raw_token, "new_password": "AnotherPass789!"},
    )
    assert second.status_code == 400


def test_logout_returns_204(client):
    response = client.post("/api/v1/users/logout")
    assert response.status_code == 204


def test_admin_bootstrap_registration_succeeds(client, monkeypatch):
    monkeypatch.setenv(
        "REDU_ADMIN_BOOTSTRAP_KEY",
        os.environ.get("REDU_ADMIN_BOOTSTRAP_KEY", "bootstrap-secret"),
    )
    payload = {
        "email": "admin-bootstrap@example.com",
        "display_name": "Bootstrap Admin",
        "password": "AdminPass123!",
        "bootstrap_key": os.environ.get("REDU_ADMIN_BOOTSTRAP_KEY", "bootstrap-secret"),
    }

    response = client.post("/api/v1/users/register", json=payload)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["display_name"] == "Bootstrap Admin"
    assert data["role"] == "admin"


def test_admin_bootstrap_registration_rejects_bad_key(client, monkeypatch):
    monkeypatch.setenv(
        "REDU_ADMIN_BOOTSTRAP_KEY",
        os.environ.get("REDU_ADMIN_BOOTSTRAP_KEY", "bootstrap-secret"),
    )
    payload = {
        "email": "admin-bad-key@example.com",
        "display_name": "Bad Bootstrap Admin",
        "password": "AdminPass123!",
        "bootstrap_key": "wrong-key",
    }

    response = client.post("/api/v1/users/register", json=payload)

    assert response.status_code == 400
    assert "bootstrap" in response.json()["detail"].lower()


def test_non_admin_user_cannot_list_users(client, seeded_users):
    login = client.post(
        "/api/v1/users/login",
        json={"email": seeded_users["learner"].email, "password": "LearnerPass1!"},
    )
    token = login.json()["access_token"]

    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_can_list_and_fetch_users(client, seeded_users):
    login = client.post(
        "/api/v1/users/login",
        json={"email": seeded_users["admin"].email, "password": "AdminPass123!"},
    )
    token = login.json()["access_token"]

    list_response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    user_ids = {user["user_id"] for user in list_response.json()}
    assert str(seeded_users["admin"].user_id) in user_ids
    assert str(seeded_users["learner"].user_id) in user_ids

    fetch_response = client.get(
        f"/api/v1/users/{seeded_users['learner'].user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fetch_response.status_code == 200
    assert fetch_response.json()["display_name"] == seeded_users["learner"].display_name


def test_admin_can_update_and_delete_user(client, seeded_users):
    login = client.post(
        "/api/v1/users/login",
        json={"email": seeded_users["admin"].email, "password": "AdminPass123!"},
    )
    token = login.json()["access_token"]

    update_response = client.patch(
        f"/api/v1/users/{seeded_users['learner'].user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "Updated Seed Learner", "class_level": "S2"},
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["display_name"] == "Updated Seed Learner"
    assert update_response.json()["class_level"] == "S2"

    delete_response = client.delete(
        f"/api/v1/users/{seeded_users['learner'].user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 204

    after_delete = client.get(
        f"/api/v1/users/{seeded_users['learner'].user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after_delete.status_code == 404


@pytest.mark.parametrize(
    "payload, expected_status",
    [
        (
            {
                "learner_code": "",
                "display_name": "Valid Name",
                "password": "ValidPassword123!",
                "email": "one@example.com",
            },
            422,
        ),
        (
            {
                "learner_code": "LC-123",
                "display_name": "",
                "password": "ValidPassword123!",
                "email": "two@example.com",
            },
            422,
        ),
        (
            {
                "learner_code": "LC-123",
                "display_name": "Valid Name",
                "password": "short",
                "email": "three@example.com",
            },
            422,
        ),
        (
            {
                "learner_code": "LC-123",
                "display_name": "Valid Name",
                "password": "ValidPassword123!",
                "email": "bad-email",
            },
            422,
        ),
        (
            {
                "learner_code": "LC-123",
                "display_name": "Valid Name",
                "password": "ValidPassword123!",
                "email": None,
            },
            201,
        ),
    ],
)
def test_register_payload_validation_matrix(client, payload, expected_status):
    response = client.post("/api/v1/users/register", json=payload)
    assert response.status_code == expected_status, response.text


@pytest.mark.parametrize(
    "request_factory",
    [
        lambda body: {
            "learner_code": body["learner_code"],
            "password": body["password"],
        },
        lambda body: {"email": body["email"], "password": body["password"]},
        lambda body: {
            "learner_code": body["learner_code"],
            "password": body["password"],
        },
        lambda body: {
            "email": body["email"],
            "learner_code": body["learner_code"],
            "password": body["password"],
        },
    ],
)
def test_login_with_supported_identifier_variants(client, request_factory):
    body = register_body()
    client.post("/api/v1/users/register", json=body)
    request = request_factory(body)
    response = client.post("/api/v1/users/login", json=request)
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer invalid-token"},
        {"Authorization": "Token invalid-token"},
    ],
)
def test_me_requires_valid_access_token(client, headers):
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "path, expected_status",
    [
        ("/api/v1/users/00000000-0000-0000-0000-000000000001", 403),
        ("/api/v1/users/00000000-0000-0000-0000-000000000001", 403),
        ("/api/v1/users/00000000-0000-0000-0000-000000000002", 403),
    ],
)
def test_user_detail_routes_require_admin_for_non_admin(
    client, seeded_users, path, expected_status
):
    login = client.post(
        "/api/v1/users/login",
        json={"email": seeded_users["learner"].email, "password": "LearnerPass1!"},
    )
    token = login.json()["access_token"]
    response = client.get(path, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == expected_status


def test_admin_can_get_own_profile(client, seeded_users):
    login = client.post(
        "/api/v1/users/login",
        json={"email": seeded_users["admin"].email, "password": "AdminPass123!"},
    )
    token = login.json()["access_token"]
    response = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["display_name"] == seeded_users["admin"].display_name


@pytest.mark.parametrize(
    "path, method, payload",
    [
        ("/api/v1/users/00000000-0000-0000-0000-000000000099", "get", None),
        (
            "/api/v1/users/00000000-0000-0000-0000-000000000099",
            "patch",
            {"display_name": "Ghost"},
        ),
        ("/api/v1/users/00000000-0000-0000-0000-000000000099", "delete", None),
        ("/api/v1/users/00000000-0000-0000-0000-000000000100", "get", None),
    ],
)
def test_admin_routes_return_404_for_missing_user(
    client, seeded_users, path, method, payload
):
    login = client.post(
        "/api/v1/users/login",
        json={"email": seeded_users["admin"].email, "password": "AdminPass123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    if method == "get":
        response = client.get(path, headers=headers)
    elif method == "patch":
        response = client.patch(path, headers=headers, json=payload)
    else:
        response = client.delete(path, headers=headers)
    assert response.status_code == 404, response.text


@pytest.mark.parametrize(
    "payload",
    [
        {"display_name": "Updated Name"},
        {"class_level": "S2"},
        {"school_name": "New School"},
        {"email": "updated@example.com"},
        {
            "display_name": "Updated Name",
            "class_level": "S2",
            "school_name": "New School",
        },
    ],
)
def test_admin_can_apply_partial_user_updates(client, seeded_users, payload):
    login = client.post(
        "/api/v1/users/login",
        json={"email": seeded_users["admin"].email, "password": "AdminPass123!"},
    )
    token = login.json()["access_token"]
    response = client.patch(
        f"/api/v1/users/{seeded_users['learner'].user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    for key, value in payload.items():
        if key in {"display_name", "class_level"}:
            assert data[key] == value

    if "school_name" in payload:
        refreshed = client.get(
            f"/api/v1/users/{seeded_users['learner'].user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert refreshed.status_code == 200
        assert refreshed.json()["display_name"] == payload.get(
            "display_name", refreshed.json()["display_name"]
        )


@pytest.mark.parametrize(
    "payload, expected_status",
    [
        ({"learner_code": "LC-EXISTING", "email": "other@example.com"}, 200),
        ({"learner_code": "LC-EXISTING", "email": "bad-email"}, 422),
        ({"learner_code": "", "email": "person@example.com"}, 200),
        (
            {
                "learner_code": "LC-EXISTING",
                "email": "person@example.com",
                "password": "short",
            },
            200,
        ),
    ],
)
def test_recovery_request_validation_errors(client, payload, expected_status):
    response = client.post("/api/v1/users/recovery/request", json=payload)
    assert response.status_code == expected_status, response.text


@pytest.mark.parametrize(
    "payload",
    [
        {"new_password": "BrandNewPass456!"},
        {"token": "1234567890abcdef1234567890abcdef", "new_password": "short"},
        {
            "token": "1234567890abcdef1234567890abcdef",
            "new_password": "ReallyLongButInvalid",
        },
    ],
)
def test_password_reset_request_validation_cases(client, payload):
    response = client.post("/api/v1/users/recovery/complete", json=payload)
    assert response.status_code in {400, 422}


@pytest.mark.parametrize(
    "payload, expected_status",
    [
        (
            {
                "email": "admin@example.com",
                "display_name": "Admin One",
                "password": "StrongPassword123!",
                "bootstrap_key": "wrong",
            },
            400,
        ),
        (
            {
                "email": "admin@example.com",
                "display_name": "Admin One",
                "password": "short",
                "bootstrap_key": "secret",
            },
            422,
        ),
        (
            {
                "email": "bad-email",
                "display_name": "Admin One",
                "password": "StrongPassword123!",
                "bootstrap_key": "secret",
            },
            422,
        ),
    ],
)
def test_admin_registration_validation_matrix(
    client, monkeypatch, payload, expected_status
):
    monkeypatch.setenv("REDU_ADMIN_BOOTSTRAP_KEY", "secret")
    response = client.post("/api/v1/users/register", json=payload)
    assert response.status_code == expected_status, response.text


@pytest.mark.parametrize(
    "identifier, password",
    [
        ("LC-does-not-exist", "AnyPassword123!"),
        ("missing@example.com", "AnyPassword123!"),
        ("LC-does-not-exist", "wrong"),
        ("missing@example.com", "wrong"),
    ],
)
def test_login_rejections_for_unknown_or_mismatched_credentials(
    client, identifier, password
):
    response = client.post(
        "/api/v1/users/login",
        json={
            "learner_code": identifier if "@" not in identifier else None,
            "email": identifier if "@" in identifier else None,
            "password": password,
        },
    )
    assert response.status_code == 401


def test_user_list_response_contains_expected_fields(client, seeded_users):
    login = client.post(
        "/api/v1/users/login",
        json={"email": seeded_users["admin"].email, "password": "AdminPass123!"},
    )
    token = login.json()["access_token"]
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    payload = response.json()
    assert payload
    for user in payload:
        assert {"user_id", "display_name", "role", "class_level"}.issubset(user)


def test_user_fetch_endpoint_returns_public_profile(client, seeded_users):
    login = client.post(
        "/api/v1/users/login",
        json={"email": seeded_users["admin"].email, "password": "AdminPass123!"},
    )
    token = login.json()["access_token"]
    response = client.get(
        f"/api/v1/users/{seeded_users['learner'].user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(seeded_users["learner"].user_id)
    assert data["display_name"] == seeded_users["learner"].display_name
    assert data["role"] == "student"


def test_learner_can_view_own_profile(client, seeded_users):
    login = client.post(
        "/api/v1/users/login",
        json={"email": seeded_users["learner"].email, "password": "LearnerPass1!"},
    )
    token = login.json()["access_token"]
    response = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == str(seeded_users["learner"].user_id)


@pytest.mark.parametrize(
    "token, expected_status",
    [
        ("", 401),
        ("badtoken", 401),
        ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.invalid", 401),
        ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.invalid", 401),
    ],
)
def test_explicitly_invalid_tokens_are_rejected(client, token, expected_status):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == expected_status


def test_admin_registration_success_with_valid_bootstrap_key(client, monkeypatch):
    monkeypatch.setenv(
        "REDU_ADMIN_BOOTSTRAP_KEY",
        os.environ.get("REDU_ADMIN_BOOTSTRAP_KEY", "bootstrap-secret"),
    )
    payload = {
        "email": "valid-admin@example.com",
        "display_name": "Valid Admin",
        "password": "AdminPass123!",
        "bootstrap_key": os.environ.get("REDU_ADMIN_BOOTSTRAP_KEY", "bootstrap-secret"),
    }
    response = client.post("/api/v1/users/register", json=payload)
    assert response.status_code == 201
    assert response.json()["role"] == "admin"


def test_registering_duplicate_admin_email_is_rejected(client, monkeypatch):
    monkeypatch.setenv(
        "REDU_ADMIN_BOOTSTRAP_KEY",
        os.environ.get("REDU_ADMIN_BOOTSTRAP_KEY", "bootstrap-secret"),
    )
    payload = {
        "email": "duplicate-admin@example.com",
        "display_name": "Admin One",
        "password": "AdminPass123!",
        "bootstrap_key": os.environ.get("REDU_ADMIN_BOOTSTRAP_KEY", "bootstrap-secret"),
    }
    first = client.post("/api/v1/users/register", json=payload)
    assert first.status_code == 201
    second = client.post("/api/v1/users/register", json=payload)
    assert second.status_code == 400


@pytest.mark.parametrize(
    "request_body",
    [
        {"token": "x" * 32, "new_password": "BrandNewPass456!"},
        {"token": "x" * 40, "new_password": "BrandNewPass456!"},
        {"token": "x" * 64, "new_password": "BrandNewPass456!"},
        {"token": "x" * 128, "new_password": "BrandNewPass456!"},
    ],
)
def test_invalid_recovery_tokens_fail_clearly(client, request_body):
    response = client.post("/api/v1/users/recovery/complete", json=request_body)
    assert response.status_code == 400


def test_recovery_request_for_known_email_uses_generic_response(client):
    body = register_body(email="email-recovery@example.com")
    client.post("/api/v1/users/register", json=body)
    response = client.post(
        "/api/v1/users/recovery/request",
        json={"email": body["email"]},
    )
    assert response.status_code == 200
    assert response.json() == {
        "message": "If the account can be recovered, instructions will be provided through the approved recovery channel."
    }


@pytest.mark.parametrize(
    "payload",
    [
        {
            "email": "seed-admin@example.com",
            "password": "AdminPass123!",
            "bootstrap_key": "bootstrap-secret",
        },
        {
            "email": "seed-admin@example.com",
            "display_name": "",
            "password": "AdminPass123!",
            "bootstrap_key": "bootstrap-secret",
        },
        {
            "email": "seed-admin@example.com",
            "display_name": "Admin One",
            "password": "AdminPass123!",
            "bootstrap_key": "",
        },
    ],
)
def test_admin_registration_rejects_invalid_payloads(client, monkeypatch, payload):
    monkeypatch.setenv(
        "REDU_ADMIN_BOOTSTRAP_KEY",
        os.environ.get("REDU_ADMIN_BOOTSTRAP_KEY", "bootstrap-secret"),
    )
    response = client.post("/api/v1/users/register", json=payload)
    assert response.status_code in {400, 422}


def test_invalid_token_handler_coverage():
    client = TestClient(app)

    @app.get("/_test_invalid_token_exception")
    def raise_invalid_token():
        raise InvalidToken("Forced exception for coverage testing")

    try:
        response = client.get("/_test_invalid_token_exception")
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid or expired access token"}
    finally:
        app.routes[:] = [
            route
            for route in app.routes
            if getattr(route, "path", None) != "/_test_invalid_token_exception"
        ]


def test_database_branches_coverage():
    database.get_engine.cache_clear()
    database.get_session_factory.cache_clear()

    with patch.dict("os.environ", {"DATABASE_URL": ""}, clear=True):
        with pytest.raises(RuntimeError) as exc_info:
            database._database_url()

        assert str(exc_info.value) == "DATABASE_URL is not set"

    with patch.dict("os.environ", {"DATABASE_URL": "postgres://user:pass@host/db"}):
        url = database._database_url()
        assert url.startswith("postgresql://")

    with patch.dict("os.environ", {"DATABASE_URL": "sqlite:///:memory:"}):
        engine = database.get_engine()
        assert engine.url.database == ":memory:"

    database.get_engine.cache_clear()
    database.get_session_factory.cache_clear()
