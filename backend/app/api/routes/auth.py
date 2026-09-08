"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.errors import APIError
from app.schemas.auth import RegisteredUser, RegisterRequest, RegisterResponse
from app.services.auth import EmailAlreadyRegisteredError, register_user

router = APIRouter(prefix="/auth", tags=["authentication"])


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
            code="AUTH_EMAIL_ALREADY_EXISTS",
            message="该邮箱已注册",
        ) from error

    return RegisterResponse(data=RegisteredUser.model_validate(user))
