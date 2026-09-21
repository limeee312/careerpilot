"""Core backend workflow against PostgreSQL with deterministic fake AI."""

import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from app.api.routes import job_match as job_match_routes
from app.api.routes import jobs as job_routes
from app.database import AsyncSessionFactory
from app.main import app
from app.models.application import Application, ApplicationEvent
from app.models.job import Job
from app.models.matching import JobMatchResult
from app.models.resume_version import ResumeVersion
from app.models.user import User
from tests.integration.test_match_analysis import StubAIClient
from tests.integration.test_resume_api import initial_resume

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1",
        reason="requires an isolated migrated PostgreSQL database",
    ),
]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_authenticated_core_flow_persists_ai_and_application_graph() -> None:
    """Exercise auth through timeline persistence without calling a real model."""

    email = f"backend-flow-{uuid4().hex}@example.com"
    password = f"BackendFlow-{uuid4().hex}"
    fake_ai = StubAIClient()
    app.dependency_overrides[job_match_routes.get_ai_client] = lambda: fake_ai
    app.dependency_overrides[job_routes.get_resume_tailor_ai_client] = lambda: fake_ai

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            register_response = await client.post(
                "/api/v1/auth/register",
                json={"email": email, "password": password},
            )
            assert register_response.status_code == 201
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert login_response.status_code == 200

            resume_payload = initial_resume()
            resume_payload["experiences"][0]["description"] = (
                "分析用户行为数据并推动运营优化"
            )
            resume_response = await client.put(
                "/api/v1/resume/master",
                json=resume_payload,
            )
            assert resume_response.status_code == 200

            batch_response = await client.post(
                "/api/v1/job-match/batches",
                json={
                    "name": "后端闭环测试",
                    "jobs": [
                        {
                            "company_name": "示例科技",
                            "title": "用户运营",
                            "raw_jd": (
                                "负责制定用户运营策略，分析用户行为数据并推动运营优化，"
                                "联动产品和研发团队推进项目落地并持续复盘迭代。"
                            ),
                        }
                    ],
                },
            )
            assert batch_response.status_code == 201
            batch = batch_response.json()["data"]
            job_id = batch["jobs"][0]["id"]

            analysis_response = await client.post(
                f"/api/v1/job-match/batches/{batch['id']}/analyze"
            )
            assert analysis_response.status_code == 200
            analyzed_job = analysis_response.json()["data"]["jobs"][0]
            assert analyzed_job["analysis_status"] == "COMPLETED"
            match_result_id = analyzed_job["result"]["id"]

            tailor_response = await client.post(f"/api/v1/jobs/{job_id}/resume-tailor")
            assert tailor_response.status_code == 200
            tailor = tailor_response.json()["data"]
            assert tailor["match_result_id"] == match_result_id

            version_response = await client.post(
                "/api/v1/resume/versions",
                json={
                    "match_result_id": match_result_id,
                    "draft": tailor["draft"],
                    "prompt_version": tailor["prompt_version"],
                    "model": tailor["model"],
                },
            )
            assert version_response.status_code == 201
            saved_version = version_response.json()["data"]
            version_id = saved_version["id"]
            saved_skills = saved_version["content"]["skills"]
            assert [skill["skill_name"] for skill in saved_skills] == ["Python", "Excel"]

            application_response = await client.post(
                "/api/v1/applications",
                json={
                    "job_id": job_id,
                    "resume_version_id": version_id,
                    "applied_at": "2026-09-19",
                },
            )
            assert application_response.status_code == 201
            application_id = application_response.json()["data"]["id"]

            event_response = await client.post(
                f"/api/v1/applications/{application_id}/events",
                json={
                    "event_type": "INTERVIEW",
                    "round_no": 1,
                    "occurred_at": "2026-09-22",
                    "outcome": "PENDING",
                },
            )
            assert event_response.status_code == 201

            detail_response = await client.get(f"/api/v1/applications/{application_id}")
            assert detail_response.status_code == 200
            detail = detail_response.json()["data"]
            assert detail["job_id"] == job_id
            assert detail["resume_version_id"] == version_id
            assert detail["current_stage"] == "INTERVIEW"
            assert [event["event_type"] for event in detail["events"]] == [
                "APPLICATION",
                "INTERVIEW",
            ]

        assert fake_ai.calls == 3
        async with AsyncSessionFactory() as session:
            user_id = await session.scalar(select(User.id).where(User.email == email))
            assert user_id is not None
            assert (
                await session.scalar(
                    select(func.count()).select_from(Job).where(Job.user_id == user_id)
                )
                == 1
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(JobMatchResult)
                    .where(JobMatchResult.user_id == user_id)
                )
                == 1
            )
            version = await session.scalar(
                select(ResumeVersion).where(ResumeVersion.id == version_id)
            )
            assert version is not None
            assert str(version.match_result_id) == match_result_id
            application = await session.scalar(
                select(Application).where(Application.id == application_id)
            )
            assert application is not None
            assert application.user_id == user_id
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(ApplicationEvent)
                    .where(ApplicationEvent.application_id == application_id)
                )
                == 2
            )
    finally:
        app.dependency_overrides.clear()
        async with AsyncSessionFactory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()
