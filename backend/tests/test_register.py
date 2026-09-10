"""Registration endpoint and service tests."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import auth as auth_routes
from app.database import get_db_session
from app.main import app
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.security import verify_password
from app.services.auth import EmailAlreadyRegisteredError, register_user


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_register_request_normalizes_email() -> None:
    registration = RegisterRequest(
        email="  Candidate.Name@Example.COM  ",
        password="long enough password",
    )

    assert registration.email == "candidate.name@example.com"


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("not-an-email", "long enough password"),
        ("candidate@example.com", "too short"),
    ],
)
def test_register_request_rejects_invalid_input(email: str, password: str) -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(email=email, password=password)


@pytest.mark.anyio
async def test_register_user_hashes_password_before_persistence() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    registration = RegisterRequest(
        email="candidate@example.com",
        password="a secure passphrase",
    )

    user = await register_user(session, registration)

    assert user.password_hash != registration.password
    assert user.password_hash.startswith("$argon2id$")
    assert verify_password(registration.password, user.password_hash)
    session.add.assert_called_once_with(user)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(user)


@pytest.mark.anyio
async def test_register_user_rejects_known_email_without_hashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = uuid4()
    hasher = AsyncMock()
    monkeypatch.setattr("app.services.auth.hash_password", hasher)
    registration = RegisterRequest(
        email="candidate@example.com",
        password="a secure passphrase",
    )

    with pytest.raises(EmailAlreadyRegisteredError):
        await register_user(session, registration)

    hasher.assert_not_called()
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_register_user_maps_concurrent_duplicate_to_domain_error() -> None:
    class DuplicateEmailDiagnostic:
        constraint_name = "users_email_idx"

    class DuplicateEmailDatabaseError(Exception):
        diag = DuplicateEmailDiagnostic()

    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    session.commit.side_effect = IntegrityError(
        "duplicate email",
        params={},
        orig=DuplicateEmailDatabaseError(),
    )
    registration = RegisterRequest(
        email="candidate@example.com",
        password="a secure passphrase",
    )

    with pytest.raises(EmailAlreadyRegisteredError):
        await register_user(session, registration)

    session.rollback.assert_awaited_once()
    session.refresh.assert_not_awaited()


@pytest.mark.anyio
async def test_register_endpoint_returns_public_user_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(
        id=uuid4(),
        email="candidate@example.com",
        password_hash="$argon2id$private",
    )
    register_mock = AsyncMock(return_value=user)
    monkeypatch.setattr(auth_routes, "register_user", register_mock)

    async def override_session() -> AsyncSession:
        return AsyncMock(spec=AsyncSession)

    app.dependency_overrides[get_db_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": " Candidate@Example.COM ",
                "password": "a secure passphrase",
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "data": {
            "id": str(user.id),
            "email": "candidate@example.com",
        }
    }
    assert "password" not in response.text


@pytest.mark.anyio
async def test_register_endpoint_returns_conflict_for_duplicate_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_mock = AsyncMock(side_effect=EmailAlreadyRegisteredError)
    monkeypatch.setattr(auth_routes, "register_user", register_mock)

    async def override_session() -> AsyncSession:
        return AsyncMock(spec=AsyncSession)

    app.dependency_overrides[get_db_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "candidate@example.com",
                "password": "a secure passphrase",
            },
        )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "AUTH_EMAIL_EXISTS",
            "message": "该邮箱已注册",
        }
    }


@pytest.mark.anyio
async def test_register_endpoint_uses_standard_validation_error() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "short",
            },
        )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "请求参数校验失败",
        }
    }
