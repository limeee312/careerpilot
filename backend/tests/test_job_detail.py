"""Job match detail serialization tests without a database."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.domain.matching import (
    AssessmentStatus,
    ConfidenceLevel,
    EligibilityStatus,
    EvidenceGrade,
    MatchDimension,
    RecommendationLevel,
    RequirementType,
)
from app.models.job import Job
from app.models.matching import (
    AIStatus,
    JobMatchResult,
    JobParseResult,
    JobRequirement,
    MatchDimensionScore,
    MatchGateCheck,
    MatchRequirementAssessment,
)
from app.services.job_detail import serialize_job_match_detail

NOW = datetime(2026, 9, 14, 11, tzinfo=UTC)


def build_detail_graph() -> tuple[Job, JobMatchResult]:
    user_id = uuid4()
    job_id = uuid4()
    parse_id = uuid4()
    hard_requirement = JobRequirement(
        id=uuid4(),
        job_parse_result_id=parse_id,
        requirement_type=RequirementType.HARD,
        dimension=None,
        requirement_text="本科及以上学历",
        source_quote="本科及以上学历",
        importance=1,
        sort_order=1,
        created_at=NOW,
    )
    core_requirement = JobRequirement(
        id=uuid4(),
        job_parse_result_id=parse_id,
        requirement_type=RequirementType.CORE,
        dimension=MatchDimension.RESPONSIBILITY,
        requirement_text="分析用户行为并推动策略优化",
        source_quote="分析用户行为并推动策略优化",
        importance=2,
        sort_order=2,
        created_at=NOW,
    )
    parse_result = JobParseResult(
        id=parse_id,
        job_id=job_id,
        status=AIStatus.SUCCESS,
        summary="负责数据驱动的用户运营。",
        prompt_version="job_parser_v1",
        model="test-model",
        created_at=NOW,
        requirements=[hard_requirement, core_requirement],
    )
    gate = MatchGateCheck(
        id=uuid4(),
        job_requirement_id=hard_requirement.id,
        requirement=hard_requirement,
        status=EligibilityStatus.WARN,
        reason="当前简历未明确学历层次。",
        resume_evidence=[],
        created_at=NOW,
    )
    assessment = MatchRequirementAssessment(
        id=uuid4(),
        job_requirement_id=core_requirement.id,
        requirement=core_requirement,
        match_level=3,
        evidence_grade=EvidenceGrade.A,
        evidence_cap=4,
        weighted_score=Decimal("75.000"),
        assessment_status=AssessmentStatus.MATCHED,
        reason="存在直接的数据分析和优化经验。",
        resume_evidence=[
            {
                "source_type": "experience",
                "source_id": str(uuid4()),
                "source_quote": "分析用户行为数据并推动运营优化",
            }
        ],
        created_at=NOW,
    )
    dimension = MatchDimensionScore(
        id=uuid4(),
        dimension=MatchDimension.RESPONSIBILITY,
        raw_score=Decimal("75.000"),
        max_score=Decimal("100.000"),
        normalized_score=Decimal("75.000"),
        created_at=NOW,
    )
    result = JobMatchResult(
        id=uuid4(),
        user_id=user_id,
        job_id=job_id,
        resume_master_id=uuid4(),
        job_parse_result_id=parse_id,
        eligibility_status=EligibilityStatus.WARN,
        total_score=Decimal("74.50"),
        confidence_score=Decimal("72.50"),
        confidence_level=ConfidenceLevel.MEDIUM,
        recommendation_level=RecommendationLevel.STRONG,
        recommendation="匹配较强",
        strengths=["用户数据分析有直接成果证据"],
        gaps=[
            {
                "requirement_key": "R1",
                "importance": "HIGH",
                "gap": "学历信息未明确",
                "improvement_direction": "补充最高学历信息",
            }
        ],
        resume_snapshot={},
        job_snapshot={},
        prompt_version="job_matcher_v1",
        model="test-model",
        created_at=NOW,
        gate_checks=[gate],
        requirement_assessments=[assessment],
        dimension_scores=[dimension],
    )
    job = Job(
        id=job_id,
        batch_id=uuid4(),
        user_id=user_id,
        company_name="示例科技",
        title="产品运营",
        location="杭州",
        department="用户增长",
        source_url="https://example.com/jobs/1",
        raw_jd="测试岗位描述" * 20,
        created_at=NOW,
        updated_at=NOW,
        parse_results=[parse_result],
        match_results=[result],
    )
    return job, result


def test_detail_serialization_keeps_scores_requirements_and_evidence() -> None:
    job, result = build_detail_graph()

    data = serialize_job_match_detail(job, result)

    assert data.job_id == job.id
    assert data.display_score == 75
    assert data.eligibility_status is EligibilityStatus.WARN
    assert data.role_summary == "负责数据驱动的用户运营。"
    assert data.strengths == ["用户数据分析有直接成果证据"]
    assert data.gaps[0].improvement_direction == "补充最高学历信息"
    assert data.hard_gates[0].requirement.requirement_key == "R1"
    assert data.hard_gates[0].status is EligibilityStatus.WARN
    assert data.requirement_assessments[0].requirement.requirement_key == "R2"
    assert data.requirement_assessments[0].evidence[0].source_type == "experience"
    assert data.dimension_scores[0].normalized_score == Decimal("75.000")


def test_detail_serialization_orders_assessments_by_requirement() -> None:
    job, result = build_detail_graph()
    first = result.requirement_assessments[0]
    later_requirement = JobRequirement(
        id=uuid4(),
        job_parse_result_id=result.job_parse_result_id,
        requirement_type=RequirementType.PREFERRED,
        dimension=MatchDimension.TOOLS_METHODS,
        requirement_text="熟悉 SQL 优先",
        source_quote="熟悉 SQL 优先",
        importance=1,
        sort_order=3,
        created_at=NOW,
    )
    later = MatchRequirementAssessment(
        id=uuid4(),
        job_requirement_id=later_requirement.id,
        requirement=later_requirement,
        match_level=0,
        evidence_grade=EvidenceGrade.X,
        evidence_cap=0,
        weighted_score=Decimal("0.000"),
        assessment_status=AssessmentStatus.UNKNOWN,
        reason="当前简历没有 SQL 证据。",
        resume_evidence=[],
        created_at=NOW,
    )
    result.requirement_assessments = [later, first]

    data = serialize_job_match_detail(job, result)

    assert [
        item.requirement.requirement_key for item in data.requirement_assessments
    ] == [
        "R2",
        "R3",
    ]
