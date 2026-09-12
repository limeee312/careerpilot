"""Deterministic trust-boundary checks for Resume-Job Matcher output."""

import re
from collections import Counter

from app.ai.errors import AIInvalidOutputError
from app.ai.job_matcher.schemas import (
    GateEvidence,
    MatcherInput,
    MatcherOutput,
    ResumeEvidenceRef,
)
from app.domain.matching import EligibilityStatus, EvidenceGrade, RequirementType

WHITESPACE_PATTERN = re.compile(r"\s+", flags=re.UNICODE)


def normalize_quote_whitespace(value: str) -> str:
    """Ignore Unicode whitespace while preserving every substantive character."""

    return WHITESPACE_PATTERN.sub("", value)


def _validate_exact_coverage(
    *,
    expected: list[str],
    actual: list[str],
    label: str,
) -> None:
    if Counter(actual) != Counter(expected):
        raise AIInvalidOutputError(
            f"{label} must assess every matching requirement exactly once"
        )


def _is_grounded(
    matcher_input: MatcherInput,
    evidence: GateEvidence | ResumeEvidenceRef,
) -> bool:
    if evidence.source_type is None or evidence.source_quote is None:
        return True

    normalized_quote = normalize_quote_whitespace(evidence.source_quote)
    return any(
        item.source_type == evidence.source_type
        and item.source_id == evidence.source_id
        and normalized_quote in normalize_quote_whitespace(item.content)
        for item in matcher_input.resume_evidence
    )


def validate_matcher_output(
    matcher_input: MatcherInput,
    output: MatcherOutput,
) -> MatcherOutput:
    """Validate requirement coverage and every resume evidence reference."""

    hard_keys = [
        item.requirement_key
        for item in matcher_input.parsed_job.requirements
        if item.requirement_type is RequirementType.HARD
    ]
    capability_keys = [
        item.requirement_key
        for item in matcher_input.parsed_job.requirements
        if item.requirement_type is not RequirementType.HARD
    ]
    all_keys = set(hard_keys) | set(capability_keys)

    _validate_exact_coverage(
        expected=hard_keys,
        actual=[item.requirement_key for item in output.gate_assessments],
        label="gate_assessments",
    )
    _validate_exact_coverage(
        expected=capability_keys,
        actual=[item.requirement_key for item in output.requirement_assessments],
        label="requirement_assessments",
    )

    for gap in output.gaps:
        if gap.requirement_key not in all_keys:
            raise AIInvalidOutputError(
                f"gap references unknown requirement {gap.requirement_key}"
            )

    for assessment in output.gate_assessments:
        concrete_evidence = [
            item for item in assessment.evidence if item.source_quote is not None
        ]
        conclusive_statuses = {EligibilityStatus.PASS, EligibilityStatus.FAIL}
        if assessment.status in conclusive_statuses and not concrete_evidence:
            raise AIInvalidOutputError(
                f"{assessment.requirement_key} {assessment.status} requires evidence"
            )
        for evidence in concrete_evidence:
            if not _is_grounded(matcher_input, evidence):
                raise AIInvalidOutputError(
                    f"{assessment.requirement_key} evidence is not grounded in resume"
                )

    for assessment in output.requirement_assessments:
        if assessment.evidence_grade is not EvidenceGrade.X and not assessment.evidence:
            raise AIInvalidOutputError(
                f"{assessment.requirement_key} evidence grade requires evidence"
            )
        for evidence in assessment.evidence:
            if not _is_grounded(matcher_input, evidence):
                raise AIInvalidOutputError(
                    f"{assessment.requirement_key} evidence is not grounded in resume"
                )

    return output
