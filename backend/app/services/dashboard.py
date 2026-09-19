"""User-scoped Dashboard aggregation."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.schemas.dashboard import DashboardData, DashboardOverview
from app.services.application import serialize_application_list_item

RECENT_APPLICATION_LIMIT = 5


async def get_dashboard(
    session: AsyncSession,
    user_id: UUID,
) -> DashboardData:
    """Return lifecycle counts and the user's most recent applications."""

    count_rows = (
        await session.execute(
            select(Application.process_status, func.count(Application.id))
            .where(Application.user_id == user_id)
            .group_by(Application.process_status)
        )
    ).all()
    counts = {status: 0 for status in ApplicationStatus}
    for process_status, count in count_rows:
        counts[process_status] = count

    recent = list(
        await session.scalars(
            select(Application)
            .where(Application.user_id == user_id)
            .order_by(Application.applied_at.desc(), Application.created_at.desc())
            .limit(RECENT_APPLICATION_LIMIT)
        )
    )

    return DashboardData(
        overview=DashboardOverview(
            total=sum(counts.values()),
            active=counts[ApplicationStatus.ACTIVE],
            rejected=counts[ApplicationStatus.REJECTED],
            offer=counts[ApplicationStatus.OFFER],
            withdrawn=counts[ApplicationStatus.WITHDRAWN],
        ),
        recent_applications=[
            serialize_application_list_item(application) for application in recent
        ],
    )
