"""Job Parser v1 Pydantic contract tests."""

import pytest
from pydantic import ValidationError

from app.ai.job_parser import JOB_PARSER_VERSION
from app.ai.job_parser.schemas import (
    JobParserInput,
    JobParserOutput,
    MatchDimension,
    RequirementType,
)

RAW_JD = """岗位：产品运营

职责：
1. 负责产品用户运营策略制定与执行；
2. 通过用户行为数据分析发现问题并推动产品优化；
3. 联动产品、研发和市场团队推进运营项目落地。

要求：
1. 本科及以上学历；
2. 具备良好的数据分析能力；
3. 熟悉SQL优先。
"""


def parser_input() -> dict[str, object]:
    return {
        "company_name": "  示例科技  ",
        "title": "  产品运营  ",
        "location": " ",
        "raw_jd": RAW_JD,
    }


def parser_output() -> dict[str, object]:
    return {
        "role_summary": "负责用户运营策略、数据分析和跨团队项目推进。",
        "responsibilities_summary": [
            "制定并执行用户运营策略",
            "分析用户行为数据并推动产品优化",
        ],
        "requirements": [
            {
                "requirement_key": "R1",
                "requirement_type": "CORE",
                "dimension": "RESPONSIBILITY",
                "requirement_text": "负责用户运营策略制定与执行",
                "source_quote": "负责产品用户运营策略制定与执行",
                "importance": 2,
            },
            {
                "requirement_key": "R2",
                "requirement_type": "HARD",
                "dimension": None,
                "requirement_text": "本科及以上学历",
                "source_quote": "本科及以上学历",
                "importance": 1,
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


def test_parser_contract_has_a_stable_version() -> None:
    assert JOB_PARSER_VERSION == "job_parser_v1"


def test_parser_input_normalizes_job_fields_without_resume_context() -> None:
    value = JobParserInput.model_validate(parser_input())

    assert value.company_name == "示例科技"
    assert value.title == "产品运营"
    assert value.location is None
    assert value.raw_jd.startswith("岗位：产品运营")
    assert set(value.model_dump()) == {
        "company_name",
        "title",
        "location",
        "raw_jd",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("company_name", " "),
        ("title", " "),
        ("raw_jd", "职位描述过短"),
    ],
)
def test_parser_input_rejects_missing_or_short_job_facts(
    field: str, value: str
) -> None:
    data = parser_input()
    data[field] = value

    with pytest.raises(ValidationError):
        JobParserInput.model_validate(data)


def test_parser_input_rejects_unknown_context() -> None:
    data = parser_input()
    data["resume"] = {"name": "不应发送给 Parser"}

    with pytest.raises(ValidationError):
        JobParserInput.model_validate(data)


def test_parser_output_accepts_atomic_requirements_and_enums() -> None:
    output = JobParserOutput.model_validate(parser_output())

    assert output.requirements[0].requirement_type is RequirementType.CORE
    assert output.requirements[0].dimension is MatchDimension.RESPONSIBILITY
    assert output.requirements[1].dimension is None
    assert output.requirements[2].requirement_type is RequirementType.PREFERRED


@pytest.mark.parametrize(
    ("requirement_type", "dimension"),
    [
        ("HARD", "COMMUNICATION"),
        ("CORE", None),
        ("STANDARD", None),
        ("PREFERRED", None),
    ],
)
def test_requirement_type_enforces_dimension_contract(
    requirement_type: str,
    dimension: str | None,
) -> None:
    data = parser_output()
    requirement = data["requirements"][0]  # type: ignore[index]
    requirement["requirement_type"] = requirement_type
    requirement["dimension"] = dimension

    with pytest.raises(ValidationError):
        JobParserOutput.model_validate(data)


@pytest.mark.parametrize(
    "keys",
    [
        ["R1", "R1", "R3"],
        ["R2", "R1", "R3"],
        ["R1", "R3", "R4"],
        ["requirement-1", "R2", "R3"],
    ],
)
def test_parser_output_requires_unique_sequential_keys(keys: list[str]) -> None:
    data = parser_output()
    for requirement, key in zip(data["requirements"], keys, strict=True):  # type: ignore[arg-type]
        requirement["requirement_key"] = key

    with pytest.raises(ValidationError):
        JobParserOutput.model_validate(data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("responsibilities_summary", None),
        ("business_domains", None),
        ("tools", None),
        ("ambiguous_points", None),
    ],
)
def test_parser_output_arrays_cannot_be_null(field: str, value: None) -> None:
    data = parser_output()
    data[field] = value

    with pytest.raises(ValidationError):
        JobParserOutput.model_validate(data)


def test_parser_output_rejects_invalid_importance_and_extra_fields() -> None:
    invalid_importance = parser_output()
    invalid_importance["requirements"][0]["importance"] = 3  # type: ignore[index]
    extra_field = parser_output()
    extra_field["total_score"] = 95

    with pytest.raises(ValidationError):
        JobParserOutput.model_validate(invalid_importance)
    with pytest.raises(ValidationError):
        JobParserOutput.model_validate(extra_field)
