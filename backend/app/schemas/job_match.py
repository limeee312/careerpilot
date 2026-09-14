"""Public contracts for batch analysis progress and ranked match results."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.matching import (
    ConfidenceLevel,
    EligibilityStatus,
    RecommendationLevel,
)
from app.models.job import BatchStatus


class JobAnalysisStatus(StrEnum):
    """User-facing state of one job in the current batch analysis run."""

    PENDING = "PENDING"
    PARSING = "PARSING"
    MATCHING = "MATCHING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobMatchSchema(BaseModel):
    """Strict API response base used by match-result endpoints."""

    model_config = ConfigDict(extra="forbid")


class MatchResultSummaryData(JobMatchSchema):
    """Rankable fields needed by the batch result page."""

    id: UUID
    rank: int | None
    near_tie_group: int | None
    is_tied: bool
    eligibility_status: EligibilityStatus
    total_score: Decimal
    display_score: int
    confidence_score: Decimal
    confidence_level: ConfidenceLevel
    recommendation_level: RecommendationLevel
    recommendation: str
    created_at: datetime


class JobMatchResultItemData(JobMatchSchema):
    """One original job plus its current analysis outcome, if available."""

    job_id: UUID
    company_name: str
    title: str
    location: str | None
    department: str | None
    source_url: str | None
    analysis_status: JobAnalysisStatus
    error_code: str | None
    result: MatchResultSummaryData | None


class JobMatchBatchResultData(JobMatchSchema):
    """A user-owned batch and the latest result for its current parse run."""

    id: UUID
    name: str | None
    status: BatchStatus
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    jobs: list[JobMatchResultItemData]
    created_at: datetime
    updated_at: datetime


class JobMatchBatchResultResponse(JobMatchSchema):
    data: JobMatchBatchResultData
