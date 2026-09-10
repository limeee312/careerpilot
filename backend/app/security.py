"""Password hashing and signed-token primitives for authentication."""

import unicodedata
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.config import Settings, get_settings

JWT_ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()


def normalize_password(password: str) -> str:
    """Normalize Unicode without trimming or changing intentional whitespace."""

    return unicodedata.normalize("NFC", password)


def hash_password(password: str) -> str:
    """Hash a password using pwdlib's recommended Argon2id configuration."""

    return password_hash.hash(normalize_password(password))


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password against a stored hash."""

    return password_hash.verify(normalize_password(password), encoded_hash)


class InvalidAccessTokenError(Exception):
    """Raised when an access token cannot identify an active session."""


def create_access_token(
    user_id: UUID,
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> str:
    """Create a short-lived JWT whose subject is the authenticated user UUID."""

    runtime_settings = settings or get_settings()
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=runtime_settings.jwt_expire_minutes)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": issued_at,
            "exp": expires_at,
        },
        runtime_settings.jwt_secret.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(
    token: str,
    *,
    settings: Settings | None = None,
) -> UUID:
    """Validate a JWT and return its user UUID subject."""

    runtime_settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            runtime_settings.jwt_secret.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "iat", "exp"]},
        )
        return UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise InvalidAccessTokenError from error
