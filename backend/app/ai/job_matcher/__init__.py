"""Resume-Job Matcher v1 contracts."""

from app.ai.job_matcher.constants import (
    JOB_MATCHER_SKILL_NAME,
    JOB_MATCHER_VERSION,
    MAX_JOB_MATCHER_ATTEMPTS,
)
from app.ai.job_matcher.prompt import JOB_MATCHER_PROMPT_V1
from app.ai.job_matcher.schemas import (
    EvidenceSourceType,
    GapImportance,
    GateAssessment,
    GateEvidence,
    MatcherInput,
    MatcherOutput,
    MatchGap,
    RequirementAssessment,
    ResumeEvidenceItem,
    ResumeEvidenceRef,
)
from app.ai.job_matcher.service import JobMatcherResult, match_job
from app.ai.job_matcher.validator import validate_matcher_output
from app.domain.matching import (
    AssessmentStatus,
    EligibilityStatus,
    EvidenceGrade,
    MatchLevel,
)

__all__ = [
    "JOB_MATCHER_SKILL_NAME",
    "JOB_MATCHER_PROMPT_V1",
    "JOB_MATCHER_VERSION",
    "MAX_JOB_MATCHER_ATTEMPTS",
    "AssessmentStatus",
    "EligibilityStatus",
    "EvidenceGrade",
    "EvidenceSourceType",
    "GapImportance",
    "GateAssessment",
    "GateEvidence",
    "JobMatcherResult",
    "MatchGap",
    "MatchLevel",
    "MatcherInput",
    "MatcherOutput",
    "RequirementAssessment",
    "ResumeEvidenceItem",
    "ResumeEvidenceRef",
    "match_job",
    "validate_matcher_output",
]
