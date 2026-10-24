from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import pyotp
from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()


class InvalidCredentials(Exception):
    """Raised when authentication credentials are invalid."""


class InvalidToken(Exception):
    """Raised when a token is invalid, expired, or otherwise unusable."""


def hash_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < 1:
        raise ValueError("Password must not be empty")
    return _password_hash.hash(password)


def verify_password(password: str, encoded_hash: str | None) -> bool:
    if not password or not encoded_hash:
        return False
    try:
        return _password_hash.verify(password, encoded_hash)
    except (ValueError, TypeError):
        return False


def create_access_token(
    *,
    user_id: str,
    role: str,
    secret: str,
    now: datetime | None = None,
    max_hours: int = 8,
) -> str:
    if not secret:
        raise ValueError("A signing secret is required")
    if max_hours < 1 or max_hours > 8:
        raise ValueError("max_hours must be between 1 and 8")
    issued = now or datetime.now(timezone.utc)
    expires = issued + timedelta(hours=max_hours)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": secrets.token_urlsafe(24),
        "typ": "access",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str, secret: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except (jwt.PyJWTError, TypeError, ValueError) as exc:
        raise InvalidToken("Invalid or expired access token") from exc
    if payload.get("typ") != "access" or not payload.get("sub"):
        raise InvalidToken("Invalid access token")
    return payload


def new_recovery_token() -> str:
    return secrets.token_urlsafe(32)


def recovery_token_digest(token: str, pepper: str) -> str:
    if not token or not pepper:
        raise ValueError("Token and recovery pepper are required")
    return hmac.new(pepper.encode(), token.encode(), hashlib.sha256).hexdigest()


def verify_recovery_token(token: str, expected_digest: str, pepper: str) -> bool:
    try:
        actual = recovery_token_digest(token, pepper)
    except ValueError:
        return False
    return hmac.compare_digest(actual, expected_digest)


def new_admin_totp_secret() -> str:
    return pyotp.random_base32()


def verify_admin_totp(secret: str | None, code: str, *, valid_window: int = 1) -> bool:
    if not secret or not code or not code.isdigit() or len(code) != 6:
        return False
    try:
        return pyotp.TOTP(secret).verify(code, valid_window=valid_window)
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class SessionState:
    user_id: str
    role: str
    created_at: float
    last_seen_at: float
    revoked: bool = False


class InMemorySessionStore:
    def __init__(self, inactivity_seconds: int = 600, absolute_seconds: int = 8 * 3600):
        self.inactivity_seconds = inactivity_seconds
        self.absolute_seconds = absolute_seconds
        self._sessions: dict[str, SessionState] = {}

    def create(
        self, session_id: str, user_id: str, role: str, now: float | None = None
    ) -> None:
        current = time.time() if now is None else now
        self._sessions[session_id] = SessionState(user_id, role, current, current)

    def validate_and_touch(
        self, session_id: str, now: float | None = None
    ) -> SessionState:
        current = time.time() if now is None else now
        state = self._sessions.get(session_id)
        if state is None or state.revoked:
            raise InvalidToken("Session is invalid")
        if current - state.last_seen_at >= self.inactivity_seconds:
            self._sessions.pop(session_id, None)
            raise InvalidToken("Session expired due to inactivity")
        if current - state.created_at >= self.absolute_seconds:
            self._sessions.pop(session_id, None)
            raise InvalidToken("Session reached its absolute lifetime")
        touched = SessionState(
            state.user_id, state.role, state.created_at, current, False
        )
        self._sessions[session_id] = touched
        return touched

    def revoke(self, session_id: str) -> None:
        state = self._sessions.get(session_id)
        if state is None:
            return
        self._sessions[session_id] = SessionState(
            state.user_id, state.role, state.created_at, state.last_seen_at, True
        )


class SessionStore:
    def __init__(self, inactivity_seconds: int = 600, absolute_seconds: int = 8 * 3600):
        self._store = InMemorySessionStore(inactivity_seconds, absolute_seconds)

    def create(self, session_id: str, user_id: str, role: str) -> None:
        self._store.create(session_id, user_id, role)

    def validate_and_touch(self, session_id: str) -> SessionState:
        return self._store.validate_and_touch(session_id)

    def revoke(self, session_id: str) -> None:
        self._store.revoke(session_id)


@dataclass(frozen=True)
class RecoveryTokenRecord:
    digest: str
    user_id: str
    created_at: float
    used: bool = False


class RecoveryTokenStore:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._tokens: dict[str, RecoveryTokenRecord] = {}

    def store(self, token_digest: str, user_id: str, now: float | None = None) -> str:
        current = time.time() if now is None else now
        self._tokens[token_digest] = RecoveryTokenRecord(
            digest=token_digest, user_id=user_id, created_at=current, used=False
        )
        return token_digest

    def consume(self, token_digest: str, now: float | None = None) -> str | None:
        current = time.time() if now is None else now
        record = self._tokens.get(token_digest)
        if record is None or record.used:
            return None
        if current - record.created_at > self.ttl_seconds:
            self._tokens.pop(token_digest, None)
            return None
        self._tokens[token_digest] = RecoveryTokenRecord(
            digest=record.digest,
            user_id=record.user_id,
            created_at=record.created_at,
            used=True,
        )
        return record.user_id


def get_current_user():
    return {"id": 1, "email": "learner@example.com"}
