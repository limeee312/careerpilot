"""Regression checks for the versioned Resume Tailor prompt."""

from app.ai.resume_tailor.constants import RESUME_TAILOR_VERSION
from app.ai.resume_tailor.prompt import RESUME_TAILOR_PROMPT_V1


def test_resume_tailor_prompt_is_loaded_and_versioned() -> None:
    assert RESUME_TAILOR_VERSION == "resume_tailor_v1"
    assert RESUME_TAILOR_PROMPT_V1.startswith("你是 CareerPilot")


def test_resume_tailor_prompt_preserves_critical_truth_boundaries() -> None:
    required_rules = (
        "你不是经历生成器",
        "不得创造新公司、职位、项目、学校、学历、技能或工具",
        "不得创造数字、百分比、用户量、收入、效率提升或成果规模",
        "不得把团队成果改写成候选人的个人成果",
        "不得把参与、协助改写成独立负责、主导或牵头",
        "不得把提案、原型、试运行或待评审方案改写成已正式上线",
        "每一个生成 Bullet 都必须至少提供一个 evidence_ref",
        "skill_order 必须且只能包含输入中的全部 Skill source_id",
        "只能放入 improvement_suggestions",
    )

    for rule in required_rules:
        assert rule in RESUME_TAILOR_PROMPT_V1
