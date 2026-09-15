"""Authenticated Resume Tailor HTTP contract tests."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import (
    AIInputError,
    AIInvalidOutputError,
    AIProviderError,
    AITimeoutError,
)
from app.api.routes import jobs as job_routes
from app.database import get_db_session
from app.dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.services.job_detail import JobNotFoundError, MatchResultNotFoundError
from app.services.resume_tailor import (
    GeneratedResumeTailorDraft,
    ResumeTailorSourceInvalidError,
)
from tests.ai.test_context_builder import resume_data
from tests.test_resume_tailor import source_records, tailor_result


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def authenticated_user() -> User:
    return User(
        id=uuid4(),
        email="candidate@example.com",
        password_hash="$argon2id$private",
    )


def generated_draft() -> GeneratedResumeTailorDraft:
    job, match_result = source_records()
    return GeneratedResumeTailorDraft(
        job=job,
        match_result=match_result,
        source_resume=resume_data(),
        tailor_result=tailor_result(),
    )


@pytest.mark.anyio
async def test_resume_tailor_requires_authentication() -> None:
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)
    app.dependency_overrides[job_routes.get_resume_tailor_ai_client] = lambda: object()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(f"/api/v1/jobs/{uuid4()}/resume-tailor")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.anyio
async def test_resume_tailor_returns_reviewable_unpersisted_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    generated = generated_draft()
    generator = AsyncMock(return_value=generated)
    monkeypatch.setattr(job_routes, "generate_resume_tailor_draft", generator)
    session = AsyncMock(spec=AsyncSession)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[job_routes.get_resume_tailor_ai_client] = lambda: object()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(f"/api/v1/jobs/{generated.job.id}/resume-tailor")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["job_id"] == str(generated.job.id)
    assert data["match_result_id"] == str(generated.match_result.id)
    assert data["draft"]["skill_order"] == [str(resume_data().skills[0].id)]
    assert data["source_resume_snapshot"]["basic_info"]["name"] == "应被移除的姓名"
    assert data["prompt_version"] == "resume_tailor_v1"
    generator.assert_awaited_once()
    assert generator.await_args.args[0] is session
    assert generator.await_args.args[1] == user.id


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("service_error", "expected_status", "expected_code"),
    [
        (JobNotFoundError(), 404, "JOB_NOT_FOUND"),
        (MatchResultNotFoundError(), 409, "MATCH_RESULT_NOT_FOUND"),
        (AIInputError("bad snapshot"), 409, "AI_INVALID_INPUT"),
        (ResumeTailorSourceInvalidError(), 409, "AI_INVALID_INPUT"),
        (AITimeoutError("timeout"), 504, "AI_TIMEOUT"),
        (AIInvalidOutputError("fabricated"), 502, "AI_INVALID_OUTPUT"),
        (AIProviderError("provider"), 502, "AI_PROVIDER_ERROR"),
    ],
)
async def test_resume_tailor_maps_expected_errors(
    monkeypatch: pytest.MonkeyPatch,
    service_error: Exception,
    expected_status: int,
    expected_code: str,
) -> None:
    user = authenticated_user()
    generator = AsyncMock(side_effect=service_error)
    monkeypatch.setattr(job_routes, "generate_resume_tailor_draft", generator)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)
    app.dependency_overrides[job_routes.get_resume_tailor_ai_client] = lambda: object()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(f"/api/v1/jobs/{uuid4()}/resume-tailor")

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code
