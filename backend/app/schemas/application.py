"""API contracts for applications and their timeline events."""

from datetime import UTC, date, datetime, time
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.application import (
    ApplicationEventOutcome,
    ApplicationStage,
    ApplicationStatus,
)

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def normalize_datetime(value: object) -> object:
    """Accept the date-only MVP contract and normalize naive values to UTC."""

    if isinstance(value, str) and len(value) == 10:
        try:
            value = date.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, time.min, tzinfo=UTC)
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class ApplicationSchema(BaseModel):
    """Strict base for application API payloads."""

    model_config = ConfigDict(extra="forbid")


class ApplicationCreate(ApplicationSchema):
    """Create from a stored source or a complete manual snapshot."""

    job_id: UUID | None = None
    resume_version_id: UUID | None = None
    company_name: NonEmptyText | None = Field(default=None, max_length=200)
    job_title: NonEmptyText | None = Field(default=None, max_length=300)
    job_url: NonEmptyText | None = None
    applied_at: datetime
    note: str | None = None

    @field_validator("applied_at", mode="before")
    @classmethod
    def validate_applied_at(cls, value: object) -> object:
        return normalize_datetime(value)

    @model_validator(mode="after")
    def require_snapshot_or_source(self) -> Self:
        if (
            self.job_id is None
            and self.resume_version_id is None
            and (self.company_name is None or self.job_title is None)
        ):
            raise ValueError(
                "company_name and job_title are required for manual applications"
            )
        return self


class ApplicationUpdate(ApplicationSchema):
    """Editable snapshot and optional source links."""

    job_id: UUID | None = None
    resume_version_id: UUID | None = None
    company_name: NonEmptyText | None = Field(default=None, max_length=200)
    job_title: NonEmptyText | None = Field(default=None, max_length=300)
    job_url: NonEmptyText | None = None
    applied_at: datetime | None = None
    note: str | None = None

    @field_validator("applied_at", mode="before")
    @classmethod
    def validate_applied_at(cls, value: object) -> object:
        return normalize_datetime(value)

    @model_validator(mode="after")
    def reject_empty_update(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self


class ApplicationStatusUpdate(ApplicationSchema):
    """Update lifecycle status and explicitly capture a terminal stage."""

    process_status: ApplicationStatus
    current_stage: ApplicationStage | None = None
    current_round: int | None = Field(default=None, ge=1, le=32767)

    @model_validator(mode="after")
    def validate_stage(self) -> Self:
        if (
            self.process_status is not ApplicationStatus.ACTIVE
            and self.current_stage is None
        ):
            raise ValueError("current_stage is required for a terminal status")
        if self.current_stage is ApplicationStage.INTERVIEW:
            if self.current_round is None:
                raise ValueError("current_round is required for an interview")
        elif self.current_round is not None:
            raise ValueError("current_round is only valid for an interview")
        return self


class ApplicationEventFields(ApplicationSchema):
    """Shared constraints for creating and updating timeline events."""

    event_type: ApplicationStage
    custom_event_name: NonEmptyText | None = Field(default=None, max_length=200)
    round_no: int | None = Field(default=None, ge=1, le=32767)
    occurred_at: datetime
    outcome: ApplicationEventOutcome | None = None
    note: str | None = None

    @field_validator("occurred_at", mode="before")
    @classmethod
    def validate_occurred_at(cls, value: object) -> object:
        return normalize_datetime(value)

    @model_validator(mode="after")
    def validate_stage_details(self) -> Self:
        if self.event_type is ApplicationStage.INTERVIEW:
            if self.round_no is None:
                raise ValueError("round_no is required for an interview")
        elif self.round_no is not None:
            raise ValueError("round_no is only valid for an interview")
        if self.event_type is ApplicationStage.OTHER:
            if self.custom_event_name is None:
                raise ValueError("custom_event_name is required for OTHER")
        elif self.custom_event_name is not None:
            raise ValueError("custom_event_name is only valid for OTHER")
        return self


class ApplicationEventCreate(ApplicationEventFields):
    """Append one hiring milestone."""


class ApplicationEventUpdate(ApplicationEventFields):
    """Replace the editable content of one milestone."""


class ApplicationEventData(ApplicationEventFields):
    id: UUID
    application_id: UUID
    created_at: datetime
    updated_at: datetime


class ApplicationListItem(ApplicationSchema):
    id: UUID
    job_id: UUID | None
    resume_version_id: UUID | None
    company_name: str
    job_title: str
    job_url: str | None
    applied_at: datetime
    current_stage: ApplicationStage
    current_round: int | None
    process_status: ApplicationStatus
    note: str | None
    created_at: datetime
    updated_at: datetime


class ApplicationData(ApplicationListItem):
    events: list[ApplicationEventData]


class ApplicationResponse(ApplicationSchema):
    data: ApplicationData


class ApplicationListResponse(ApplicationSchema):
    data: list[ApplicationListItem]


class ApplicationEventResponse(ApplicationSchema):
    data: ApplicationEventData


class ApplicationEventListResponse(ApplicationSchema):
    data: list[ApplicationEventData]
