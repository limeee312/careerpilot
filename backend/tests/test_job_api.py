"""Manual job batch HTTP endpoint contract tests without a database."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import job_match as job_match_routes
from app.database import get_db_session
from app.dependencies import get_current_user
from app.main import app
from app.models.job import BatchStatus, Job, JobMatchBatch
from app.models.user import User
from app.schemas.job import JobBatchCreate
from app.services.job import create_job_batch

LONG_JD = (
    "负责产品用户运营策略制定与执行，通过用户行为数据分析发现问题，"
    "并联动产品、研发和市场团队推进运营项目落地。"
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def valid_payload() -> dict[str, object]:
    return {
        "name": "秋招重点岗位",
        "jobs": [
            {
                "company_name": "示例科技",
                "title": "产品运营",
                "raw_jd": LONG_JD,
            }
        ],
    }


def authenticated_user() -> User:
    return User(
        id=uuid4(),
        email="candidate@example.com",
        password_hash="$argon2id$private",
    )


@pytest.mark.anyio
async def test_create_job_batch_uses_authenticated_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    session = AsyncMock(spec=AsyncSession)
    now = datetime.now(UTC)
    batch = JobMatchBatch(
        id=uuid4(),
        user_id=user.id,
        name="秋招重点岗位",
        status=BatchStatus.DRAFT,
        total_jobs=1,
        successful_jobs=0,
        failed_jobs=0,
        created_at=now,
        updated_at=now,
        jobs=[
            Job(
                id=uuid4(),
                user_id=user.id,
                company_name="示例科技",
                title="产品运营",
                raw_jd=LONG_JD,
                created_at=now,
                updated_at=now,
            )
        ],
    )
    creator = AsyncMock(return_value=batch)
    monkeypatch.setattr(job_match_routes, "create_job_batch", creator)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/job-match/batches",
            json=valid_payload(),
        )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "DRAFT"
    assert data["total_jobs"] == 1
    assert data["successful_jobs"] == 0
    assert data["jobs"][0]["company_name"] == "示例科技"
    creator.assert_awaited_once()
    assert creator.await_args.args[0] is session
    assert creator.await_args.args[1] == user.id
    assert creator.await_args.args[2].jobs[0].title == "产品运营"


@pytest.mark.anyio
async def test_create_job_batch_requires_authentication() -> None:
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/job-match/batches",
            json=valid_payload(),
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.anyio
async def test_create_job_batch_returns_standard_validation_error() -> None:
    user = authenticated_user()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)
    payload = valid_payload()
    payload["jobs"][0]["raw_jd"] = "太短"  # type: ignore[index]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/job-match/batches",
            json=payload,
        )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "请求参数校验失败",
        }
    }


@pytest.mark.anyio
async def test_create_job_batch_rolls_back_the_whole_batch_on_failure() -> None:
    user = authenticated_user()
    session = AsyncMock(spec=AsyncSession)
    session.commit.side_effect = RuntimeError("database unavailable")
    payload = JobBatchCreate.model_validate(valid_payload())

    with pytest.raises(RuntimeError, match="database unavailable"):
        await create_job_batch(session, user.id, payload)

    session.add.assert_called_once()
    pending_batch = session.add.call_args.args[0]
    assert pending_batch.user_id == user.id
    assert pending_batch.total_jobs == 1
    assert len(pending_batch.jobs) == 1
    session.rollback.assert_awaited_once_with()
