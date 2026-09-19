"""Dashboard aggregation and HTTP contract tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import dashboard as dashboard_routes
from app.database import get_db_session
from app.dependencies import get_current_user
from app.main import app
from app.models.application import Application, ApplicationStage, ApplicationStatus
from app.models.user import User
from app.schemas.dashboard import DashboardData, DashboardOverview
from app.services.dashboard import get_dashboard


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def application_record(
    user_id,
    *,
    company_name: str,
    applied_at: datetime,
    status: ApplicationStatus = ApplicationStatus.ACTIVE,
) -> Application:
    return Application(
        id=uuid4(),
        user_id=user_id,
        company_name=company_name,
        job_title="产品运营",
        applied_at=applied_at,
        current_stage=ApplicationStage.APPLICATION,
        process_status=status,
        created_at=applied_at,
        updated_at=applied_at,
    )


@pytest.mark.anyio
async def test_dashboard_service_maps_counts_and_recent_applications() -> None:
    user_id = uuid4()
    now = datetime(2026, 9, 19, tzinfo=UTC)
    recent = [
        application_record(user_id, company_name="新公司", applied_at=now),
        application_record(
            user_id,
            company_name="旧公司",
            applied_at=now - timedelta(days=1),
            status=ApplicationStatus.OFFER,
        ),
    ]
    rows = MagicMock()
    rows.all.return_value = [
        (ApplicationStatus.ACTIVE, 3),
        (ApplicationStatus.REJECTED, 2),
        (ApplicationStatus.OFFER, 1),
    ]
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = rows
    session.scalars.return_value = recent

    dashboard = await get_dashboard(session, user_id)

    assert dashboard.overview.model_dump() == {
        "total": 6,
        "active": 3,
        "rejected": 2,
        "offer": 1,
        "withdrawn": 0,
    }
    assert [item.company_name for item in dashboard.recent_applications] == [
        "新公司",
        "旧公司",
    ]


@pytest.mark.anyio
async def test_dashboard_endpoint_requires_authentication() -> None:
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/dashboard")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.anyio
async def test_dashboard_endpoint_returns_aggregate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(
        id=uuid4(),
        email="candidate@example.com",
        password_hash="$argon2id$private",
    )
    loader = AsyncMock(
        return_value=DashboardData(
            overview=DashboardOverview(
                total=12,
                active=5,
                rejected=4,
                offer=2,
                withdrawn=1,
            ),
            recent_applications=[],
        )
    )
    monkeypatch.setattr(dashboard_routes, "get_dashboard", loader)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock(spec=AsyncSession)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/dashboard")

    assert response.status_code == 200
    assert response.json()["data"]["overview"] == {
        "total": 12,
        "active": 5,
        "rejected": 4,
        "offer": 2,
        "withdrawn": 1,
    }
    loader.assert_awaited_once()
    assert loader.await_args.args[1] == user.id
