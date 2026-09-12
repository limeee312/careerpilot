"""Resume-Job Matcher coverage and evidence-grounding tests."""

import pytest

from app.ai.errors import AIInvalidOutputError
from app.ai.job_matcher import MatcherInput, MatcherOutput, validate_matcher_output
from tests.ai.job_matcher.test_schemas import matcher_input, matcher_output


def valid_input() -> MatcherInput:
    return MatcherInput.model_validate(matcher_input())


def valid_output() -> MatcherOutput:
    return MatcherOutput.model_validate(matcher_output())


def test_complete_grounded_output_is_accepted() -> None:
    output = valid_output()

    assert validate_matcher_output(valid_input(), output) is output


def test_evidence_comparison_normalizes_unicode_whitespace() -> None:
    data = matcher_output()
    data["requirement_assessments"][0]["evidence"][0][  # type: ignore[index]
        "source_quote"
    ] = "定位异常\n并 推动优化"
    output = MatcherOutput.model_validate(data)

    assert validate_matcher_output(valid_input(), output) is output


@pytest.mark.parametrize(
    ("collection", "replacement"),
    [
        ("gate_assessments", []),
        (
            "gate_assessments",
            [
                {
                    "requirement_key": "R2",
                    "status": "WARN",
                    "reason": "错误地评估了非 Hard 要求。",
                    "evidence": [],
                }
            ],
        ),
        (
            "requirement_assessments",
            [
                {
                    "requirement_key": "R2",
                    "match_level": 0,
                    "evidence_grade": "X",
                    "status": "UNKNOWN",
                    "reason": "重复评估。",
                    "evidence": [],
                },
                {
                    "requirement_key": "R2",
                    "match_level": 0,
                    "evidence_grade": "X",
                    "status": "UNKNOWN",
                    "reason": "重复评估。",
                    "evidence": [],
                },
            ],
        ),
    ],
)
def test_every_requirement_must_be_assessed_once_in_the_correct_collection(
    collection: str,
    replacement: list[dict[str, object]],
) -> None:
    data = matcher_output()
    data[collection] = replacement
    output = MatcherOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="exactly once"):
        validate_matcher_output(valid_input(), output)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_id", "exp-does-not-exist"),
        ("source_type", "project"),
        ("source_quote", "简历中不存在的成果"),
    ],
)
def test_fabricated_or_misattributed_evidence_is_rejected(
    field: str,
    value: str,
) -> None:
    data = matcher_output()
    evidence = data["requirement_assessments"][0]["evidence"][0]  # type: ignore[index]
    evidence[field] = value
    output = MatcherOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="not grounded") as error:
        validate_matcher_output(valid_input(), output)

    assert error.value.code == "AI_INVALID_OUTPUT"


@pytest.mark.parametrize("status", ["PASS", "FAIL"])
def test_conclusive_gate_status_requires_grounded_evidence(status: str) -> None:
    data = matcher_output()
    data["gate_assessments"][0]["status"] = status  # type: ignore[index]
    data["gate_assessments"][0]["evidence"] = []  # type: ignore[index]
    output = MatcherOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="requires evidence"):
        validate_matcher_output(valid_input(), output)


def test_warn_gate_may_have_no_evidence() -> None:
    data = matcher_output()
    data["gate_assessments"][0]["status"] = "WARN"  # type: ignore[index]
    data["gate_assessments"][0]["evidence"] = []  # type: ignore[index]
    output = MatcherOutput.model_validate(data)

    assert validate_matcher_output(valid_input(), output) is output


@pytest.mark.parametrize("evidence_grade", ["A", "B", "C"])
def test_supported_evidence_grades_require_a_resume_quote(
    evidence_grade: str,
) -> None:
    data = matcher_output()
    assessment = data["requirement_assessments"][0]  # type: ignore[index]
    assessment["evidence_grade"] = evidence_grade
    assessment["evidence"] = []
    output = MatcherOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="grade requires evidence"):
        validate_matcher_output(valid_input(), output)


def test_x_grade_may_have_no_evidence() -> None:
    output = valid_output()

    assert output.requirement_assessments[1].evidence == []
    assert validate_matcher_output(valid_input(), output) is output


def test_gap_must_reference_a_parsed_requirement() -> None:
    data = matcher_output()
    data["gaps"][0]["requirement_key"] = "R9"  # type: ignore[index]
    output = MatcherOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="unknown requirement R9"):
        validate_matcher_output(valid_input(), output)
