"""Cookie-based JWT session tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import auth as auth_routes
from app.config import DEVELOPMENT_JWT_SECRET, Settings
from app.database import get_db_session
from app.dependencies import AUTH_COOKIE_NAME, get_current_user
from app.errors import APIError
from app.main import app
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.security import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
)
from app.services.auth import (
    DUMMY_PASSWORD_HASH,
    InvalidCredentialsError,
    authenticate_user,
)

TEST_JWT_SECRET = "test-secret-that-is-longer-than-32-characters"


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "test",
        "jwt_secret": TEST_JWT_SECRET,
        "jwt_expire_minutes": 60,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_access_token_round_trip() -> None:
    user_id = uuid4()
    issued_at = datetime.now(UTC)
    settings = make_settings()

    token = create_access_token(user_id, settings=settings, now=issued_at)

    assert decode_access_token(token, settings=settings) == user_id
    payload = jwt.decode(
        token,
        TEST_JWT_SECRET,
        algorithms=["HS256"],
    )
    assert payload["sub"] == str(user_id)
    assert payload["exp"] - payload["iat"] == 60 * 60


def test_access_token_rejects_expired_or_wrongly_signed_tokens() -> None:
    expired = create_access_token(
        uuid4(),
        settings=make_settings(),
        now=datetime.now(UTC) - timedelta(minutes=61),
    )
    valid = create_access_token(uuid4(), settings=make_settings())

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(expired, settings=make_settings())
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(
            valid,
            settings=make_settings(
                jwt_secret="different-secret-with-at-least-32-characters"
            ),
        )


def test_deployed_environment_requires_non_default_secret() -> None:
    with pytest.raises(ValidationError):
        make_settings(app_env="production", jwt_secret=DEVELOPMENT_JWT_SECRET)
    with pytest.raises(ValidationError):
        make_settings(app_env="production", jwt_secret="too-short")

    production = make_settings(
        app_env="production",
        jwt_secret="production-secret-with-at-least-32-characters",
    )
    assert production.secure_cookies


@pytest.mark.anyio
async def test_authenticate_user_accepts_valid_credentials() -> None:
    from app.security import hash_password

    user = User(
        id=uuid4(),
        email="candidate@example.com",
        password_hash=hash_password("a secure passphrase"),
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = user

    authenticated = await authenticate_user(
        session,
        LoginRequest(
            email="candidate@example.com",
            password="a secure passphrase",
        ),
    )

    assert authenticated is user


@pytest.mark.anyio
async def test_authenticate_user_uses_dummy_hash_for_unknown_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    verifier = Mock(return_value=False)
    monkeypatch.setattr("app.services.auth.verify_password", verifier)
    credentials = LoginRequest(
        email="missing@example.com",
        password="a secure passphrase",
    )

    with pytest.raises(InvalidCredentialsError):
        await authenticate_user(session, credentials)

    verifier.assert_called_once_with(credentials.password, DUMMY_PASSWORD_HASH)


@pytest.mark.anyio
async def test_current_user_is_loaded_from_token_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(
        id=uuid4(),
        email="candidate@example.com",
        password_hash="$argon2id$private",
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = user
    decoder = Mock(return_value=user.id)
    monkeypatch.setattr("app.dependencies.decode_access_token", decoder)

    current_user = await get_current_user(session, "signed-token")

    assert current_user is user
    decoder.assert_called_once_with("signed-token")
    statement = session.scalar.await_args.args[0]
    assert str(statement.whereclause) == "users.id = :id_1"


@pytest.mark.anyio
async def test_invalid_session_token_does_not_query_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock(spec=AsyncSession)
    decoder = Mock(side_effect=InvalidAccessTokenError)
    monkeypatch.setattr("app.dependencies.decode_access_token", decoder)

    with pytest.raises(APIError) as error_info:
        await get_current_user(session, "invalid-token")

    assert getattr(error_info.value, "code", None) == "AUTH_REQUIRED"
    session.scalar.assert_not_awaited()


@pytest.mark.anyio
async def test_login_sets_httponly_session_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(
        id=uuid4(),
        email="candidate@example.com",
        password_hash="$argon2id$private",
        name="Candidate",
    )
    monkeypatch.setattr(
        auth_routes,
        "authenticate_user",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr(auth_routes, "create_access_token", Mock(return_value="token"))

    async def override_session() -> AsyncSession:
        return AsyncMock(spec=AsyncSession)

    app.dependency_overrides[get_db_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "candidate@example.com",
                "password": "a secure passphrase",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
        }
    }
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{AUTH_COOKIE_NAME}=token;")
    assert "HttpOnly" in cookie
    assert "Max-Age=3600" in cookie
    assert "Path=/" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" not in cookie


@pytest.mark.anyio
async def test_login_uses_generic_invalid_credentials_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_routes,
        "authenticate_user",
        AsyncMock(side_effect=InvalidCredentialsError),
    )

    async def override_session() -> AsyncSession:
        return AsyncMock(spec=AsyncSession)

    app.dependency_overrides[get_db_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "candidate@example.com",
                "password": "a secure passphrase",
            },
        )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "AUTH_INVALID_CREDENTIALS",
            "message": "邮箱或密码错误",
        }
    }


@pytest.mark.anyio
async def test_logout_clears_session_cookie() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f'{AUTH_COOKIE_NAME}="";')
    assert "Max-Age=0" in cookie
    assert "HttpOnly" in cookie


@pytest.mark.anyio
async def test_me_returns_current_user() -> None:
    user = User(
        id=uuid4(),
        email="candidate@example.com",
        password_hash="$argon2id$private",
        name=None,
    )
    app.dependency_overrides[get_current_user] = lambda: user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "id": str(user.id),
            "email": user.email,
            "name": None,
        }
    }


@pytest.mark.anyio
async def test_me_requires_session_cookie() -> None:
    async def override_session() -> AsyncSession:
        return AsyncMock(spec=AsyncSession)

    app.dependency_overrides[get_db_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "AUTH_REQUIRED",
            "message": "请先登录",
        }
    }
