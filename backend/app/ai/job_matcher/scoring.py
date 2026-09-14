"""Deterministic scoring and ranking for validated Matcher output."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from app.ai.job_matcher.schemas import (
    GateAssessment,
    MatcherOutput,
    RequirementAssessment,
)
from app.ai.job_parser.schemas import JobParserOutput, ParsedRequirement
from app.domain.matching import (
    ConfidenceLevel,
    EligibilityStatus,
    EvidenceGrade,
    MatchDimension,
    RecommendationLevel,
    RequirementType,
)

EVIDENCE_CAP: Final[dict[EvidenceGrade, int]] = {
    EvidenceGrade.A: 4,
    EvidenceGrade.B: 3,
    EvidenceGrade.C: 1,
    EvidenceGrade.X: 0,
}

EVIDENCE_COVERAGE: Final[dict[EvidenceGrade, Decimal]] = {
    EvidenceGrade.A: Decimal("1"),
    EvidenceGrade.B: Decimal("1"),
    EvidenceGrade.C: Decimal("0.5"),
    EvidenceGrade.X: Decimal("0"),
}

DIMENSION_MAX: Final[dict[MatchDimension, Decimal]] = {
    MatchDimension.RESPONSIBILITY: Decimal("35"),
    MatchDimension.TOOLS_METHODS: Decimal("20"),
    MatchDimension.BUSINESS_DOMAIN: Decimal("15"),
    MatchDimension.OWNERSHIP: Decimal("15"),
    MatchDimension.OUTCOME: Decimal("10"),
    MatchDimension.COMMUNICATION: Decimal("5"),
}

SCORE_QUANTUM: Final = Decimal("0.01")
DETAIL_QUANTUM: Final = Decimal("0.001")
DISPLAY_QUANTUM: Final = Decimal("1")
NEAR_TIE_DISTANCE: Final = Decimal("3")

RECOMMENDATION_TEXT: Final[dict[RecommendationLevel, str]] = {
    RecommendationLevel.BLOCKED: "存在明确硬性条件冲突，不进入正常可投排序。",
    RecommendationLevel.PRIORITY: "优先投递",
    RecommendationLevel.STRONG: "匹配较强",
    RecommendationLevel.SELECTIVE: "选择性投递",
    RecommendationLevel.LOW: "低优先级",
}


class MatchScoringError(ValueError):
    """Raised when otherwise validated inputs cannot be scored consistently."""


@dataclass(frozen=True, slots=True)
class ScoredRequirement:
    """One evidence-capped requirement contribution to the total score."""

    requirement_key: str
    dimension: MatchDimension
    importance: int
    match_level: int
    evidence_grade: EvidenceGrade
    evidence_cap: int
    effective_level: int
    normalized_requirement_weight: Decimal
    effective_weight: Decimal
    weighted_score: Decimal


@dataclass(frozen=True, slots=True)
class DimensionScore:
    """One applicable dimension after N/A dimensions are reweighted away."""

    dimension: MatchDimension
    base_max_score: Decimal
    max_score: Decimal
    raw_score: Decimal
    normalized_score: Decimal


@dataclass(frozen=True, slots=True)
class MatchScoringResult:
    """All backend-owned values derived from one Matcher result."""

    eligibility_status: EligibilityStatus
    total_score: Decimal
    display_score: int
    confidence_score: Decimal
    confidence_level: ConfidenceLevel
    recommendation_level: RecommendationLevel
    recommendation: str
    requirement_scores: tuple[ScoredRequirement, ...]
    dimension_scores: tuple[DimensionScore, ...]

    @property
    def responsibility_score_rate(self) -> Decimal | None:
        """Return the normalized RESPONSIBILITY rate used by ranking."""

        return next(
            (
                score.normalized_score
                for score in self.dimension_scores
                if score.dimension is MatchDimension.RESPONSIBILITY
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class MatchRankingCandidate:
    """Minimal persisted match projection needed for deterministic ranking."""

    match_id: str
    eligibility_status: EligibilityStatus
    total_score: Decimal
    responsibility_score_rate: Decimal | None
    confidence_score: Decimal


@dataclass(frozen=True, slots=True)
class RankedMatch:
    """One normally rankable match and its competition rank."""

    candidate: MatchRankingCandidate
    rank: int
    near_tie_group: int
    is_tied: bool


@dataclass(frozen=True, slots=True)
class MatchRankingResult:
    """Normal ordering plus FAIL matches kept outside that ordering."""

    ranked: tuple[RankedMatch, ...]
    blocked: tuple[MatchRankingCandidate, ...]


def _quantize_score(value: Decimal) -> Decimal:
    return value.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)


def _quantize_detail(value: Decimal) -> Decimal:
    return value.quantize(DETAIL_QUANTUM, rounding=ROUND_HALF_UP)


def _assessment_maps(
    parsed_job: JobParserOutput,
    output: MatcherOutput,
) -> tuple[
    list[ParsedRequirement],
    dict[str, RequirementAssessment],
    list[GateAssessment],
]:
    capability_requirements = [
        requirement
        for requirement in parsed_job.requirements
        if requirement.requirement_type is not RequirementType.HARD
    ]
    hard_requirements = [
        requirement
        for requirement in parsed_job.requirements
        if requirement.requirement_type is RequirementType.HARD
    ]

    assessments = {
        assessment.requirement_key: assessment
        for assessment in output.requirement_assessments
    }
    gates = {
        assessment.requirement_key: assessment for assessment in output.gate_assessments
    }

    expected_capability_keys = {
        requirement.requirement_key for requirement in capability_requirements
    }
    expected_hard_keys = {
        requirement.requirement_key for requirement in hard_requirements
    }

    if len(assessments) != len(output.requirement_assessments) or (
        set(assessments) != expected_capability_keys
    ):
        raise MatchScoringError(
            "requirement assessments must cover every non-HARD requirement once"
        )
    if len(gates) != len(output.gate_assessments) or set(gates) != expected_hard_keys:
        raise MatchScoringError(
            "gate assessments must cover every HARD requirement once"
        )
    if not capability_requirements:
        raise MatchScoringError("at least one non-HARD requirement is required")

    return capability_requirements, assessments, list(gates.values())


def _calculate_eligibility(
    gate_assessments: list[GateAssessment],
) -> EligibilityStatus:
    statuses = {assessment.status for assessment in gate_assessments}
    if EligibilityStatus.FAIL in statuses:
        return EligibilityStatus.FAIL
    if EligibilityStatus.WARN in statuses:
        return EligibilityStatus.WARN
    return EligibilityStatus.PASS


def calculate_confidence_level(
    confidence_score: Decimal,
    *,
    has_unknown_hard_gate: bool,
) -> ConfidenceLevel:
    if confidence_score >= Decimal("85"):
        level = ConfidenceLevel.HIGH
    elif confidence_score >= Decimal("60"):
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    if has_unknown_hard_gate and level is ConfidenceLevel.HIGH:
        return ConfidenceLevel.MEDIUM
    return level


def round_score_for_display(total_score: Decimal) -> int:
    """Round the persisted two-decimal score with conventional half-up rules."""

    if total_score < Decimal("0") or total_score > Decimal("100"):
        raise MatchScoringError("total score must be between 0 and 100")
    return int(total_score.quantize(DISPLAY_QUANTUM, rounding=ROUND_HALF_UP))


def calculate_recommendation_level(
    *,
    total_score: Decimal,
    eligibility_status: EligibilityStatus,
) -> RecommendationLevel:
    display_score = round_score_for_display(total_score)
    if eligibility_status is EligibilityStatus.FAIL:
        return RecommendationLevel.BLOCKED
    if display_score >= 85:
        return RecommendationLevel.PRIORITY
    if display_score >= 75:
        return RecommendationLevel.STRONG
    if display_score >= 65:
        return RecommendationLevel.SELECTIVE
    return RecommendationLevel.LOW


def score_match(
    parsed_job: JobParserOutput,
    output: MatcherOutput,
) -> MatchScoringResult:
    """Calculate deterministic capability, confidence, and recommendation values."""

    requirements, assessments, gates = _assessment_maps(parsed_job, output)

    requirements_by_dimension: dict[MatchDimension, list[ParsedRequirement]] = {}
    for requirement in requirements:
        if requirement.dimension is None:
            raise MatchScoringError("non-HARD requirement must have a dimension")
        requirements_by_dimension.setdefault(requirement.dimension, []).append(
            requirement
        )

    active_base_max = sum(
        (DIMENSION_MAX[dimension] for dimension in requirements_by_dimension),
        start=Decimal("0"),
    )

    scored_requirements: list[ScoredRequirement] = []
    dimension_scores: list[DimensionScore] = []
    total_score_unrounded = Decimal("0")
    confidence_unrounded = Decimal("0")

    for dimension in MatchDimension:
        dimension_requirements = requirements_by_dimension.get(dimension)
        if not dimension_requirements:
            continue

        base_max_score = DIMENSION_MAX[dimension]
        effective_max_score = base_max_score / active_base_max * Decimal("100")
        importance_sum = sum(
            (Decimal(requirement.importance) for requirement in dimension_requirements),
            start=Decimal("0"),
        )
        dimension_raw_unrounded = Decimal("0")

        for requirement in dimension_requirements:
            assessment = assessments[requirement.requirement_key]
            evidence_cap = EVIDENCE_CAP[assessment.evidence_grade]
            effective_level = min(int(assessment.match_level), evidence_cap)
            normalized_requirement_weight = (
                Decimal(requirement.importance) / importance_sum
            )
            effective_weight = effective_max_score * normalized_requirement_weight
            weighted_score = effective_weight * Decimal(effective_level) / Decimal("4")

            dimension_raw_unrounded += weighted_score
            confidence_unrounded += (
                effective_weight * EVIDENCE_COVERAGE[assessment.evidence_grade]
            )
            scored_requirements.append(
                ScoredRequirement(
                    requirement_key=requirement.requirement_key,
                    dimension=dimension,
                    importance=requirement.importance,
                    match_level=int(assessment.match_level),
                    evidence_grade=assessment.evidence_grade,
                    evidence_cap=evidence_cap,
                    effective_level=effective_level,
                    normalized_requirement_weight=_quantize_detail(
                        normalized_requirement_weight
                    ),
                    effective_weight=_quantize_detail(effective_weight),
                    weighted_score=_quantize_detail(weighted_score),
                )
            )

        total_score_unrounded += dimension_raw_unrounded
        dimension_scores.append(
            DimensionScore(
                dimension=dimension,
                base_max_score=base_max_score,
                max_score=_quantize_detail(effective_max_score),
                raw_score=_quantize_detail(dimension_raw_unrounded),
                normalized_score=_quantize_detail(
                    dimension_raw_unrounded / effective_max_score * Decimal("100")
                ),
            )
        )

    total_score = _quantize_score(total_score_unrounded)
    display_score = round_score_for_display(total_score)
    confidence_score = _quantize_score(confidence_unrounded)
    eligibility_status = _calculate_eligibility(gates)
    confidence_level = calculate_confidence_level(
        confidence_score,
        has_unknown_hard_gate=any(
            gate.status is EligibilityStatus.WARN for gate in gates
        ),
    )
    recommendation_level = calculate_recommendation_level(
        total_score=total_score,
        eligibility_status=eligibility_status,
    )

    return MatchScoringResult(
        eligibility_status=eligibility_status,
        total_score=total_score,
        display_score=display_score,
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        recommendation_level=recommendation_level,
        recommendation=RECOMMENDATION_TEXT[recommendation_level],
        requirement_scores=tuple(scored_requirements),
        dimension_scores=tuple(dimension_scores),
    )


def _ranking_sort_key(
    indexed_candidate: tuple[int, MatchRankingCandidate],
) -> tuple[bool, Decimal, Decimal, int]:
    index, candidate = indexed_candidate
    responsibility = candidate.responsibility_score_rate
    return (
        responsibility is None,
        -(responsibility if responsibility is not None else Decimal("0")),
        -candidate.confidence_score,
        index,
    )


def rank_match_candidates(
    candidates: list[MatchRankingCandidate],
) -> MatchRankingResult:
    """Rank eligible matches using anchored near-tie groups and stable ties."""

    if len({candidate.match_id for candidate in candidates}) != len(candidates):
        raise MatchScoringError("ranking candidate match_id values must be unique")

    indexed = list(enumerate(candidates))
    blocked = tuple(
        candidate
        for _, candidate in indexed
        if candidate.eligibility_status is EligibilityStatus.FAIL
    )
    normal = [
        item
        for item in indexed
        if item[1].eligibility_status is not EligibilityStatus.FAIL
    ]
    normal.sort(key=lambda item: (-item[1].total_score, item[0]))

    grouped: list[list[tuple[int, MatchRankingCandidate]]] = []
    group: list[tuple[int, MatchRankingCandidate]] = []
    anchor: Decimal | None = None
    for item in normal:
        if anchor is None or anchor - item[1].total_score <= NEAR_TIE_DISTANCE:
            if anchor is None:
                anchor = item[1].total_score
            group.append(item)
            continue
        grouped.append(group)
        group = [item]
        anchor = item[1].total_score
    if group:
        grouped.append(group)

    ranked: list[RankedMatch] = []
    overall_position = 0
    for group_number, near_tie_group in enumerate(grouped, start=1):
        near_tie_group.sort(key=_ranking_sort_key)
        previous_signature: tuple[Decimal | None, Decimal] | None = None
        previous_rank = 0
        pending: list[tuple[MatchRankingCandidate, int, bool]] = []

        signatures = [
            (candidate.responsibility_score_rate, candidate.confidence_score)
            for _, candidate in near_tie_group
        ]
        for (_, candidate), signature in zip(near_tie_group, signatures, strict=True):
            overall_position += 1
            is_tied = signatures.count(signature) > 1
            if signature != previous_signature:
                previous_rank = overall_position
                previous_signature = signature
            pending.append((candidate, previous_rank, is_tied))

        ranked.extend(
            RankedMatch(
                candidate=candidate,
                rank=rank,
                near_tie_group=group_number,
                is_tied=is_tied,
            )
            for candidate, rank, is_tied in pending
        )

    return MatchRankingResult(ranked=tuple(ranked), blocked=blocked)
