"""Resume-Job Matcher v1 Pydantic contract tests."""

import pytest
from pydantic import ValidationError

from app.ai.job_matcher import (
    JOB_MATCHER_VERSION,
    AssessmentStatus,
    EligibilityStatus,
    EvidenceGrade,
    MatcherInput,
    MatcherOutput,
    MatchLevel,
)


def parsed_job() -> dict[str, object]:
    return {
        "role_summary": "负责用户运营、数据分析和跨团队项目推进。",
        "responsibilities_summary": ["制定用户运营策略", "分析用户行为数据"],
        "requirements": [
            {
                "requirement_key": "R1",
                "requirement_type": "HARD",
                "dimension": None,
                "requirement_text": "本科及以上学历",
                "source_quote": "本科及以上学历",
                "importance": 1,
            },
            {
                "requirement_key": "R2",
                "requirement_type": "CORE",
                "dimension": "RESPONSIBILITY",
                "requirement_text": "分析用户行为并推动优化",
                "source_quote": "通过用户行为数据分析发现问题并推动产品优化",
                "importance": 2,
            },
            {
                "requirement_key": "R3",
                "requirement_type": "PREFERRED",
                "dimension": "TOOLS_METHODS",
                "requirement_text": "熟悉 SQL",
                "source_quote": "熟悉SQL优先",
                "importance": 1,
            },
        ],
        "business_domains": ["用户运营"],
        "tools": ["SQL"],
        "ambiguous_points": [],
    }


def matcher_input() -> dict[str, object]:
    return {
        "parsed_job": parsed_job(),
        "resume_evidence": [
            {
                "source_type": "education",
                "source_id": "edu-1",
                "content": "华东大学管理学本科，2027年6月毕业。",
            },
            {
                "source_type": "experience",
                "source_id": "exp-1",
                "content": "梳理近三年业务需求及全流程耗时数据，定位异常并推动优化。",
            },
            {
                "source_type": "skill",
                "source_id": "skill-1",
                "content": "Python",
            },
            {
                "source_type": "summary",
                "source_id": None,
                "content": "关注数据驱动的运营工作。",
            },
        ],
    }


def matcher_output() -> dict[str, object]:
    return {
        "gate_assessments": [
            {
                "requirement_key": "R1",
                "status": "PASS",
                "reason": "简历明确包含本科学历。",
                "evidence": [
                    {
                        "source_type": "education",
                        "source_id": "edu-1",
                        "source_quote": "管理学本科",
                    }
                ],
            }
        ],
        "requirement_assessments": [
            {
                "requirement_key": "R2",
                "match_level": 3,
                "evidence_grade": "B",
                "status": "MATCHED",
                "reason": "存在直接的数据分析和优化经验。",
                "evidence": [
                    {
                        "source_type": "experience",
                        "source_id": "exp-1",
                        "source_quote": "定位异常并推动优化",
                    }
                ],
            },
            {
                "requirement_key": "R3",
                "match_level": 0,
                "evidence_grade": "X",
                "status": "UNKNOWN",
                "reason": "当前简历未提供 SQL 证据。",
                "evidence": [],
            },
        ],
        "strengths": ["具有数据分析和流程优化经验"],
        "gaps": [
            {
                "requirement_key": "R3",
                "importance": "LOW",
                "gap": "当前材料没有 SQL 使用证据。",
                "improvement_direction": "补充真实 SQL 项目或工作案例。",
            }
        ],
        "overall_reasoning": "核心职责有直接证据，SQL 偏好项仍待确认。",
    }


def test_matcher_contract_has_a_stable_version() -> None:
    assert JOB_MATCHER_VERSION == "job_matcher_v1"


def test_matcher_input_contains_only_parsed_job_and_redacted_evidence() -> None:
    value = MatcherInput.model_validate(matcher_input())

    assert value.resume_evidence[0].content.startswith("华东大学")
    assert value.resume_evidence[-1].source_id is None
    assert set(value.model_dump()) == {"parsed_job", "resume_evidence"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_type", "certificate"),
        ("source_id", " "),
        ("content", " "),
    ],
)
def test_resume_evidence_rejects_invalid_source_fields(field: str, value: str) -> None:
    data = matcher_input()
    data["resume_evidence"][0][field] = value  # type: ignore[index]

    with pytest.raises(ValidationError):
        MatcherInput.model_validate(data)


def test_matcher_input_rejects_career_preferences_and_personal_context() -> None:
    data = matcher_input()
    data["career_preferences"] = {"preferred_city": "上海"}

    with pytest.raises(ValidationError):
        MatcherInput.model_validate(data)


def test_matcher_output_uses_shared_domain_enums() -> None:
    output = MatcherOutput.model_validate(matcher_output())

    assert output.gate_assessments[0].status is EligibilityStatus.PASS
    assessment = output.requirement_assessments[0]
    assert assessment.match_level is MatchLevel.DIRECT_PARTIAL
    assert assessment.evidence_grade is EvidenceGrade.B
    assert assessment.status is AssessmentStatus.MATCHED


@pytest.mark.parametrize("match_level", [-1, 5, "DIRECT_STRONG"])
def test_match_level_accepts_only_integer_values_zero_through_four(
    match_level: object,
) -> None:
    data = matcher_output()
    data["requirement_assessments"][0]["match_level"] = match_level  # type: ignore[index]

    with pytest.raises(ValidationError):
        MatcherOutput.model_validate(data)


@pytest.mark.parametrize("forbidden_field", ["total_score", "recommendation_level"])
def test_matcher_output_rejects_backend_owned_fields(forbidden_field: str) -> None:
    data = matcher_output()
    data[forbidden_field] = 90 if forbidden_field == "total_score" else "PRIORITY"

    with pytest.raises(ValidationError):
        MatcherOutput.model_validate(data)


@pytest.mark.parametrize(
    "evidence",
    [
        {"source_type": "education", "source_id": "edu-1", "source_quote": None},
        {"source_type": None, "source_id": "edu-1", "source_quote": None},
        {"source_type": None, "source_id": None, "source_quote": "管理学本科"},
    ],
)
def test_gate_evidence_requires_a_coherent_nullable_tuple(
    evidence: dict[str, object],
) -> None:
    data = matcher_output()
    data["gate_assessments"][0]["evidence"] = [evidence]  # type: ignore[index]

    with pytest.raises(ValidationError):
        MatcherOutput.model_validate(data)


def test_gate_evidence_allows_an_explicit_no_evidence_placeholder() -> None:
    data = matcher_output()
    data["gate_assessments"][0] = {  # type: ignore[index]
        "requirement_key": "R1",
        "status": "WARN",
        "reason": "当前信息不足。",
        "evidence": [{"source_type": None, "source_id": None, "source_quote": None}],
    }

    output = MatcherOutput.model_validate(data)

    assert output.gate_assessments[0].evidence[0].source_quote is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("gate_assessments", None),
        ("requirement_assessments", None),
        ("strengths", None),
        ("gaps", None),
        ("overall_reasoning", " "),
    ],
)
def test_matcher_output_rejects_null_arrays_and_blank_reasoning(
    field: str, value: object
) -> None:
    data = matcher_output()
    data[field] = value

    with pytest.raises(ValidationError):
        MatcherOutput.model_validate(data)
