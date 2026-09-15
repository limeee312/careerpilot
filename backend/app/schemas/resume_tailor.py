"""Public response contract for an unpersisted Resume Tailor draft."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.ai.resume_tailor.schemas import ResumeTailorOutput
from app.schemas.resume import ResumeMasterData


class ResumeTailorAPISchema(BaseModel):
    """Strict public schema for the Resume Tailor endpoint."""

    model_config = ConfigDict(extra="forbid")


class ResumeTailorDraftData(ResumeTailorAPISchema):
    """One reviewable draft and the immutable snapshot it was derived from."""

    job_id: UUID
    match_result_id: UUID
    resume_master_id: UUID
    company_name: str
    job_title: str
    source_resume_snapshot: ResumeMasterData
    draft: ResumeTailorOutput
    skill_name: str
    prompt_version: str
    model: str
    attempts: int = Field(ge=1, le=2)


class ResumeTailorDraftResponse(ResumeTailorAPISchema):
    data: ResumeTailorDraftData
