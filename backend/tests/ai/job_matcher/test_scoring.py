"""Deterministic Matcher scoring, confidence, and ranking tests."""

from decimal import Decimal

import pytest

from app.ai.job_matcher import (
    DIMENSION_MAX,
    EVIDENCE_CAP,
    MatcherOutput,
    MatchRankingCandidate,
    MatchScoringError,
    calculate_recommendation_level,
    rank_match_candidates,
    round_score_for_display,
    score_match,
)
from app.ai.job_parser import JobParserOutput
from app.domain.matching import (
    ConfidenceLevel,
    EligibilityStatus,
    EvidenceGrade,
    MatchDimension,
    RecommendationLevel,
)


def build_case(
    requirements: list[tuple[str, str | None, int]],
    assessments: list[tuple[int, str]],
    *,
    gate_statuses: list[str] | None = None,
) -> tuple[JobParserOutput, MatcherOutput]:
    """Build aligned parser and Matcher contracts for scoring tests."""

    parsed_requirements: list[dict[str, object]] = []
    capability_assessments: list[dict[str, object]] = []
    gate_assessments: list[dict[str, object]] = []
    capability_index = 0
    gate_index = 0
    gate_statuses = gate_statuses or []

    for index, (requirement_type, dimension, importance) in enumerate(
        requirements, start=1
    ):
        requirement_key = f"R{index}"
        parsed_requirements.append(
            {
                "requirement_key": requirement_key,
                "requirement_type": requirement_type,
                "dimension": dimension,
                "requirement_text": f"Requirement {index}",
                "source_quote": f"Requirement {index}",
                "importance": importance,
            }
        )
        if requirement_type == "HARD":
            status = gate_statuses[gate_index]
            gate_index += 1
            gate_assessments.append(
                {
                    "requirement_key": requirement_key,
                    "status": status,
                    "reason": "Hard gate assessment",
                    "evidence": [],
                }
            )
            continue

        match_level, evidence_grade = assessments[capability_index]
        capability_index += 1
        capability_assessments.append(
            {
                "requirement_key": requirement_key,
                "match_level": match_level,
                "evidence_grade": evidence_grade,
                "status": "MATCHED" if match_level else "UNKNOWN",
                "reason": "Capability assessment",
                "evidence": [],
            }
        )

    parsed_job = JobParserOutput.model_validate(
        {
            "role_summary": "Test role",
            "responsibilities_summary": [],
            "requirements": parsed_requirements,
            "business_domains": [],
            "tools": [],
            "ambiguous_points": [],
        }
    )
    output = MatcherOutput.model_validate(
        {
            "gate_assessments": gate_assessments,
            "requirement_assessments": capability_assessments,
            "strengths": [],
            "gaps": [],
            "overall_reasoning": "Test result",
        }
    )
    return parsed_job, output


def candidate(
    match_id: str,
    score: str,
    responsibility: str | None,
    confidence: str,
    *,
    eligibility: EligibilityStatus = EligibilityStatus.PASS,
) -> MatchRankingCandidate:
    return MatchRankingCandidate(
        match_id=match_id,
        eligibility_status=eligibility,
        total_score=Decimal(score),
        responsibility_score_rate=(
            Decimal(responsibility) if responsibility is not None else None
        ),
        confidence_score=Decimal(confidence),
    )


def test_scoring_constants_match_the_versioned_specification() -> None:
    assert EVIDENCE_CAP == {
        EvidenceGrade.A: 4,
        EvidenceGrade.B: 3,
        EvidenceGrade.C: 1,
        EvidenceGrade.X: 0,
    }
    assert {
        MatchDimension.RESPONSIBILITY: Decimal("35"),
        MatchDimension.TOOLS_METHODS: Decimal("20"),
        MatchDimension.BUSINESS_DOMAIN: Decimal("15"),
        MatchDimension.OWNERSHIP: Decimal("15"),
        MatchDimension.OUTCOME: Decimal("10"),
        MatchDimension.COMMUNICATION: Decimal("5"),
    } == DIMENSION_MAX


@pytest.mark.parametrize(
    ("grade", "expected_cap", "expected_score", "expected_confidence"),
    [
        ("A", 4, "100.00", "100.00"),
        ("B", 3, "75.00", "100.00"),
        ("C", 1, "25.00", "50.00"),
        ("X", 0, "0.00", "0.00"),
    ],
)
def test_evidence_grade_caps_level_and_controls_coverage(
    grade: str,
    expected_cap: int,
    expected_score: str,
    expected_confidence: str,
) -> None:
    parsed_job, output = build_case(
        [("CORE", "RESPONSIBILITY", 1)],
        [(4, grade)],
    )

    result = score_match(parsed_job, output)

    assert result.requirement_scores[0].evidence_cap == expected_cap
    assert result.requirement_scores[0].effective_level == expected_cap
    assert result.total_score == Decimal(expected_score)
    assert result.confidence_score == Decimal(expected_confidence)


def test_importance_is_normalized_only_within_each_dimension() -> None:
    parsed_job, output = build_case(
        [
            ("CORE", "RESPONSIBILITY", 2),
            ("STANDARD", "RESPONSIBILITY", 1),
        ],
        [(4, "A"), (2, "A")],
    )

    result = score_match(parsed_job, output)

    first, second = result.requirement_scores
    assert first.normalized_requirement_weight == Decimal("0.667")
    assert second.normalized_requirement_weight == Decimal("0.333")
    assert first.weighted_score == Decimal("66.667")
    assert second.weighted_score == Decimal("16.667")
    assert result.total_score == Decimal("83.33")


def test_absent_dimensions_are_na_and_active_weights_are_rebalanced_to_100() -> None:
    parsed_job, output = build_case(
        [
            ("CORE", "RESPONSIBILITY", 1),
            ("STANDARD", "TOOLS_METHODS", 1),
        ],
        [(4, "A"), (4, "A")],
    )

    result = score_match(parsed_job, output)

    assert [item.dimension for item in result.dimension_scores] == [
        MatchDimension.RESPONSIBILITY,
        MatchDimension.TOOLS_METHODS,
    ]
    assert sum(item.max_score for item in result.dimension_scores) == Decimal("100.000")
    assert result.dimension_scores[0].base_max_score == Decimal("35")
    assert result.dimension_scores[0].max_score == Decimal("63.636")
    assert result.dimension_scores[1].max_score == Decimal("36.364")
    assert result.total_score == Decimal("100.00")


def test_all_six_dimensions_keep_their_fixed_base_weights() -> None:
    parsed_job, output = build_case(
        [("CORE", dimension.value, 1) for dimension in MatchDimension],
        [(4, "A") for _ in MatchDimension],
    )

    result = score_match(parsed_job, output)

    assert {item.dimension: item.max_score for item in result.dimension_scores} == {
        dimension: weight.quantize(Decimal("0.001"))
        for dimension, weight in DIMENSION_MAX.items()
    }
    assert result.total_score == Decimal("100.00")


def test_total_uses_rebalanced_dimension_weights_and_full_precision() -> None:
    parsed_job, output = build_case(
        [
            ("CORE", "RESPONSIBILITY", 1),
            ("STANDARD", "TOOLS_METHODS", 1),
        ],
        [(4, "A"), (2, "B")],
    )

    result = score_match(parsed_job, output)

    assert result.dimension_scores[0].raw_score == Decimal("63.636")
    assert result.dimension_scores[1].raw_score == Decimal("18.182")
    assert result.total_score == Decimal("81.82")
    assert result.display_score == 82
    assert result.confidence_score == Decimal("100.00")
    assert result.confidence_level is ConfidenceLevel.HIGH


@pytest.mark.parametrize(
    ("statuses", "eligibility", "recommendation"),
    [
        ([], EligibilityStatus.PASS, RecommendationLevel.PRIORITY),
        (["PASS"], EligibilityStatus.PASS, RecommendationLevel.PRIORITY),
        (["WARN"], EligibilityStatus.WARN, RecommendationLevel.PRIORITY),
        (["PASS", "FAIL"], EligibilityStatus.FAIL, RecommendationLevel.BLOCKED),
        (["WARN", "FAIL"], EligibilityStatus.FAIL, RecommendationLevel.BLOCKED),
    ],
)
def test_hard_gates_determine_eligibility_and_block_failures(
    statuses: list[str],
    eligibility: EligibilityStatus,
    recommendation: RecommendationLevel,
) -> None:
    requirements = [("HARD", None, 1) for _ in statuses]
    requirements.append(("CORE", "RESPONSIBILITY", 1))
    parsed_job, output = build_case(
        requirements,
        [(4, "A")],
        gate_statuses=statuses,
    )

    result = score_match(parsed_job, output)

    assert result.eligibility_status is eligibility
    assert result.recommendation_level is recommendation


def test_unknown_hard_gate_caps_high_confidence_at_medium() -> None:
    parsed_job, output = build_case(
        [("HARD", None, 1), ("CORE", "RESPONSIBILITY", 1)],
        [(4, "A")],
        gate_statuses=["WARN"],
    )

    result = score_match(parsed_job, output)

    assert result.confidence_score == Decimal("100.00")
    assert result.confidence_level is ConfidenceLevel.MEDIUM


def test_mixed_evidence_coverage_produces_medium_confidence() -> None:
    parsed_job, output = build_case(
        [
            ("CORE", "RESPONSIBILITY", 2),
            ("STANDARD", "RESPONSIBILITY", 1),
        ],
        [(4, "A"), (1, "C")],
    )

    result = score_match(parsed_job, output)

    assert result.confidence_score == Decimal("83.33")
    assert result.confidence_level is ConfidenceLevel.MEDIUM


@pytest.mark.parametrize(
    ("score", "display", "level"),
    [
        ("84.49", 84, RecommendationLevel.STRONG),
        ("84.50", 85, RecommendationLevel.PRIORITY),
        ("74.49", 74, RecommendationLevel.SELECTIVE),
        ("74.50", 75, RecommendationLevel.STRONG),
        ("64.49", 64, RecommendationLevel.LOW),
        ("64.50", 65, RecommendationLevel.SELECTIVE),
    ],
)
def test_recommendation_bands_use_the_half_up_display_integer(
    score: str,
    display: int,
    level: RecommendationLevel,
) -> None:
    total_score = Decimal(score)

    assert round_score_for_display(total_score) == display
    assert (
        calculate_recommendation_level(
            total_score=total_score,
            eligibility_status=EligibilityStatus.PASS,
        )
        is level
    )


def test_fail_is_blocked_regardless_of_score() -> None:
    assert (
        calculate_recommendation_level(
            total_score=Decimal("99.99"),
            eligibility_status=EligibilityStatus.FAIL,
        )
        is RecommendationLevel.BLOCKED
    )


@pytest.mark.parametrize("score", [Decimal("-0.01"), Decimal("100.01")])
def test_display_score_rejects_out_of_range_values(score: Decimal) -> None:
    with pytest.raises(MatchScoringError, match="between 0 and 100"):
        round_score_for_display(score)


def test_scoring_rejects_missing_or_duplicate_assessments() -> None:
    parsed_job, output = build_case(
        [
            ("CORE", "RESPONSIBILITY", 1),
            ("STANDARD", "TOOLS_METHODS", 1),
        ],
        [(4, "A"), (4, "A")],
    )
    invalid = output.model_copy(
        update={"requirement_assessments": [output.requirement_assessments[0]]}
    )

    with pytest.raises(MatchScoringError, match="cover every non-HARD"):
        score_match(parsed_job, invalid)


def test_scoring_rejects_a_job_without_capability_requirements() -> None:
    parsed_job, output = build_case(
        [("HARD", None, 1)],
        [],
        gate_statuses=["WARN"],
    )

    with pytest.raises(MatchScoringError, match="at least one non-HARD"):
        score_match(parsed_job, output)


def test_ranking_uses_highest_score_as_each_near_tie_group_anchor() -> None:
    result = rank_match_candidates(
        [
            candidate("a", "90", "70", "70"),
            candidate("b", "88", "80", "60"),
            candidate("c", "86", "99", "99"),
            candidate("d", "85", "60", "60"),
        ]
    )

    assert [item.candidate.match_id for item in result.ranked] == ["b", "a", "c", "d"]
    assert [item.near_tie_group for item in result.ranked] == [1, 1, 2, 2]


def test_near_ties_use_responsibility_then_confidence() -> None:
    result = rank_match_candidates(
        [
            candidate("lower-confidence", "90", "80", "70"),
            candidate("higher-confidence", "88", "80", "90"),
            candidate("no-responsibility", "89", None, "100"),
        ]
    )

    assert [item.candidate.match_id for item in result.ranked] == [
        "higher-confidence",
        "lower-confidence",
        "no-responsibility",
    ]


def test_equal_tie_breakers_share_a_competition_rank() -> None:
    result = rank_match_candidates(
        [
            candidate("a", "90", "80", "70"),
            candidate("b", "88", "80", "70"),
            candidate("c", "87", "70", "70"),
        ]
    )

    assert [item.rank for item in result.ranked] == [1, 1, 3]
    assert [item.is_tied for item in result.ranked] == [True, True, False]


def test_fail_candidates_are_excluded_from_normal_ranking() -> None:
    blocked = candidate(
        "blocked",
        "99",
        "100",
        "100",
        eligibility=EligibilityStatus.FAIL,
    )
    result = rank_match_candidates([blocked, candidate("normal", "50", "50", "50")])

    assert [item.candidate.match_id for item in result.ranked] == ["normal"]
    assert result.blocked == (blocked,)


def test_ranking_rejects_duplicate_match_ids() -> None:
    with pytest.raises(MatchScoringError, match="must be unique"):
        rank_match_candidates(
            [
                candidate("same", "90", "80", "70"),
                candidate("same", "80", "70", "60"),
            ]
        )
