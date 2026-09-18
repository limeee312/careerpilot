"""Application service ownership and atomic-create tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import ApplicationStage, ApplicationStatus
from app.models.job import Job
from app.models.resume_version import ResumeVersion, ResumeVersionStatus
from app.schemas.application import ApplicationCreate
from app.services.application import (
    ApplicationNotFoundError,
    ApplicationSourceMismatchError,
    create_application,
    get_application,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_create_is_atomic_with_initial_application_event() -> None:
    session = AsyncMock(spec=AsyncSession)
    user_id = uuid4()
    applied_at = datetime(2026, 9, 18, tzinfo=UTC)

    application = await create_application(
        session,
        user_id,
        ApplicationCreate(
            company_name="示例科技",
            job_title="产品运营",
            applied_at=applied_at,
        ),
    )

    session.add.assert_called_once_with(application)
    session.commit.assert_awaited_once()
    assert application.user_id == user_id
    assert application.current_stage is ApplicationStage.APPLICATION
    assert application.process_status is ApplicationStatus.ACTIVE
    assert len(application.events) == 1
    assert application.events[0].event_type is ApplicationStage.APPLICATION
    assert application.events[0].occurred_at == applied_at


@pytest.mark.anyio
async def test_create_rolls_back_application_and_event_together() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.commit.side_effect = RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        await create_application(
            session,
            uuid4(),
            ApplicationCreate(
                company_name="示例科技",
                job_title="产品运营",
                applied_at="2026-09-18",
            ),
        )

    session.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_cross_user_application_is_reported_as_not_found() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None

    with pytest.raises(ApplicationNotFoundError):
        await get_application(session, uuid4(), uuid4())


@pytest.mark.anyio
async def test_linked_sources_are_owner_scoped_and_fill_snapshot() -> None:
    session = AsyncMock(spec=AsyncSession)
    user_id = uuid4()
    job_id = uuid4()
    job = Job(
        id=job_id,
        user_id=user_id,
        batch_id=uuid4(),
        company_name="来源公司",
        title="来源岗位",
        source_url="https://example.com/jobs/source",
        raw_jd="测试职位描述",
    )
    version = ResumeVersion(
        id=uuid4(),
        user_id=user_id,
        job_id=job_id,
        status=ResumeVersionStatus.SAVED,
    )
    session.scalar.side_effect = [job, version]

    application = await create_application(
        session,
        user_id,
        ApplicationCreate(
            job_id=job_id,
            resume_version_id=version.id,
            applied_at="2026-09-18",
        ),
    )

    assert application.company_name == "来源公司"
    assert application.job_title == "来源岗位"
    assert application.job_url == "https://example.com/jobs/source"
    assert application.resume_version_id == version.id


@pytest.mark.anyio
async def test_mismatched_job_and_resume_version_are_rejected() -> None:
    session = AsyncMock(spec=AsyncSession)
    user_id = uuid4()
    job = Job(
        id=uuid4(),
        user_id=user_id,
        batch_id=uuid4(),
        company_name="来源公司",
        title="来源岗位",
        raw_jd="测试职位描述",
    )
    version = ResumeVersion(
        id=uuid4(),
        user_id=user_id,
        job_id=uuid4(),
        status=ResumeVersionStatus.SAVED,
    )
    session.scalar.side_effect = [job, version]

    with pytest.raises(ApplicationSourceMismatchError):
        await create_application(
            session,
            user_id,
            ApplicationCreate(
                job_id=job.id,
                resume_version_id=version.id,
                applied_at="2026-09-18",
            ),
        )

    session.add.assert_not_called()
