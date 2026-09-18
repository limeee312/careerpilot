"""End-to-end application workflow against migrated PostgreSQL."""

import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from app.database import AsyncSessionFactory
from app.main import app
from app.models.application import Application, ApplicationEvent
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


async def test_full_application_timeline_status_and_permissions() -> None:
    owner_email = f"application-owner-{uuid4().hex}@example.com"
    other_email = f"application-other-{uuid4().hex}@example.com"

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as owner_client:
            await register_and_login(owner_client, owner_email)
            create_response = await owner_client.post(
                "/api/v1/applications",
                json={
                    "company_name": "示例科技",
                    "job_title": "产品运营",
                    "job_url": "https://example.com/jobs/product-ops",
                    "applied_at": "2026-09-18",
                    "note": "官网投递",
                },
            )
            assert create_response.status_code == 201
            application = create_response.json()["data"]
            application_id = application["id"]
            assert application["current_stage"] == "APPLICATION"
            assert application["process_status"] == "ACTIVE"
            assert [event["event_type"] for event in application["events"]] == [
                "APPLICATION"
            ]

            assessment_response = await owner_client.post(
                f"/api/v1/applications/{application_id}/events",
                json={
                    "event_type": "ASSESSMENT",
                    "occurred_at": "2026-09-20T09:00:00+08:00",
                    "outcome": "PENDING",
                },
            )
            assert assessment_response.status_code == 201
            assessment_id = assessment_response.json()["data"]["id"]

            update_event_response = await owner_client.put(
                f"/api/v1/application-events/{assessment_id}",
                json={
                    "event_type": "ASSESSMENT",
                    "occurred_at": "2026-09-20T09:00:00+08:00",
                    "outcome": "PASSED",
                    "note": "在线测评通过",
                },
            )
            assert update_event_response.status_code == 200
            assert update_event_response.json()["data"]["outcome"] == "PASSED"

            interview_response = await owner_client.post(
                f"/api/v1/applications/{application_id}/events",
                json={
                    "event_type": "INTERVIEW",
                    "round_no": 1,
                    "occurred_at": "2026-09-22T14:00:00+08:00",
                    "outcome": "FAILED",
                    "note": "一面结束",
                },
            )
            assert interview_response.status_code == 201

            status_response = await owner_client.put(
                f"/api/v1/applications/{application_id}/status",
                json={
                    "process_status": "REJECTED",
                    "current_stage": "INTERVIEW",
                    "current_round": 1,
                },
            )
            assert status_response.status_code == 200
            assert status_response.json()["data"]["process_status"] == "REJECTED"

            timeline_response = await owner_client.get(
                f"/api/v1/applications/{application_id}/events"
            )
            assert timeline_response.status_code == 200
            timeline = timeline_response.json()["data"]
            assert [event["event_type"] for event in timeline] == [
                "APPLICATION",
                "ASSESSMENT",
                "INTERVIEW",
            ]

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as other_client:
            await register_and_login(other_client, other_email)
            hidden_response = await other_client.get(
                f"/api/v1/applications/{application_id}"
            )
            assert hidden_response.status_code == 404
            assert hidden_response.json()["error"]["code"] == ("APPLICATION_NOT_FOUND")

        async with AsyncSessionFactory() as session:
            owner_id = await session.scalar(
                select(User.id).where(User.email == owner_email)
            )
            saved = await session.scalar(
                select(Application).where(Application.id == application_id)
            )
            assert saved is not None
            assert saved.user_id == owner_id
            assert saved.current_stage.value == "INTERVIEW"
            assert saved.current_round == 1
            assert saved.process_status.value == "REJECTED"
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(ApplicationEvent)
                    .where(ApplicationEvent.application_id == application_id)
                )
                == 3
            )
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(
                delete(User).where(User.email.in_([owner_email, other_email]))
            )
            await session.commit()
