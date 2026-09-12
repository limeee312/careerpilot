"""Resume-Job Matcher v1 contracts."""

from app.ai.job_matcher.constants import (
    JOB_MATCHER_SKILL_NAME,
    JOB_MATCHER_VERSION,
)
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
from app.ai.job_matcher.validator import validate_matcher_output
from app.domain.matching import (
    AssessmentStatus,
    EligibilityStatus,
    EvidenceGrade,
    MatchLevel,
)

__all__ = [
    "JOB_MATCHER_SKILL_NAME",
    "JOB_MATCHER_VERSION",
    "AssessmentStatus",
    "EligibilityStatus",
    "EvidenceGrade",
    "EvidenceSourceType",
    "GapImportance",
    "GateAssessment",
    "GateEvidence",
    "MatchGap",
    "MatchLevel",
    "MatcherInput",
    "MatcherOutput",
    "RequirementAssessment",
    "ResumeEvidenceItem",
    "ResumeEvidenceRef",
    "validate_matcher_output",
]
