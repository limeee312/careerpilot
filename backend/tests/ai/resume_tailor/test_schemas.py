"""Resume Tailor v1 Pydantic contract tests and shared fixtures."""

import pytest
from pydantic import ValidationError

from app.ai.resume_tailor import (
    RESUME_TAILOR_VERSION,
    ResumeTailorOutput,
    TailorInput,
)
from tests.ai.job_matcher.test_schemas import parsed_job


def tailor_input() -> dict[str, object]:
    return {
        "resume_summary": "关注数据驱动的产品运营。",
        "experiences": [
            {
                "source_id": "exp-1",
                "experience_type": "INTERNSHIP",
                "organization": "示例科技",
                "position": "产品运营实习生",
                "start_date": "2025-06",
                "end_date": "2025-09",
                "description": "负责整理过去三年的翻译需求量和流程耗时数据。",
                "achievements": "分析异常环节并推动流程优化。",
            }
        ],
        "projects": [
            {
                "source_id": "project-1",
                "name": "运营数据周报",
                "role": "产品负责人",
                "description": "设计数据周报 PRD，方案待研发评审。",
                "achievements": "形成自动化质量监控方案并推进研发评审。",
            }
        ],
        "skills": [{"source_id": "skill-1", "skill_name": "Python"}],
        "parsed_job": parsed_job(),
        "match_strengths": ["具有数据分析和流程优化经验"],
        "match_gaps": ["当前材料没有 SQL 使用证据。"],
    }


def tailor_output() -> dict[str, object]:
    return {
        "professional_summary": "具备数据分析与流程优化实践。",
        "experiences": [
            {
                "source_id": "exp-1",
                "include": True,
                "order": 1,
                "bullets": [
                    {
                        "text": (
                            "梳理近三年翻译需求量及全流程耗时数据，定位异常并推动优化。"
                        ),
                        "evidence_refs": [
                            {
                                "source_field": "description",
                                "source_quote": (
                                    "整理过去三年的翻译需求量和流程耗时数据"
                                ),
                            },
                            {
                                "source_field": "achievements",
                                "source_quote": "分析异常环节并推动流程优化",
                            },
                        ],
                    }
                ],
            }
        ],
        "projects": [
            {
                "source_id": "project-1",
                "include": True,
                "order": 1,
                "bullets": [
                    {
                        "text": (
                            "设计数据周报 PRD，形成自动化质量监控方案并推进研发评审。"
                        ),
                        "evidence_refs": [
                            {
                                "source_field": "description",
                                "source_quote": "设计数据周报 PRD",
                            },
                            {
                                "source_field": "achievements",
                                "source_quote": "形成自动化质量监控方案并推进研发评审",
                            },
                        ],
                    }
                ],
            }
        ],
        "skill_order": ["skill-1"],
        "improvement_suggestions": [
            {
                "job_requirement": "熟悉 SQL",
                "current_status": "NO_EVIDENCE",
                "suggestion": "完成真实 SQL 数据分析项目后再补充相关经历。",
                "do_not_claim_yet": True,
            }
        ],
        "warnings": ["SQL 尚无简历证据，不得加入技能列表。"],
    }


def test_resume_tailor_contract_has_a_stable_version() -> None:
    assert RESUME_TAILOR_VERSION == "resume_tailor_v1"


def test_tailor_input_excludes_identity_and_education_fields() -> None:
    value = TailorInput.model_validate(tailor_input())

    assert set(value.model_dump()) == {
        "resume_summary",
        "experiences",
        "projects",
        "skills",
        "parsed_job",
        "match_strengths",
        "match_gaps",
    }


@pytest.mark.parametrize(
    "forbidden_field",
    ["organization", "position", "start_date", "school", "degree"],
)
def test_tailored_output_cannot_modify_immutable_fields(forbidden_field: str) -> None:
    data = tailor_output()
    data["experiences"][0][forbidden_field] = "伪造值"  # type: ignore[index]

    with pytest.raises(ValidationError):
        ResumeTailorOutput.model_validate(data)


@pytest.mark.parametrize(
    "replacement",
    [
        {"include": True, "order": None, "bullets": []},
        {"include": False, "order": 1, "bullets": []},
        {
            "include": False,
            "order": None,
            "bullets": [{"text": "内容", "evidence_refs": []}],
        },
    ],
)
def test_include_flag_controls_order_and_bullets(
    replacement: dict[str, object],
) -> None:
    data = tailor_output()
    data["experiences"][0].update(replacement)  # type: ignore[index]

    with pytest.raises(ValidationError):
        ResumeTailorOutput.model_validate(data)


def test_every_bullet_requires_evidence() -> None:
    data = tailor_output()
    data["experiences"][0]["bullets"][0]["evidence_refs"] = []  # type: ignore[index]

    with pytest.raises(ValidationError):
        ResumeTailorOutput.model_validate(data)


def test_improvement_suggestion_must_remain_future_facing() -> None:
    data = tailor_output()
    data["improvement_suggestions"][0]["do_not_claim_yet"] = False  # type: ignore[index]

    with pytest.raises(ValidationError):
        ResumeTailorOutput.model_validate(data)
