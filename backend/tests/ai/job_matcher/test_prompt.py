"""Regression checks for the versioned Resume-Job Matcher prompt."""

from app.ai.job_matcher.constants import JOB_MATCHER_VERSION
from app.ai.job_matcher.prompt import JOB_MATCHER_PROMPT_V1


def test_job_matcher_prompt_is_loaded_and_versioned() -> None:
    assert JOB_MATCHER_VERSION == "job_matcher_v1"
    assert JOB_MATCHER_PROMPT_V1.startswith("你是 CareerPilot")


def test_job_matcher_prompt_preserves_critical_product_boundaries() -> None:
    required_rules = (
        "所有判断必须来自提供的简历内容",
        "“简历没有写”与“已确认不会”必须区分",
        "Hard Gate 与能力匹配完全分离",
        "不允许把相邻技能直接视为等价技能",
        "PASS 和 FAIL 必须引用明确的简历证据",
        "source_type 和 source_id 必须与输入中的同一条 Evidence 对应",
        "每个 HARD Requirement 必须且只能",
        "不要计算或输出最终分数",
        "不要输出推荐等级、岗位排名或录用概率",
    )

    for rule in required_rules:
        assert rule in JOB_MATCHER_PROMPT_V1
