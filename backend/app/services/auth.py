"""Authentication application services."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.security import hash_password


class EmailAlreadyRegisteredError(Exception):
    """Raised when registration targets an existing account email."""


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
