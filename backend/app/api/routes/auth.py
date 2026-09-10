"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db_session
from app.dependencies import AUTH_COOKIE_NAME, get_current_user
from app.errors import APIError
from app.models.user import User
from app.schemas.auth import (
    CurrentUser,
    CurrentUserResponse,
    LoginRequest,
    RegisteredUser,
    RegisterRequest,
    RegisterResponse,
)
from app.security import create_access_token
from app.services.auth import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
settings = get_settings()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    registration: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RegisterResponse:
    """Create an account without exposing authentication secrets."""

    try:
        user = await register_user(session, registration)
    except EmailAlreadyRegisteredError as error:
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="AUTH_EMAIL_EXISTS",
            message="该邮箱已注册",
        ) from error

    return RegisterResponse(data=RegisteredUser.model_validate(user))


@router.post("/login", response_model=CurrentUserResponse)
async def login(
    credentials: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CurrentUserResponse:
    """Authenticate a user and establish a short-lived cookie session."""

    try:
        user = await authenticate_user(session, credentials)
    except InvalidCredentialsError as error:
        raise APIError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTH_INVALID_CREDENTIALS",
            message="邮箱或密码错误",
        ) from error

    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=create_access_token(user.id),
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )
    return CurrentUserResponse(data=CurrentUser.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    """Clear the browser session cookie."""

    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> CurrentUserResponse:
    """Return the account associated with the current cookie session."""

    return CurrentUserResponse(data=CurrentUser.model_validate(current_user))
