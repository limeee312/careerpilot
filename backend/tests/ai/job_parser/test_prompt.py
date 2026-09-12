"""Regression checks for the versioned Job Parser system prompt."""

from app.ai.job_parser.constants import JOB_PARSER_VERSION
from app.ai.job_parser.prompt import JOB_PARSER_PROMPT_V1


def test_job_parser_prompt_is_loaded_and_versioned() -> None:
    assert JOB_PARSER_VERSION == "job_parser_v1"
    assert JOB_PARSER_PROMPT_V1.startswith("你是 CareerPilot")


def test_job_parser_prompt_preserves_critical_product_boundaries() -> None:
    required_rules = (
        "只依据输入 JD",
        "不要读取或评价任何候选人简历",
        "不要进行职位匹配",
        "不得标记为 HARD",
        "dimension 必须为 null",
        "source_quote 必须来自输入 JD",
        "不要计算最终分数",
    )

    for rule in required_rules:
        assert rule in JOB_PARSER_PROMPT_V1
