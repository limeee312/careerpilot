"""Dashboard aggregation against migrated PostgreSQL."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.database import AsyncSessionFactory
from app.main import app
from app.models.application import Application, ApplicationStatus
from app.models.user import User

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1",
        reason="requires an isolated migrated PostgreSQL database",
    ),
]

PASSWORD = f"dashboard-test-{uuid4().hex}"


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


async def test_dashboard_counts_are_user_scoped_and_recent_is_limited() -> None:
    owner_email = f"dashboard-owner-{uuid4().hex}@example.com"
    other_email = f"dashboard-other-{uuid4().hex}@example.com"
    now = datetime(2026, 9, 19, 8, tzinfo=UTC)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as owner_client:
            await register_and_login(owner_client, owner_email)

            async with AsyncSessionFactory() as session:
                owner_id = await session.scalar(
                    select(User.id).where(User.email == owner_email)
                )
                assert owner_id is not None
                statuses = [
                    ApplicationStatus.ACTIVE,
                    ApplicationStatus.ACTIVE,
                    ApplicationStatus.REJECTED,
                    ApplicationStatus.OFFER,
                    ApplicationStatus.WITHDRAWN,
                    ApplicationStatus.ACTIVE,
                ]
                session.add_all(
                    [
                        Application(
                            user_id=owner_id,
                            company_name=f"公司 {index}",
                            job_title="产品运营",
                            applied_at=now - timedelta(days=index),
                            process_status=process_status,
                        )
                        for index, process_status in enumerate(statuses)
                    ]
                )
                await session.commit()

            response = await owner_client.get("/api/v1/dashboard")

            assert response.status_code == 200
            dashboard = response.json()["data"]
            assert dashboard["overview"] == {
                "total": 6,
                "active": 3,
                "rejected": 1,
                "offer": 1,
                "withdrawn": 1,
            }
            assert len(dashboard["recent_applications"]) == 5
            assert [
                item["company_name"] for item in dashboard["recent_applications"]
            ] == [f"公司 {index}" for index in range(5)]

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as other_client:
            await register_and_login(other_client, other_email)
            response = await other_client.get("/api/v1/dashboard")

            assert response.status_code == 200
            assert response.json()["data"]["overview"]["total"] == 0
            assert response.json()["data"]["recent_applications"] == []
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(
                delete(User).where(User.email.in_([owner_email, other_email]))
            )
            await session.commit()
