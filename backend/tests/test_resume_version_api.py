"""Authenticated Resume Version HTTP contract tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import resume as resume_routes
from app.database import get_db_session
from app.dependencies import get_current_user
from app.main import app
from app.models.resume_version import ResumeVersion, ResumeVersionStatus
from app.models.user import User
from app.services.resume_version import (
    ResumeVersionInvalidDraftError,
    ResumeVersionNotFoundError,
    ResumeVersionSourceNotFoundError,
)
from tests.test_resume_tailor import tailor_result
from tests.test_resume_version import source_match_result


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


def saved_version(user_id) -> ResumeVersion:
    job, result = source_match_result()
    now = datetime(2026, 9, 15, tzinfo=UTC)
    return ResumeVersion(
        id=uuid4(),
        user_id=user_id,
        resume_master_id=result.resume_master_id,
        job_id=job.id,
        match_result_id=result.id,
        name="目标公司 - 产品运营",
        status=ResumeVersionStatus.SAVED,
        content={
            "summary": "具备数据分析与流程优化经验。",
            "education": [],
            "experiences": [],
            "projects": [],
            "skills": [],
        },
        source_resume_snapshot=result.resume_snapshot,
        source_job_snapshot=result.job_snapshot,
        prompt_version="resume_tailor_v1",
        model="tailor-model",
        created_at=now,
        updated_at=now,
    )


def payload(match_result_id) -> dict[str, object]:
    return {
        "match_result_id": str(match_result_id),
        "draft": tailor_result().output.model_dump(mode="json"),
        "prompt_version": "resume_tailor_v1",
        "model": "tailor-model",
    }


@pytest.mark.anyio
async def test_save_endpoint_requires_authentication() -> None:
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/resume/versions",
            json=payload(uuid4()),
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.anyio
async def test_save_endpoint_persists_only_after_explicit_post(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    session = AsyncMock(spec=AsyncSession)
    version = saved_version(user.id)
    saver = AsyncMock(return_value=version)
    monkeypatch.setattr(resume_routes, "create_resume_version", saver)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/resume/versions",
            json=payload(version.match_result_id),
        )

    assert response.status_code == 201
    assert response.json()["data"]["id"] == str(version.id)
    assert response.json()["data"]["status"] == "SAVED"
    assert response.json()["data"]["company_name"] == "目标公司"
    saver.assert_awaited_once()
    assert saver.await_args.args[0] is session
    assert saver.await_args.args[1] == user.id


@pytest.mark.anyio
async def test_save_endpoint_hides_unowned_match_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    monkeypatch.setattr(
        resume_routes,
        "create_resume_version",
        AsyncMock(side_effect=ResumeVersionSourceNotFoundError),
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/resume/versions",
            json=payload(uuid4()),
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESUME_VERSION_SOURCE_NOT_FOUND"


@pytest.mark.anyio
async def test_list_endpoint_returns_only_service_scoped_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    version = saved_version(user.id)
    loader = AsyncMock(return_value=[version])
    monkeypatch.setattr(resume_routes, "list_resume_versions", loader)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/resume/versions")

    assert response.status_code == 200
    assert response.json()["data"][0]["name"] == "目标公司 - 产品运营"
    loader.assert_awaited_once()
    assert loader.await_args.args[1] == user.id


@pytest.mark.anyio
async def test_detail_endpoint_returns_owned_saved_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    version = saved_version(user.id)
    loader = AsyncMock(return_value=version)
    monkeypatch.setattr(resume_routes, "get_resume_version", loader)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(f"/api/v1/resume/versions/{version.id}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(version.id)
    assert response.json()["data"]["content"]["summary"]
    loader.assert_awaited_once()
    assert loader.await_args.args[1] == user.id


@pytest.mark.anyio
async def test_detail_endpoint_hides_missing_or_foreign_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    monkeypatch.setattr(
        resume_routes,
        "get_resume_version",
        AsyncMock(side_effect=ResumeVersionNotFoundError),
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(f"/api/v1/resume/versions/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESUME_VERSION_NOT_FOUND"


@pytest.mark.anyio
async def test_detail_endpoint_maps_invalid_persisted_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    monkeypatch.setattr(
        resume_routes,
        "get_resume_version",
        AsyncMock(side_effect=ResumeVersionInvalidDraftError),
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(f"/api/v1/resume/versions/{uuid4()}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESUME_VERSION_INVALID_DATA"
