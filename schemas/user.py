from __future__ import annotations

from uuid import UUID

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from core.enums import UserRole


class UserRegistration(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    display_name: str = Field(
        min_length=1,
        max_length=100,
        validation_alias=AliasChoices("display_name", "displayName", "fullName"),
    )
    password: str = Field(min_length=12, max_length=128)
    email: EmailStr | None = None

    role: UserRole = Field(
        default=UserRole.STUDENT,
        validation_alias=AliasChoices("role", "user_role"),
    )

    learner_code: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
        validation_alias=AliasChoices("learner_code", "learnerCode", "learnercode"),
    )
    class_level: str | None = Field(
        default=None,
        validation_alias=AliasChoices("class_level", "classLevel"),
    )
    class_name: str | None = Field(
        default=None,
        max_length=50,
        validation_alias=AliasChoices("class_name", "className"),
    )
    school_name: str | None = Field(
        default=None,
        max_length=100,
        validation_alias=AliasChoices("school_name", "schoolName"),
    )

    bootstrap_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
        validation_alias=AliasChoices("bootstrap_key", "bootstrapKey"),
    )

    @field_validator("display_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field must not be blank")
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    learner_code: str | None = Field(
        default=None,
        max_length=20,
        validation_alias=AliasChoices("learner_code", "learnerCode", "learnercode"),
    )
    email: EmailStr | None = None
    password: str = Field(min_length=1, max_length=128)
    mfa_code: str | None = Field(
        default=None,
        pattern=r"^\d{6}$",
        validation_alias=AliasChoices("mfa_code", "mfaCode"),
    )

    @field_validator("learner_code")
    @classmethod
    def strip_learner_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: UUID
    display_name: str
    role: str
    class_level: str | None = None


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    class_level: str | None = None
    class_name: str | None = Field(default=None, max_length=50)
    school_name: str | None = Field(default=None, max_length=100)
    role: UserRole | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 28800


class RecoveryRequest(BaseModel):
    learner_code: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)
