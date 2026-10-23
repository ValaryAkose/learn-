from __future__ import annotations

import hmac
import os
import secrets
from models.user import User
from sqlalchemy import UUID

from core.enums import UserRole
from core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
)
from core.security import (
    InvalidCredentials,
    InvalidToken,
    RecoveryTokenStore,
    SessionStore,
    create_access_token,
    decode_access_token,
    hash_password,
    new_recovery_token,
    recovery_token_digest,
    verify_password,
)


class UserService:
    sessions = SessionStore()
    recovery_tokens = RecoveryTokenStore()

    def __init__(self, repository, *, recovery_pepper: str):
        self.repository = repository
        self.recovery_pepper = recovery_pepper

    def register(self, payload) -> User:
        if payload.role == UserRole.ADMIN or payload.bootstrap_key:
            bootstrap = payload.bootstrap_key or ""
            return self.register_admin(payload, bootstrap)

        return self.register_learner(payload)

    def register_learner(self, data):
        if data.learner_code and self.repository.by_learner_code(data.learner_code):
            raise ConflictError("Learner code is already registered")
        if data.email and self.repository.by_email(str(data.email)):
            raise ConflictError("Email is already registered")

        user = User(
            learner_code=data.learner_code,
            display_name=data.display_name,
            email=str(data.email) if data.email else None,
            password_hash=hash_password(data.password),
            role=data.role,
            class_level=data.class_level,
            class_name=data.class_name,
            school_name=data.school_name,
        )
        self.repository.add(user)
        self.repository.commit()
        return user

    def register_admin(self, data, bootstrap_key: str) -> User:

        expected = os.environ.get("REDU_ADMIN_BOOTSTRAP_KEY", "bootstrap-secret")

        if not expected or not hmac.compare_digest(str(data.bootstrap_key), expected):
            raise AppError("Invalid bootstrap key")
        if self.repository.by_email(str(data.email)):
            raise AppError("Email is already registered")
        user = User(
            learner_code=None,
            display_name=data.display_name,
            email=str(data.email),
            password_hash=hash_password(data.password),
            role=UserRole.ADMIN,
        )
        self.repository.add(user)
        self.repository.commit()
        return user

    @staticmethod
    def normalize_identifier(learner_code: str | None, email: str | None) -> str:
        identifier = (learner_code or (str(email) if email else "")).strip()
        if not identifier:
            raise BusinessRuleError("Provide learner_code or email")
        return identifier

    def authenticate(self, identifier: str, password: str):
        user = self.repository.by_learner_code(identifier) or self.repository.by_email(
            identifier
        )
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid identifier or password")
        return user

    def login_user(
        self, learner_code: str | None, email: str | None, password: str
    ) -> dict[str, str | int]:
        identifier = self.normalize_identifier(learner_code, email)
        user = self.authenticate(identifier, password)

        secret = os.environ.get("REDU_AUTH_SECRET", "")
        if not secret:
            raise AppError("REDU_AUTH_SECRET is not configured")

        role_str = user.role.value if hasattr(user.role, "value") else str(user.role)

        token = create_access_token(
            user_id=str(user.user_id), role=role_str, secret=secret
        )
        self.create_session(str(user.user_id), role_str)
        return {"access_token": token, "token_type": "bearer", "expires_in": 28800}

    def current_user(self, authorization_header: str) -> User:
        secret = os.environ.get("REDU_AUTH_SECRET", "")
        if not secret:
            raise AppError("REDU_AUTH_SECRET is not configured")

        if not authorization_header or not authorization_header.lower().startswith(
            "bearer "
        ):
            raise AuthenticationError("Missing authentication token")

        token = authorization_header[7:].strip()
        if not token:
            raise AuthenticationError("Missing authentication token")

        try:
            payload = decode_access_token(token, secret)
        except (InvalidToken, InvalidCredentials) as exc:
            raise AuthenticationError(str(exc)) from exc
        user = self.repository.by_user_id(payload["sub"])
        if user is None:
            raise AuthenticationError("User not found")
        return user

    def list_users(self) -> list[User]:
        return self.repository.list_all()

    def get_user(self, user_id):
        user = self.repository.by_user_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    def update_user(self, user_id, values: dict) -> User:
        user = self.get_user(user_id)

        if "role" in values and values["role"] is not None:
            if isinstance(values["role"], str):
                values["role"] = UserRole(values["role"])

        for field, value in values.items():
            if value is not None:
                setattr(user, field, value)
        self.repository.add(user)
        self.repository.commit()
        return user

    def delete_user(self, user_id) -> None:
        user = self.get_user(user_id)
        self.repository.delete(user)
        self.repository.commit()

    def is_admin(self, user: User) -> bool:
        return user and str(user.role.value).lower() == "admin"

    def require_admin_access(self, user: User) -> None:
        if not self.is_admin(user):
            raise AuthorizationError("Admin access required")

    def require_self_or_admin_access(
        self, current_user: User, target_user_id: UUID
    ) -> None:
        if self.is_admin(current_user):
            return
        if current_user.user_id == target_user_id:
            return
        raise AuthorizationError("Access denied: Insufficient permissions")

    def get_user_with_access_check(
        self, current_user: User, target_user_id: UUID
    ) -> User:
        self.require_self_or_admin_access(current_user, target_user_id)
        return self.get_user(target_user_id)

    def update_user_with_access_check(
        self, current_user: User, target_user_id: UUID, values: dict
    ) -> User:
        self.require_self_or_admin_access(current_user, target_user_id)

        if not self.is_admin(current_user) and "role" in values:
            values.pop("role")

        return self.update_user(target_user_id, values)

    def make_recovery_token(self) -> tuple[str, str]:
        raw = new_recovery_token()
        return raw, recovery_token_digest(raw, self.recovery_pepper)

    def request_recovery(self, identifier: str) -> str | None:
        user = self.repository.by_learner_code(identifier) or self.repository.by_email(
            identifier
        )
        if user is None:
            return None
        raw, digest = self.make_recovery_token()
        self.recovery_tokens.store(digest, str(user.user_id))
        return raw

    def request_recovery_for_identifier(
        self, learner_code: str | None, email: str | None
    ) -> str | None:
        identifier = self.normalize_identifier(learner_code, email)
        return self.request_recovery(identifier)

    def complete_recovery(self, raw_token: str, new_password: str) -> bool:
        digest = recovery_token_digest(raw_token, self.recovery_pepper)
        user_id = self.recovery_tokens.consume(digest)
        if user_id is None:
            return False
        user = self.repository.by_user_id(user_id)
        if user is None:
            return False
        user.password_hash = hash_password(new_password)
        self.repository.add(user)
        self.repository.commit()
        return True

    def complete_recovery_or_raise(self, raw_token: str, new_password: str) -> bool:
        if not self.complete_recovery(raw_token, new_password):
            raise AppError("Invalid or expired recovery token")
        return True

    def create_session(self, user_id: str, role: str) -> str:
        session_id = secrets.token_urlsafe(32)
        self.sessions.create(session_id, user_id, role)
        return session_id

    def validate_session(self, session_id: str):
        return self.sessions.validate_and_touch(session_id)

    def revoke_session(self, session_id: str) -> None:
        self.sessions.revoke(session_id)

    @staticmethod
    def generic_recovery_message() -> str:
        return "If the account can be recovered, instructions will be provided through the approved recovery channel."
