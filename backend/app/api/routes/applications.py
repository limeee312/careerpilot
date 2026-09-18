"""Authenticated application and timeline endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import get_current_user
from app.errors import APIError
from app.models.application import ApplicationStatus
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationEventCreate,
    ApplicationEventListResponse,
    ApplicationEventResponse,
    ApplicationEventUpdate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatusUpdate,
    ApplicationUpdate,
)
from app.services.application import (
    ApplicationEventNotFoundError,
    ApplicationInvalidSnapshotError,
    ApplicationNotFoundError,
    ApplicationSourceMismatchError,
    ApplicationSourceNotFoundError,
    create_application,
    create_application_event,
    delete_application,
    delete_application_event,
    get_application,
    list_application_events,
    list_applications,
    serialize_application,
    serialize_application_event,
    serialize_application_list_item,
    update_application,
    update_application_event,
    update_application_status,
)

router = APIRouter(tags=["applications"])


def _application_not_found(error: Exception) -> APIError:
    return APIError(
        status_code=status.HTTP_404_NOT_FOUND,
        code="APPLICATION_NOT_FOUND",
        message="投递记录不存在",
    )


def _event_not_found(error: Exception) -> APIError:
    return APIError(
        status_code=status.HTTP_404_NOT_FOUND,
        code="APPLICATION_EVENT_NOT_FOUND",
        message="投递事件不存在",
    )


def _source_error(error: Exception) -> APIError:
    if isinstance(error, ApplicationSourceNotFoundError):
        return APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="APPLICATION_SOURCE_NOT_FOUND",
            message="关联的职位或岗位版简历不存在",
        )
    if isinstance(error, ApplicationSourceMismatchError):
        return APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="APPLICATION_SOURCE_MISMATCH",
            message="职位与岗位版简历不属于同一岗位",
        )
    return APIError(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="APPLICATION_INVALID_SNAPSHOT",
        message="投递记录必须保留公司与岗位名称",
    )


@router.post(
    "/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_application_endpoint(
    payload: ApplicationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApplicationResponse:
    """Create an application and its initial timeline event atomically."""

    try:
        application = await create_application(session, current_user.id, payload)
    except (
        ApplicationSourceNotFoundError,
        ApplicationSourceMismatchError,
        ApplicationInvalidSnapshotError,
    ) as error:
        raise _source_error(error) from error
    return ApplicationResponse(data=serialize_application(application))


@router.get("/applications", response_model=ApplicationListResponse)
async def list_applications_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    process_status: Annotated[ApplicationStatus | None, Query()] = None,
) -> ApplicationListResponse:
    """List current-user applications with an optional status filter."""

    applications = await list_applications(
        session,
        current_user.id,
        process_status,
    )
    return ApplicationListResponse(
        data=[serialize_application_list_item(item) for item in applications]
    )


@router.get("/applications/{application_id}", response_model=ApplicationResponse)
async def get_application_endpoint(
    application_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApplicationResponse:
    """Return one owned application with its timeline."""

    try:
        application = await get_application(session, current_user.id, application_id)
    except ApplicationNotFoundError as error:
        raise _application_not_found(error) from error
    return ApplicationResponse(data=serialize_application(application))


@router.put("/applications/{application_id}", response_model=ApplicationResponse)
async def update_application_endpoint(
    application_id: UUID,
    payload: ApplicationUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApplicationResponse:
    """Update editable application metadata and source links."""

    try:
        application = await update_application(
            session,
            current_user.id,
            application_id,
            payload,
        )
    except ApplicationNotFoundError as error:
        raise _application_not_found(error) from error
    except (
        ApplicationSourceNotFoundError,
        ApplicationSourceMismatchError,
        ApplicationInvalidSnapshotError,
    ) as error:
        raise _source_error(error) from error
    return ApplicationResponse(data=serialize_application(application))


@router.delete(
    "/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_application_endpoint(
    application_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    """Delete one owned application and its events."""

    try:
        await delete_application(session, current_user.id, application_id)
    except ApplicationNotFoundError as error:
        raise _application_not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/applications/{application_id}/status",
    response_model=ApplicationResponse,
)
async def update_application_status_endpoint(
    application_id: UUID,
    payload: ApplicationStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApplicationResponse:
    """Update the overall process status and terminal stage."""

    try:
        application = await update_application_status(
            session,
            current_user.id,
            application_id,
            payload,
        )
    except ApplicationNotFoundError as error:
        raise _application_not_found(error) from error
    return ApplicationResponse(data=serialize_application(application))


@router.post(
    "/applications/{application_id}/events",
    response_model=ApplicationEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_application_event_endpoint(
    application_id: UUID,
    payload: ApplicationEventCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApplicationEventResponse:
    """Append a timeline event and move the current stage."""

    try:
        event = await create_application_event(
            session,
            current_user.id,
            application_id,
            payload,
        )
    except ApplicationNotFoundError as error:
        raise _application_not_found(error) from error
    return ApplicationEventResponse(data=serialize_application_event(event))


@router.get(
    "/applications/{application_id}/events",
    response_model=ApplicationEventListResponse,
)
async def list_application_events_endpoint(
    application_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApplicationEventListResponse:
    """Return an owned application's chronological timeline."""

    try:
        events = await list_application_events(
            session,
            current_user.id,
            application_id,
        )
    except ApplicationNotFoundError as error:
        raise _application_not_found(error) from error
    return ApplicationEventListResponse(
        data=[serialize_application_event(event) for event in events]
    )


@router.put(
    "/application-events/{event_id}",
    response_model=ApplicationEventResponse,
)
async def update_application_event_endpoint(
    event_id: UUID,
    payload: ApplicationEventUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApplicationEventResponse:
    """Replace one owned timeline event."""

    try:
        event = await update_application_event(
            session,
            current_user.id,
            event_id,
            payload,
        )
    except ApplicationEventNotFoundError as error:
        raise _event_not_found(error) from error
    return ApplicationEventResponse(data=serialize_application_event(event))


@router.delete(
    "/application-events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_application_event_endpoint(
    event_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    """Delete one owned timeline event."""

    try:
        await delete_application_event(session, current_user.id, event_id)
    except ApplicationEventNotFoundError as error:
        raise _event_not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
