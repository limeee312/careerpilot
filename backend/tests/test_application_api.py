"""Authenticated Application HTTP contract tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import applications as application_routes
from app.database import get_db_session
from app.dependencies import get_current_user
from app.main import app
from app.models.application import (
    Application,
    ApplicationEvent,
    ApplicationStage,
    ApplicationStatus,
)
from app.models.user import User
from app.services.application import (
    ApplicationEventNotFoundError,
    ApplicationNotFoundError,
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


def application_record(user_id) -> Application:
    now = datetime(2026, 9, 18, tzinfo=UTC)
    application_id = uuid4()
    return Application(
        id=application_id,
        user_id=user_id,
        company_name="示例科技",
        job_title="产品运营",
        applied_at=now,
        current_stage=ApplicationStage.APPLICATION,
        process_status=ApplicationStatus.ACTIVE,
        created_at=now,
        updated_at=now,
        events=[
            ApplicationEvent(
                id=uuid4(),
                application_id=application_id,
                event_type=ApplicationStage.APPLICATION,
                occurred_at=now,
                created_at=now,
                updated_at=now,
            )
        ],
    )


def event_record(application_id) -> ApplicationEvent:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    return ApplicationEvent(
        id=uuid4(),
        application_id=application_id,
        event_type=ApplicationStage.INTERVIEW,
        round_no=1,
        occurred_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.anyio
async def test_create_endpoint_requires_authentication() -> None:
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/applications",
            json={
                "company_name": "示例科技",
                "job_title": "产品运营",
                "applied_at": "2026-09-18",
            },
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.anyio
async def test_create_endpoint_returns_application_and_initial_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    session = AsyncMock(spec=AsyncSession)
    application = application_record(user.id)
    creator = AsyncMock(return_value=application)
    monkeypatch.setattr(application_routes, "create_application", creator)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/applications",
            json={
                "company_name": "示例科技",
                "job_title": "产品运营",
                "applied_at": "2026-09-18",
            },
        )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["current_stage"] == "APPLICATION"
    assert data["process_status"] == "ACTIVE"
    assert data["events"][0]["event_type"] == "APPLICATION"
    creator.assert_awaited_once()
    assert creator.await_args.args[1] == user.id


@pytest.mark.anyio
async def test_list_endpoint_passes_status_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    loader = AsyncMock(return_value=[application_record(user.id)])
    monkeypatch.setattr(application_routes, "list_applications", loader)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/applications?process_status=ACTIVE")

    assert response.status_code == 200
    assert response.json()["data"][0]["company_name"] == "示例科技"
    assert loader.await_args.args[2] is ApplicationStatus.ACTIVE


@pytest.mark.anyio
async def test_cross_user_detail_uses_not_found_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    monkeypatch.setattr(
        application_routes,
        "get_application",
        AsyncMock(side_effect=ApplicationNotFoundError),
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(f"/api/v1/applications/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "APPLICATION_NOT_FOUND"


@pytest.mark.anyio
async def test_terminal_status_requires_stage_at_http_boundary() -> None:
    user = authenticated_user()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.put(
            f"/api/v1/applications/{uuid4()}/status",
            json={"process_status": "REJECTED"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_status_endpoint_persists_terminal_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    application = application_record(user.id)
    application.process_status = ApplicationStatus.REJECTED
    application.current_stage = ApplicationStage.INTERVIEW
    application.current_round = 1
    updater = AsyncMock(return_value=application)
    monkeypatch.setattr(application_routes, "update_application_status", updater)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.put(
            f"/api/v1/applications/{application.id}/status",
            json={
                "process_status": "REJECTED",
                "current_stage": "INTERVIEW",
                "current_round": 1,
            },
        )

    assert response.status_code == 200
    assert response.json()["data"]["process_status"] == "REJECTED"
    assert response.json()["data"]["current_round"] == 1
    assert updater.await_args.args[1] == user.id
    assert updater.await_args.args[3].current_stage is ApplicationStage.INTERVIEW


@pytest.mark.anyio
async def test_create_event_endpoint_returns_timeline_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = authenticated_user()
    application_id = uuid4()
    event = event_record(application_id)
    creator = AsyncMock(return_value=event)
    monkeypatch.setattr(application_routes, "create_application_event", creator)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/applications/{application_id}/events",
            json={
                "event_type": "INTERVIEW",
                "round_no": 1,
                "occurred_at": "2026-09-22",
            },
        )

    assert response.status_code == 201
    assert response.json()["data"]["event_type"] == "INTERVIEW"
    assert response.json()["data"]["round_no"] == 1
    assert creator.await_args.args[1] == user.id
    assert creator.await_args.args[2] == application_id


@pytest.mark.anyio
@pytest.mark.parametrize("method", ["put", "delete"])
async def test_event_mutations_hide_missing_or_foreign_events(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
) -> None:
    user = authenticated_user()
    service_name = (
        "update_application_event" if method == "put" else "delete_application_event"
    )
    monkeypatch.setattr(
        application_routes,
        service_name,
        AsyncMock(side_effect=ApplicationEventNotFoundError),
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.request(
            method.upper(),
            f"/api/v1/application-events/{uuid4()}",
            json=(
                {
                    "event_type": "ASSESSMENT",
                    "occurred_at": "2026-09-22",
                }
                if method == "put"
                else None
            ),
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "APPLICATION_EVENT_NOT_FOUND"
