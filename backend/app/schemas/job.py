"""Contracts for manually creating user-owned job comparison batches."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.models.job import BatchStatus


class JobSchema(BaseModel):
    """Strict job payload base with consistent whitespace normalization."""

    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def normalize_strings(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value


class JobInput(JobSchema):
    company_name: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    location: str | None = Field(default=None, max_length=200)
    department: str | None = Field(default=None, max_length=200)
    source_url: HttpUrl | None = None
    raw_jd: str = Field(min_length=50)


class JobBatchCreate(JobSchema):
    name: str | None = Field(default=None, max_length=200)
    jobs: list[JobInput] = Field(min_length=1, max_length=5)


class JobData(JobSchema):
    id: UUID
    company_name: str
    title: str
    location: str | None
    department: str | None
    source_url: str | None
    raw_jd: str
    created_at: datetime
    updated_at: datetime


class JobBatchData(JobSchema):
    id: UUID
    name: str | None
    status: BatchStatus
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    jobs: list[JobData]
    created_at: datetime
    updated_at: datetime


class JobBatchResponse(JobSchema):
    data: JobBatchData
