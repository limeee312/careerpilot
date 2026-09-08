"""Authentication API schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PASSWORD_MIN_LENGTH = 15
PASSWORD_MAX_LENGTH = 128


class RegisterRequest(BaseModel):
    """Validated account registration input."""

    email: EmailStr
    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )

    @field_validator("email", mode="before")
    @classmethod
    def trim_email(cls, value: object) -> object:
        """Remove accidental surrounding whitespace before validation."""

        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: EmailStr) -> str:
        """Apply the approved storage normalization."""

        return str(value).lower()


class RegisteredUser(BaseModel):
    """Safe subset of a newly created account."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr


class RegisterResponse(BaseModel):
    """Registration success envelope."""

    data: RegisteredUser
