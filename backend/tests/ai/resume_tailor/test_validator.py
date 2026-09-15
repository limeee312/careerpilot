"""Resume Tailor deterministic truth-boundary tests."""

import pytest

from app.ai.errors import AIInvalidOutputError
from app.ai.resume_tailor import (
    ResumeTailorOutput,
    TailorInput,
    validate_resume_tailor_output,
)
from tests.ai.resume_tailor.test_schemas import tailor_input, tailor_output


def valid_input() -> TailorInput:
    return TailorInput.model_validate(tailor_input())


def valid_output() -> ResumeTailorOutput:
    return ResumeTailorOutput.model_validate(tailor_output())


def test_complete_grounded_output_is_accepted() -> None:
    output = valid_output()

    assert validate_resume_tailor_output(valid_input(), output) is output


def test_evidence_comparison_normalizes_unicode_whitespace() -> None:
    data = tailor_output()
    data["experiences"][0]["bullets"][0]["evidence_refs"][0][  # type: ignore[index]
        "source_quote"
    ] = "整理过去三年 的翻译需求量\n和 流程耗时数据"
    output = ResumeTailorOutput.model_validate(data)

    assert validate_resume_tailor_output(valid_input(), output) is output


@pytest.mark.parametrize(
    ("section", "source_id"),
    [("experiences", "exp-missing"), ("projects", "project-missing")],
)
def test_unknown_source_id_is_rejected(section: str, source_id: str) -> None:
    data = tailor_output()
    data[section][0]["source_id"] = source_id  # type: ignore[index]
    output = ResumeTailorOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="unknown source_id"):
        validate_resume_tailor_output(valid_input(), output)


def test_duplicate_source_id_is_rejected() -> None:
    input_data = tailor_input()
    input_data["experiences"].append(  # type: ignore[union-attr]
        {
            **input_data["experiences"][0],  # type: ignore[index]
            "source_id": "exp-2",
        }
    )
    data = tailor_output()
    data["experiences"].append(data["experiences"][0])  # type: ignore[union-attr,index]
    output = ResumeTailorOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="duplicate source_id"):
        validate_resume_tailor_output(TailorInput.model_validate(input_data), output)


def test_included_order_must_be_unique_and_contiguous() -> None:
    input_data = tailor_input()
    input_data["experiences"].append(  # type: ignore[union-attr]
        {
            **input_data["experiences"][0],  # type: ignore[index]
            "source_id": "exp-2",
        }
    )
    data = tailor_output()
    second = {
        **data["experiences"][0],  # type: ignore[index]
        "source_id": "exp-2",
        "order": 3,
    }
    data["experiences"].append(second)  # type: ignore[union-attr]
    output = ResumeTailorOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="unique and contiguous"):
        validate_resume_tailor_output(TailorInput.model_validate(input_data), output)


def test_fabricated_evidence_quote_is_rejected() -> None:
    data = tailor_output()
    data["experiences"][0]["bullets"][0]["evidence_refs"][0][  # type: ignore[index]
        "source_quote"
    ] = "简历中不存在的成果"
    output = ResumeTailorOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="not grounded"):
        validate_resume_tailor_output(valid_input(), output)


def test_fabricated_number_is_rejected() -> None:
    data = tailor_output()
    data["experiences"][0]["bullets"][0][  # type: ignore[index]
        "text"
    ] = "推动流程优化，使效率提升30%。"
    output = ResumeTailorOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="UNSUPPORTED_NUMBER.*30%"):
        validate_resume_tailor_output(valid_input(), output)


def test_skill_order_must_be_an_exact_permutation_of_source_ids() -> None:
    data = tailor_output()
    data["skill_order"] = ["SQL"]
    output = ResumeTailorOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="every input skill"):
        validate_resume_tailor_output(valid_input(), output)


def test_unsupported_target_tool_cannot_be_added_to_a_bullet() -> None:
    data = tailor_output()
    data["experiences"][0]["bullets"][0][  # type: ignore[index]
        "text"
    ] = "使用 SQL 梳理近三年翻译需求量及流程耗时数据。"
    output = ResumeTailorOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="UNSUPPORTED_TOOL.*SQL"):
        validate_resume_tailor_output(valid_input(), output)


def test_participation_cannot_be_escalated_to_independent_ownership() -> None:
    input_data = tailor_input()
    input_data["experiences"][0]["description"] = "参与年度运营活动。"  # type: ignore[index]
    data = tailor_output()
    bullet = data["experiences"][0]["bullets"][0]  # type: ignore[index]
    bullet["text"] = "独立负责年度运营活动。"
    bullet["evidence_refs"] = [
        {"source_field": "description", "source_quote": "参与年度运营活动"}
    ]
    output = ResumeTailorOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="OWNERSHIP_ESCALATION"):
        validate_resume_tailor_output(TailorInput.model_validate(input_data), output)


def test_team_metric_must_remain_attributed_to_the_team() -> None:
    input_data = tailor_input()
    input_data["experiences"][0][  # type: ignore[index]
        "description"
    ] = "参与团队年度活动运营，团队累计触达10万用户。"
    data = tailor_output()
    bullet = data["experiences"][0]["bullets"][0]  # type: ignore[index]
    bullet["text"] = "参与年度活动运营，累计触达10万用户。"
    bullet["evidence_refs"] = [
        {
            "source_field": "description",
            "source_quote": "参与团队年度活动运营，团队累计触达10万用户",
        }
    ]
    output = ResumeTailorOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="TEAM_RESULT_ATTRIBUTION"):
        validate_resume_tailor_output(TailorInput.model_validate(input_data), output)


def test_unrelated_team_sentence_does_not_block_a_grounded_individual_metric() -> None:
    input_data = tailor_input()
    input_data["experiences"][0]["description"] = (  # type: ignore[index]
        "独立分析3项流程问题；参与团队年度活动运营。"
    )
    data = tailor_output()
    bullet = data["experiences"][0]["bullets"][0]  # type: ignore[index]
    bullet["text"] = "独立分析3项流程问题。"
    bullet["evidence_refs"] = [
        {"source_field": "description", "source_quote": "独立分析3项流程问题"}
    ]
    output = ResumeTailorOutput.model_validate(data)

    assert (
        validate_resume_tailor_output(TailorInput.model_validate(input_data), output)
        is output
    )


def test_pending_project_cannot_be_rewritten_as_launched() -> None:
    data = tailor_output()
    bullet = data["projects"][0]["bullets"][0]  # type: ignore[index]
    bullet["text"] = "已上线自动化数据周报系统。"
    bullet["evidence_refs"] = [
        {
            "source_field": "description",
            "source_quote": "设计数据周报 PRD，方案待研发评审",
        }
    ]
    output = ResumeTailorOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="PROJECT_STATE_ESCALATION"):
        validate_resume_tailor_output(valid_input(), output)


def test_improvement_suggestion_must_reference_a_real_requirement() -> None:
    data = tailor_output()
    data["improvement_suggestions"][0][  # type: ignore[index]
        "job_requirement"
    ] = "不存在的岗位要求"
    output = ResumeTailorOutput.model_validate(data)

    with pytest.raises(AIInvalidOutputError, match="unknown job requirement"):
        validate_resume_tailor_output(valid_input(), output)
