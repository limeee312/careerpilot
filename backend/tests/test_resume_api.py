"""Resume HTTP endpoint contract tests without a database."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import resume as resume_routes
from app.database import get_db_session
from app.dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.services.resume import (
    DuplicateResumeSkillError,
    ResumeSaveConflictError,
    ResumeSectionNotFoundError,
)


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


def override_dependencies(user: User) -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: session
    return session


@pytest.mark.anyio
async def test_get_resume_master_returns_null_when_not_created(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    session = override_dependencies(user)
    loader = AsyncMock(return_value=None)
    monkeypatch.setattr(resume_routes, "get_resume_master", loader)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/resume/master")

    assert response.status_code == 200
    assert response.json() == {"data": None}
    loader.assert_awaited_once_with(session, user.id)


@pytest.mark.anyio
async def test_put_resume_rejects_section_not_owned_by_current_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    override_dependencies(user)
    saver = AsyncMock(side_effect=ResumeSectionNotFoundError)
    monkeypatch.setattr(resume_routes, "upsert_resume_master", saver)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.put("/api/v1/resume/master", json={})

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "RESUME_SECTION_NOT_FOUND",
            "message": "简历条目不存在",
        }
    }


@pytest.mark.anyio
async def test_resume_endpoint_requires_authentication() -> None:
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/resume/master")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("service_error", "expected_code"),
    [
        (DuplicateResumeSkillError(), "RESUME_DUPLICATE_SKILL"),
        (ResumeSaveConflictError(), "RESUME_SAVE_CONFLICT"),
    ],
)
async def test_put_resume_maps_save_conflicts(
    monkeypatch: pytest.MonkeyPatch,
    service_error: Exception,
    expected_code: str,
) -> None:
    user = authenticated_user()
    override_dependencies(user)
    monkeypatch.setattr(
        resume_routes,
        "upsert_resume_master",
        AsyncMock(side_effect=service_error),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.put("/api/v1/resume/master", json={})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == expected_code
