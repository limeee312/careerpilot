"""Authenticated Resume Master endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import get_current_user
from app.errors import APIError
from app.models.user import User
from app.schemas.resume import ResumeMasterResponse, ResumeMasterUpsert
from app.schemas.resume_version import (
    ResumeVersionCreate,
    ResumeVersionListResponse,
    ResumeVersionResponse,
)
from app.services.resume import (
    DuplicateResumeSkillError,
    ResumeSaveConflictError,
    ResumeSectionNotFoundError,
    get_resume_master,
    serialize_resume_master,
    upsert_resume_master,
)
from app.services.resume_version import (
    ResumeVersionInvalidDraftError,
    ResumeVersionNotFoundError,
    ResumeVersionSourceNotFoundError,
    create_resume_version,
    get_resume_version,
    list_resume_versions,
    serialize_resume_version,
    serialize_resume_version_list_item,
)

router = APIRouter(prefix="/resume", tags=["resume"])


@router.get("/versions", response_model=ResumeVersionListResponse)
async def read_resume_versions(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResumeVersionListResponse:
    """Return saved targeted resumes owned by the authenticated user."""

    versions = await list_resume_versions(session, current_user.id)
    return ResumeVersionListResponse(
        data=[serialize_resume_version_list_item(item) for item in versions]
    )


@router.post(
    "/versions",
    response_model=ResumeVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_resume_version(
    payload: ResumeVersionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResumeVersionResponse:
    """Validate and persist a user-confirmed Resume Tailor draft."""

    try:
        version = await create_resume_version(session, current_user.id, payload)
    except ResumeVersionSourceNotFoundError as error:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESUME_VERSION_SOURCE_NOT_FOUND",
            message="用于保存的岗位匹配结果不存在",
        ) from error
    except ResumeVersionInvalidDraftError as error:
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="RESUME_VERSION_INVALID_DRAFT",
            message="当前草稿未通过真实性校验，请检查人工修改",
        ) from error
    return ResumeVersionResponse(data=serialize_resume_version(version))


@router.get("/versions/{version_id}", response_model=ResumeVersionResponse)
async def read_resume_version(
    version_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResumeVersionResponse:
    """Return one saved targeted resume within the current user's scope."""

    try:
        version = await get_resume_version(session, current_user.id, version_id)
        data = serialize_resume_version(version)
    except ResumeVersionNotFoundError as error:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESUME_VERSION_NOT_FOUND",
            message="岗位版简历不存在",
        ) from error
    except ResumeVersionInvalidDraftError as error:
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="RESUME_VERSION_INVALID_DATA",
            message="岗位版简历数据不完整",
        ) from error
    return ResumeVersionResponse(data=data)


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
