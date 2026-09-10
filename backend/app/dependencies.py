"""Request dependencies shared by protected API routes."""

from typing import Annotated

from fastapi import Cookie, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.errors import APIError
from app.models.user import User
from app.security import InvalidAccessTokenError, decode_access_token

AUTH_COOKIE_NAME = "careerpilot_session"


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    session_token: Annotated[
        str | None,
        Cookie(alias=AUTH_COOKIE_NAME),
    ] = None,
) -> User:
    """Resolve the authenticated user exclusively from the signed session cookie."""

    if session_token is None:
        raise _authentication_required()

    try:
        user_id = decode_access_token(session_token)
    except InvalidAccessTokenError as error:
        raise _authentication_required() from error

    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise _authentication_required()
    return user


def _authentication_required() -> APIError:
    return APIError(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="AUTH_REQUIRED",
        message="请先登录",
    )
