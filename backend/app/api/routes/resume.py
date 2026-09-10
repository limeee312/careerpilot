"""Authenticated Resume Master endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import get_current_user
from app.errors import APIError
from app.models.user import User
from app.schemas.resume import ResumeMasterResponse, ResumeMasterUpsert
from app.services.resume import (
    DuplicateResumeSkillError,
    ResumeSaveConflictError,
    ResumeSectionNotFoundError,
    get_resume_master,
    serialize_resume_master,
    upsert_resume_master,
)

router = APIRouter(prefix="/resume", tags=["resume"])


@router.get("/master", response_model=ResumeMasterResponse)
async def read_resume_master(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResumeMasterResponse:
    """Return the authenticated user's resume or a null data field."""

    master = await get_resume_master(session, current_user.id)
    return ResumeMasterResponse(
        data=serialize_resume_master(master) if master is not None else None
    )


@router.put("/master", response_model=ResumeMasterResponse)
async def save_resume_master(
    payload: ResumeMasterUpsert,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResumeMasterResponse:
    """Create or fully update the authenticated user's structured resume."""

    try:
        master = await upsert_resume_master(session, current_user.id, payload)
    except ResumeSectionNotFoundError as error:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESUME_SECTION_NOT_FOUND",
            message="简历条目不存在",
        ) from error
    except DuplicateResumeSkillError as error:
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="RESUME_DUPLICATE_SKILL",
            message="同一简历不能包含重名技能",
        ) from error
    except ResumeSaveConflictError as error:
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="RESUME_SAVE_CONFLICT",
            message="简历正在被更新，请刷新后重试",
        ) from error

    return ResumeMasterResponse(data=serialize_resume_master(master))
