"""Authenticated job match detail HTTP contract tests."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import jobs as job_routes
from app.database import get_db_session
from app.dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.services.job_detail import JobNotFoundError, MatchResultNotFoundError


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


@pytest.mark.anyio
async def test_job_detail_requires_authentication() -> None:
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(f"/api/v1/jobs/{uuid4()}")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("service_error", "expected_status", "expected_code"),
    [
        (JobNotFoundError(), 404, "JOB_NOT_FOUND"),
        (MatchResultNotFoundError(), 409, "MATCH_RESULT_NOT_FOUND"),
    ],
)
@pytest.mark.parametrize(
    "path_template",
    ["/api/v1/jobs/{job_id}", "/api/v1/jobs/{job_id}/match"],
)
async def test_job_detail_maps_owner_and_result_errors(
    monkeypatch: pytest.MonkeyPatch,
    service_error: Exception,
    expected_status: int,
    expected_code: str,
    path_template: str,
) -> None:
    user = authenticated_user()
    reader = AsyncMock(side_effect=service_error)
    monkeypatch.setattr(job_routes, "get_job_match_detail", reader)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(path_template.format(job_id=uuid4()))

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code
    reader.assert_awaited_once()
