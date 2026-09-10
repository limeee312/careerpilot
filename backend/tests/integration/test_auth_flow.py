"""Authentication flow against the CI PostgreSQL service."""

import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.database import AsyncSessionFactory
from app.main import app
from app.models.user import User

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


async def test_register_login_me_logout_round_trip() -> None:
    email = f"integration-{uuid4().hex}@example.com"
    password = "correct horse battery staple"

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
            assert login_response.json()["data"]["email"] == email

            me_response = await client.get("/api/v1/auth/me")
            assert me_response.status_code == 200
            assert (
                me_response.json()["data"]["id"]
                == register_response.json()["data"]["id"]
            )

            logout_response = await client.post("/api/v1/auth/logout")
            assert logout_response.status_code == 204

            signed_out_response = await client.get("/api/v1/auth/me")
            assert signed_out_response.status_code == 401
            assert signed_out_response.json()["error"]["code"] == "AUTH_REQUIRED"
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()
