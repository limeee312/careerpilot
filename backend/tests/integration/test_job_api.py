"""Manual job batch API persistence tests against CI PostgreSQL."""

import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from app.database import AsyncSessionFactory
from app.main import app
from app.models.job import BatchStatus, Job, JobMatchBatch
from app.models.user import User

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1",
        reason="requires an isolated migrated PostgreSQL database",
    ),
]

PASSWORD = "correct horse battery staple"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def job_payload(company: str, title: str) -> dict[str, object]:
    return {
        "company_name": company,
        "title": title,
        "location": "杭州",
        "department": "用户增长",
        "source_url": "https://example.com/jobs/123",
        "raw_jd": (
            f"负责{title}策略制定与执行，通过用户行为数据分析发现问题，"
            f"并联动产品、研发和市场团队推进{company}的运营项目落地。"
        ),
    }


async def register_and_login(client: AsyncClient, email: str) -> None:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert register_response.status_code == 201
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login_response.status_code == 200


async def test_create_job_batch_persists_all_jobs_for_current_user() -> None:
    email = f"job-api-{uuid4().hex}@example.com"

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await register_and_login(client, email)
            response = await client.post(
                "/api/v1/job-match/batches",
                json={
                    "name": "  秋招重点岗位  ",
                    "jobs": [
                        job_payload("示例甲", "产品运营"),
                        job_payload("示例乙", "用户运营"),
                    ],
                },
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == "秋招重点岗位"
        assert data["status"] == "DRAFT"
        assert data["total_jobs"] == 2
        assert data["successful_jobs"] == 0
        assert data["failed_jobs"] == 0
        assert [job["company_name"] for job in data["jobs"]] == [
            "示例甲",
            "示例乙",
        ]

        async with AsyncSessionFactory() as session:
            user_id = await session.scalar(select(User.id).where(User.email == email))
            batch = await session.scalar(
                select(JobMatchBatch).where(JobMatchBatch.id == data["id"])
            )
            assert batch is not None
            assert batch.user_id == user_id
            assert batch.status is BatchStatus.DRAFT
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(Job)
                    .where(Job.batch_id == batch.id, Job.user_id == user_id)
                )
                == 2
            )
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()


@pytest.mark.parametrize(
    "jobs",
    [
        [{**job_payload("示例甲", "产品运营"), "raw_jd": "太短"}],
        [job_payload(f"示例{index}", "产品运营") for index in range(6)],
    ],
)
async def test_invalid_job_batch_creates_nothing(jobs: list[dict]) -> None:
    email = f"job-api-invalid-{uuid4().hex}@example.com"

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await register_and_login(client, email)
            response = await client.post(
                "/api/v1/job-match/batches",
                json={"jobs": jobs},
            )

        assert response.status_code == 422
        async with AsyncSessionFactory() as session:
            user_id = await session.scalar(select(User.id).where(User.email == email))
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(JobMatchBatch)
                    .where(JobMatchBatch.user_id == user_id)
                )
                == 0
            )
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()
