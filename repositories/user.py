from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _normalize_user_id(user_id):
        if user_id is None:
            return None
        if isinstance(user_id, UUID):
            return user_id
        return UUID(str(user_id))

    def by_user_id(self, user_id):
        normalized_user_id = self._normalize_user_id(user_id)
        return self.db.get(User, normalized_user_id)

    def by_learner_code(self, learner_code: str):
        return self.db.scalar(select(User).where(User.learner_code == learner_code))

    def by_email(self, email: str):
        return self.db.scalar(select(User).where(User.email == email))

    def list_all(self) -> list[User]:
        return list(self.db.scalars(select(User)).all())

    def add(self, user):
        self.db.add(user)
        self.db.flush()
        return user

    def delete(self, user) -> None:
        self.db.delete(user)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
