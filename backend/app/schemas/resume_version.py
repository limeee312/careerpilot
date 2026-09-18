"""API contracts for saved, job-targeted resume versions."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.ai.resume_tailor.schemas import ResumeTailorOutput
from app.models.resume import ExperienceType
from app.models.resume_version import ResumeVersionStatus
from app.schemas.resume import ResumeMasterData, YearMonth

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ResumeVersionSchema(BaseModel):
    """Strict base for version persistence contracts."""

    model_config = ConfigDict(extra="forbid")


class ResumeVersionCreate(ResumeVersionSchema):
    """A user-confirmed Tailor draft to validate and persist."""

    match_result_id: UUID
    name: NonEmptyText | None = Field(default=None, max_length=255)
    draft: ResumeTailorOutput
    prompt_version: NonEmptyText = Field(max_length=50)
    model: NonEmptyText = Field(max_length=100)


class ResumeVersionEducation(ResumeVersionSchema):
    source_id: UUID
    school: str
    degree: str
    major: str
    start_date: YearMonth
    end_date: YearMonth
    gpa: str | None
    courses: str | None
    description: str | None


class ResumeVersionExperience(ResumeVersionSchema):
    source_id: UUID
    experience_type: ExperienceType
    organization: str
    position: str
    start_date: YearMonth
    end_date: YearMonth | None
    is_current: bool
    bullets: list[NonEmptyText] = Field(min_length=1)


class ResumeVersionProject(ResumeVersionSchema):
    source_id: UUID
    name: str
    role: str | None
    start_date: YearMonth | None
    end_date: YearMonth | None
    background: str | None
    bullets: list[NonEmptyText] = Field(min_length=1)


class ResumeVersionSkill(ResumeVersionSchema):
    source_id: UUID
    skill_name: str
    skill_category: str | None
    proficiency: str | None


class ResumeVersionContent(ResumeVersionSchema):
    """Final content assembled from immutable source fields and the draft."""

    summary: str | None
    education: list[ResumeVersionEducation]
    experiences: list[ResumeVersionExperience]
    projects: list[ResumeVersionProject]
    skills: list[ResumeVersionSkill]


class ResumeVersionListItem(ResumeVersionSchema):
    id: UUID
    resume_master_id: UUID
    job_id: UUID
    match_result_id: UUID | None
    name: str
    status: ResumeVersionStatus
    company_name: str
    job_title: str
    prompt_version: str
    model: str
    created_at: datetime
    updated_at: datetime


class ResumeVersionData(ResumeVersionListItem):
    content: ResumeVersionContent
    source_resume_snapshot: ResumeMasterData
    source_job_snapshot: dict[str, object]


class ResumeVersionListResponse(ResumeVersionSchema):
    data: list[ResumeVersionListItem]


class ResumeVersionResponse(ResumeVersionSchema):
    data: ResumeVersionData
