from __future__ import annotations

import os
from uuid import UUID
from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from repositories.user import UserRepository
from schemas.user import (
    UserRegistration,
    LoginRequest,
    PasswordResetRequest,
    RecoveryRequest,
    TokenResponse,
    UserPublic,
    UserUpdate,
)
from services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


def get_service(db: Session = Depends(get_db)) -> UserService:
    pepper = os.environ.get("REDU_RECOVERY_PEPPER", "")
    return UserService(UserRepository(db), recovery_pepper=pepper)


def get_current_user(
    request: Request,
    service: UserService = Depends(get_service),
):
    auth_header = request.headers.get("Authorization", "")
    return service.current_user(auth_header)


def require_admin(
    user=Depends(get_current_user), service: UserService = Depends(get_service)
):
    service.require_admin_access(user)
    return user


@router.post(
    "/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED
)
def register(
    payload: UserRegistration,
    service: UserService = Depends(get_service),
):

    return service.register(payload)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    service: UserService = Depends(get_service),
):
    return service.login_user(payload.learner_code, payload.email, payload.password)


@router.get("/me", response_model=UserPublic)
def me(user=Depends(get_current_user)):
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    service: UserService = Depends(get_service),
):
    return None


@router.get("", response_model=list[UserPublic])
def list_users(
    admin=Depends(require_admin), service: UserService = Depends(get_service)
):
    return service.list_users()


@router.get("/{user_id}", response_model=UserPublic)
def get_user(
    user_id: UUID,
    admin=Depends(require_admin),
    service: UserService = Depends(get_service),
):
    return service.get_user(user_id)


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    admin=Depends(require_admin),
    service: UserService = Depends(get_service),
):
    values = payload.model_dump(mode="json", exclude_unset=True)
    return service.update_user(user_id, values)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    admin=Depends(require_admin),
    service: UserService = Depends(get_service),
):
    service.delete_user(user_id)


@router.post("/recovery/request")
def request_recovery(
    payload: RecoveryRequest,
    service: UserService = Depends(get_service),
):
    service.request_recovery_for_identifier(payload.learner_code, payload.email)
    return {"message": service.generic_recovery_message()}


@router.post("/recovery/complete")
def complete_recovery(
    payload: PasswordResetRequest,
    service: UserService = Depends(get_service),
):
    service.complete_recovery_or_raise(payload.token, payload.new_password)
    return {"message": "Password reset successfully"}
