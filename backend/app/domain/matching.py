"""Shared parsing and matching enums used across AI and persistence layers."""

from enum import StrEnum


class RequirementType(StrEnum):
    """How a requirement participates in eligibility or capability matching."""

    HARD = "HARD"
    CORE = "CORE"
    STANDARD = "STANDARD"
    PREFERRED = "PREFERRED"


class MatchDimension(StrEnum):
    """The single primary capability dimension for a non-hard requirement."""

    RESPONSIBILITY = "RESPONSIBILITY"
    TOOLS_METHODS = "TOOLS_METHODS"
    BUSINESS_DOMAIN = "BUSINESS_DOMAIN"
    OWNERSHIP = "OWNERSHIP"
    OUTCOME = "OUTCOME"
    COMMUNICATION = "COMMUNICATION"


class EligibilityStatus(StrEnum):
    """Deterministic aggregate of all hard-gate checks."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class EvidenceGrade(StrEnum):
    """Strength of resume evidence supporting a requirement assessment."""

    A = "A"
    B = "B"
    C = "C"
    X = "X"


class AssessmentStatus(StrEnum):
    """Whether current resume evidence supports a non-hard requirement."""

    MATCHED = "MATCHED"
    PARTIAL = "PARTIAL"
    CONFIRMED_GAP = "CONFIRMED_GAP"
    UNKNOWN = "UNKNOWN"


class ConfidenceLevel(StrEnum):
    """Backend-derived confidence band for the current evidence coverage."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RecommendationLevel(StrEnum):
    """Backend-derived match recommendation band."""

    BLOCKED = "BLOCKED"
    PRIORITY = "PRIORITY"
    STRONG = "STRONG"
    SELECTIVE = "SELECTIVE"
    LOW = "LOW"
