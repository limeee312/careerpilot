"""Authentication application services."""

from pwdlib.exceptions import UnknownHashError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.security import hash_password, verify_password

DUMMY_PASSWORD_HASH = hash_password("not-a-real-careerpilot-user-password")


class EmailAlreadyRegisteredError(Exception):
    """Raised when registration targets an existing account email."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials do not identify a user."""


def _is_email_uniqueness_error(error: IntegrityError) -> bool:
    diagnostic = getattr(error.orig, "diag", None)
    return getattr(diagnostic, "constraint_name", None) == "users_email_idx"


async def register_user(
    session: AsyncSession,
    registration: RegisterRequest,
) -> User:
    """Persist a user with a one-way password hash.

    The pre-check gives a useful response in the common case. The database index
    remains authoritative and handles concurrent registrations safely.
    """

    normalized_email = str(registration.email)
    existing_user_id = await session.scalar(
        select(User.id).where(User.email == normalized_email)
    )
    if existing_user_id is not None:
        raise EmailAlreadyRegisteredError

    user = User(
        email=normalized_email,
        password_hash=hash_password(registration.password),
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        if _is_email_uniqueness_error(error):
            raise EmailAlreadyRegisteredError from error
        raise

    await session.refresh(user)
    return user


async def authenticate_user(
    session: AsyncSession,
    credentials: LoginRequest,
) -> User:
    """Validate credentials without revealing whether an email exists."""

    user = await session.scalar(
        select(User).where(User.email == str(credentials.email))
    )
    encoded_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH

    try:
        password_matches = verify_password(credentials.password, encoded_hash)
    except UnknownHashError:
        password_matches = False

    if user is None or not password_matches:
        raise InvalidCredentialsError
    return user
