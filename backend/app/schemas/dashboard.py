"""Dashboard aggregate response contracts."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.application import ApplicationListItem


class DashboardSchema(BaseModel):
    """Strict base for Dashboard API responses."""

    model_config = ConfigDict(extra="forbid")


class DashboardOverview(DashboardSchema):
    """Counts for every application lifecycle state."""

    total: int = Field(ge=0)
    active: int = Field(ge=0)
    rejected: int = Field(ge=0)
    offer: int = Field(ge=0)
    withdrawn: int = Field(ge=0)


class DashboardData(DashboardSchema):
    """The complete MVP Dashboard payload."""

    overview: DashboardOverview
    recent_applications: list[ApplicationListItem]


class DashboardResponse(DashboardSchema):
    """Top-level Dashboard response envelope."""

    data: DashboardData
