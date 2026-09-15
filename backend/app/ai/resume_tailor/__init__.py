"""Resume Tailor v1 contracts and orchestration."""

from app.ai.resume_tailor.constants import (
    MAX_RESUME_TAILOR_ATTEMPTS,
    RESUME_TAILOR_SKILL_NAME,
    RESUME_TAILOR_VERSION,
)
from app.ai.resume_tailor.prompt import RESUME_TAILOR_PROMPT_V1
from app.ai.resume_tailor.schemas import (
    EvidenceReference,
    ImprovementSuggestion,
    ResumeTailorOutput,
    SourceExperience,
    SourceProject,
    SourceSkill,
    TailoredBullet,
    TailoredExperience,
    TailoredProject,
    TailorInput,
)
from app.ai.resume_tailor.service import ResumeTailorResult, tailor_resume
from app.ai.resume_tailor.validator import validate_resume_tailor_output

__all__ = [
    "MAX_RESUME_TAILOR_ATTEMPTS",
    "RESUME_TAILOR_PROMPT_V1",
    "RESUME_TAILOR_SKILL_NAME",
    "RESUME_TAILOR_VERSION",
    "EvidenceReference",
    "ImprovementSuggestion",
    "ResumeTailorOutput",
    "ResumeTailorResult",
    "SourceExperience",
    "SourceProject",
    "SourceSkill",
    "TailorInput",
    "TailoredBullet",
    "TailoredExperience",
    "TailoredProject",
    "tailor_resume",
    "validate_resume_tailor_output",
]
