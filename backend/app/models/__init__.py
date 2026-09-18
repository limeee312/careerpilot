"""SQLAlchemy models exposed to Alembic autogeneration."""

from app.models.base import Base, CreatedAtMixin
from app.models.job import BatchStatus, Job, JobMatchBatch
from app.models.matching import (
    AIStatus,
    AssessmentStatus,
    ConfidenceLevel,
    EligibilityStatus,
    EvidenceGrade,
    JobMatchResult,
    JobParseResult,
    JobRequirement,
    MatchDimensionScore,
    MatchGateCheck,
    MatchRequirementAssessment,
    RecommendationLevel,
)
from app.models.resume import (
    ExperienceType,
    ResumeEducation,
    ResumeExperience,
    ResumeMaster,
    ResumeProject,
    ResumeSkill,
)
from app.models.resume_version import ResumeVersion, ResumeVersionStatus
from app.models.user import User

__all__ = [
    "Base",
    "BatchStatus",
    "CreatedAtMixin",
    "AIStatus",
    "AssessmentStatus",
    "ConfidenceLevel",
    "EligibilityStatus",
    "EvidenceGrade",
    "ExperienceType",
    "Job",
    "JobMatchBatch",
    "JobMatchResult",
    "JobParseResult",
    "JobRequirement",
    "MatchDimensionScore",
    "MatchGateCheck",
    "MatchRequirementAssessment",
    "RecommendationLevel",
    "ResumeEducation",
    "ResumeExperience",
    "ResumeMaster",
    "ResumeProject",
    "ResumeSkill",
    "ResumeVersion",
    "ResumeVersionStatus",
    "User",
]
