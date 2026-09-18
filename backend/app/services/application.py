"""Application persistence, ownership boundaries, and timeline transitions."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import (
    Application,
    ApplicationEvent,
    ApplicationStage,
    ApplicationStatus,
)
from app.models.job import Job
from app.models.resume_version import ResumeVersion, ResumeVersionStatus
from app.schemas.application import (
    ApplicationCreate,
    ApplicationData,
    ApplicationEventCreate,
    ApplicationEventData,
    ApplicationEventUpdate,
    ApplicationListItem,
    ApplicationStatusUpdate,
    ApplicationUpdate,
)


class ApplicationNotFoundError(Exception):
    """Raised when an application is absent from the current user's scope."""


class ApplicationEventNotFoundError(Exception):
    """Raised when an event is absent from the current user's scope."""


class ApplicationSourceNotFoundError(Exception):
    """Raised when a linked job or resume version is not user-owned."""


class ApplicationSourceMismatchError(Exception):
    """Raised when a resume version and job describe different jobs."""


class ApplicationInvalidSnapshotError(Exception):
    """Raised when an application would not retain required snapshot labels."""


async def _owned_job(
    session: AsyncSession,
    user_id: UUID,
    job_id: UUID,
) -> Job:
    job = await session.scalar(
        select(Job).where(Job.id == job_id, Job.user_id == user_id)
    )
    if job is None:
        raise ApplicationSourceNotFoundError
    return job


async def _owned_version(
    session: AsyncSession,
    user_id: UUID,
    version_id: UUID,
) -> ResumeVersion:
    version = await session.scalar(
        select(ResumeVersion).where(
            ResumeVersion.id == version_id,
            ResumeVersion.user_id == user_id,
            ResumeVersion.status == ResumeVersionStatus.SAVED,
        )
    )
    if version is None:
        raise ApplicationSourceNotFoundError
    return version


async def _load_application(
    session: AsyncSession,
    user_id: UUID,
    application_id: UUID,
    *,
    with_events: bool = False,
) -> Application:
    statement = select(Application).where(
        Application.id == application_id,
        Application.user_id == user_id,
    )
    if with_events:
        statement = statement.options(selectinload(Application.events))
    application = await session.scalar(statement)
    if application is None:
        raise ApplicationNotFoundError
    return application


def serialize_application_list_item(
    application: Application,
) -> ApplicationListItem:
    """Serialize stable columns without touching a lazy event relationship."""

    return ApplicationListItem(
        id=application.id,
        job_id=application.job_id,
        resume_version_id=application.resume_version_id,
        company_name=application.company_name,
        job_title=application.job_title,
        job_url=application.job_url,
        applied_at=application.applied_at,
        current_stage=application.current_stage,
        current_round=application.current_round,
        process_status=application.process_status,
        note=application.note,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


def serialize_application_event(event: ApplicationEvent) -> ApplicationEventData:
    """Serialize one timeline event."""

    return ApplicationEventData(
        id=event.id,
        application_id=event.application_id,
        event_type=event.event_type,
        custom_event_name=event.custom_event_name,
        round_no=event.round_no,
        occurred_at=event.occurred_at,
        outcome=event.outcome,
        note=event.note,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def serialize_application(application: Application) -> ApplicationData:
    """Serialize one detail view with its deterministically ordered timeline."""

    item = serialize_application_list_item(application)
    return ApplicationData(
        **item.model_dump(),
        events=[serialize_application_event(event) for event in application.events],
    )


async def create_application(
    session: AsyncSession,
    user_id: UUID,
    payload: ApplicationCreate,
) -> Application:
    """Atomically persist an application and its initial APPLICATION event."""

    job = (
        await _owned_job(session, user_id, payload.job_id)
        if payload.job_id is not None
        else None
    )
    version = (
        await _owned_version(session, user_id, payload.resume_version_id)
        if payload.resume_version_id is not None
        else None
    )
    if version is not None:
        if job is not None and version.job_id != job.id:
            raise ApplicationSourceMismatchError
        if job is None:
            job = await _owned_job(session, user_id, version.job_id)

    company_name = payload.company_name or (job.company_name if job else None)
    job_title = payload.job_title or (job.title if job else None)
    if company_name is None or job_title is None:
        raise ApplicationInvalidSnapshotError

    application = Application(
        user_id=user_id,
        job_id=job.id if job is not None else None,
        resume_version_id=version.id if version is not None else None,
        company_name=company_name,
        job_title=job_title,
        job_url=payload.job_url or (job.source_url if job else None),
        applied_at=payload.applied_at,
        current_stage=ApplicationStage.APPLICATION,
        process_status=ApplicationStatus.ACTIVE,
        note=payload.note,
        events=[
            ApplicationEvent(
                event_type=ApplicationStage.APPLICATION,
                occurred_at=payload.applied_at,
            )
        ],
    )
    session.add(application)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return application


async def list_applications(
    session: AsyncSession,
    user_id: UUID,
    process_status: ApplicationStatus | None = None,
) -> list[Application]:
    """List the current user's applications, optionally filtered by status."""

    statement = select(Application).where(Application.user_id == user_id)
    if process_status is not None:
        statement = statement.where(Application.process_status == process_status)
    return list(
        await session.scalars(statement.order_by(Application.updated_at.desc()))
    )


async def get_application(
    session: AsyncSession,
    user_id: UUID,
    application_id: UUID,
) -> Application:
    """Load one user-owned application and its timeline."""

    return await _load_application(
        session,
        user_id,
        application_id,
        with_events=True,
    )


async def update_application(
    session: AsyncSession,
    user_id: UUID,
    application_id: UUID,
    payload: ApplicationUpdate,
) -> Application:
    """Update editable metadata while keeping linked sources owner-scoped."""

    application = await _load_application(session, user_id, application_id)
    fields = payload.model_fields_set

    job: Job | None = None
    if "job_id" in fields and payload.job_id is not None:
        job = await _owned_job(session, user_id, payload.job_id)

    version: ResumeVersion | None = None
    if "resume_version_id" in fields and payload.resume_version_id is not None:
        version = await _owned_version(session, user_id, payload.resume_version_id)

    new_job_id = payload.job_id if "job_id" in fields else application.job_id
    new_version_id = (
        payload.resume_version_id
        if "resume_version_id" in fields
        else application.resume_version_id
    )
    if version is not None:
        if new_job_id is not None and version.job_id != new_job_id:
            raise ApplicationSourceMismatchError
        new_job_id = version.job_id
        if job is None:
            job = await _owned_job(session, user_id, version.job_id)
    elif new_version_id is not None:
        current_version = await _owned_version(session, user_id, new_version_id)
        if new_job_id is None:
            new_job_id = current_version.job_id
            job = await _owned_job(session, user_id, current_version.job_id)
        elif current_version.job_id != new_job_id:
            if "job_id" in fields:
                new_version_id = None
            else:
                raise ApplicationSourceMismatchError

    application.job_id = new_job_id
    application.resume_version_id = new_version_id

    if "company_name" in fields:
        if payload.company_name is None:
            raise ApplicationInvalidSnapshotError
        application.company_name = payload.company_name
    elif job is not None:
        application.company_name = job.company_name

    if "job_title" in fields:
        if payload.job_title is None:
            raise ApplicationInvalidSnapshotError
        application.job_title = payload.job_title
    elif job is not None:
        application.job_title = job.title

    if "job_url" in fields:
        application.job_url = payload.job_url
    elif job is not None:
        application.job_url = job.source_url
    if "applied_at" in fields:
        if payload.applied_at is None:
            raise ApplicationInvalidSnapshotError
        application.applied_at = payload.applied_at
    if "note" in fields:
        application.note = payload.note

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return await _load_application(
        session,
        user_id,
        application_id,
        with_events=True,
    )


async def delete_application(
    session: AsyncSession,
    user_id: UUID,
    application_id: UUID,
) -> None:
    """Delete one application and cascade its timeline."""

    application = await _load_application(session, user_id, application_id)
    await session.delete(application)
    await session.commit()


async def update_application_status(
    session: AsyncSession,
    user_id: UUID,
    application_id: UUID,
    payload: ApplicationStatusUpdate,
) -> Application:
    """Set process status and optionally record the current terminal stage."""

    application = await _load_application(session, user_id, application_id)
    application.process_status = payload.process_status
    if payload.current_stage is not None:
        application.current_stage = payload.current_stage
        application.current_round = payload.current_round
    await session.commit()
    return await _load_application(
        session,
        user_id,
        application_id,
        with_events=True,
    )


async def _load_event(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
) -> ApplicationEvent:
    event = await session.scalar(
        select(ApplicationEvent)
        .join(Application)
        .where(
            ApplicationEvent.id == event_id,
            Application.user_id == user_id,
        )
    )
    if event is None:
        raise ApplicationEventNotFoundError
    return event


async def _sync_current_stage(
    session: AsyncSession,
    application: Application,
) -> None:
    latest = await session.scalar(
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application.id)
        .order_by(
            ApplicationEvent.occurred_at.desc(),
            ApplicationEvent.created_at.desc(),
        )
        .limit(1)
    )
    if latest is None:
        application.current_stage = ApplicationStage.APPLICATION
        application.current_round = None
        return
    application.current_stage = latest.event_type
    application.current_round = latest.round_no


async def create_application_event(
    session: AsyncSession,
    user_id: UUID,
    application_id: UUID,
    payload: ApplicationEventCreate,
) -> ApplicationEvent:
    """Append an event and update the application's current stage atomically."""

    application = await _load_application(session, user_id, application_id)
    event = ApplicationEvent(
        application_id=application.id,
        **payload.model_dump(),
    )
    session.add(event)
    await session.flush()
    await _sync_current_stage(session, application)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return event


async def list_application_events(
    session: AsyncSession,
    user_id: UUID,
    application_id: UUID,
) -> list[ApplicationEvent]:
    """Return the owned timeline in chronological order."""

    await _load_application(session, user_id, application_id)
    return list(
        await session.scalars(
            select(ApplicationEvent)
            .where(ApplicationEvent.application_id == application_id)
            .order_by(
                ApplicationEvent.occurred_at,
                ApplicationEvent.created_at,
            )
        )
    )


async def update_application_event(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
    payload: ApplicationEventUpdate,
) -> ApplicationEvent:
    """Replace an owned event and recompute the current stage."""

    event = await _load_event(session, user_id, event_id)
    application = await _load_application(session, user_id, event.application_id)
    for field, value in payload.model_dump().items():
        setattr(event, field, value)
    await session.flush()
    await _sync_current_stage(session, application)
    await session.commit()
    return event


async def delete_application_event(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
) -> None:
    """Delete an owned event and recompute the current stage."""

    event = await _load_event(session, user_id, event_id)
    application = await _load_application(session, user_id, event.application_id)
    await session.delete(event)
    await session.flush()
    await _sync_current_stage(session, application)
    await session.commit()
