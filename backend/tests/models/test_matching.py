"""Job parsing and match result ORM contract tests."""

from decimal import Decimal

from sqlalchemy import Enum, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.ai.job_parser.schemas import MatchDimension, RequirementType
from app.models.job import Job
from app.models.matching import (
    AIStatus,
    AssessmentStatus,
    ConfidenceLevel,
    EligibilityStatus,
    EvidenceGrade,
    JobMatchResult,
    JobParseResult,
    JobRequirement,
    MatchDimensionScore,
    MatchGateCheck,
    MatchRequirementAssessment,
    RecommendationLevel,
)


def constraint_names(model: type) -> set[str | None]:
    return {constraint.name for constraint in model.__table__.constraints}


def assert_created_only(model: type) -> None:
    columns = model.__table__.columns

    assert columns.id.primary_key
    assert columns.id.default is not None
    assert columns.id.default.is_callable
    assert columns.created_at.type.timezone
    assert columns.created_at.server_default is not None
    assert "updated_at" not in columns


def test_match_enums_follow_the_final_database_baseline() -> None:
    assert [item.value for item in AIStatus] == [
        "PENDING",
        "PROCESSING",
        "SUCCESS",
        "FAILED",
    ]
    assert [item.value for item in MatchDimension] == [
        "RESPONSIBILITY",
        "TOOLS_METHODS",
        "BUSINESS_DOMAIN",
        "OWNERSHIP",
        "OUTCOME",
        "COMMUNICATION",
    ]
    assert [item.value for item in EligibilityStatus] == ["PASS", "WARN", "FAIL"]
    assert [item.value for item in EvidenceGrade] == ["A", "B", "C", "X"]
    assert [item.value for item in AssessmentStatus] == [
        "MATCHED",
        "PARTIAL",
        "CONFIRMED_GAP",
        "UNKNOWN",
    ]
    assert [item.value for item in ConfidenceLevel] == ["HIGH", "MEDIUM", "LOW"]
    assert [item.value for item in RecommendationLevel] == [
        "BLOCKED",
        "PRIORITY",
        "STRONG",
        "SELECTIVE",
        "LOW",
    ]


def test_job_parse_result_is_versioned_and_traceable() -> None:
    columns = JobParseResult.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "job_id",
        "ai_run_id",
        "status",
        "summary",
        "prompt_version",
        "model",
        "error_code",
        "created_at",
    }
    assert_created_only(JobParseResult)
    job_foreign_key = next(iter(columns.job_id.foreign_keys))
    assert job_foreign_key.target_fullname == "jobs.id"
    assert job_foreign_key.ondelete == "CASCADE"
    assert not columns.job_id.nullable
    assert columns.ai_run_id.nullable
    assert not columns.ai_run_id.foreign_keys
    assert isinstance(columns.status.type, Enum)
    assert columns.status.type.name == "ai_status"
    assert columns.status.type.enums == [item.value for item in AIStatus]
    assert columns.status.server_default is not None
    assert isinstance(columns.summary.type, Text)
    assert columns.summary.nullable
    assert isinstance(columns.prompt_version.type, String)
    assert columns.prompt_version.type.length == 50
    assert isinstance(columns.model.type, String)
    assert columns.model.type.length == 100
    assert isinstance(columns.error_code.type, String)
    assert columns.error_code.type.length == 100
    assert "job_parse_results_id_job_id_key" in constraint_names(JobParseResult)

    indexes = {index.name: index for index in JobParseResult.__table__.indexes}
    assert set(indexes) == {"job_parse_results_job_created_idx"}
    index = indexes["job_parse_results_job_created_idx"]
    assert index.expressions[0].name == "job_id"
    assert index.expressions[1].element.name == "created_at"
    assert index.expressions[1].modifier.__name__ == "desc_op"


def test_job_requirement_preserves_atomic_source_grounding() -> None:
    columns = JobRequirement.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "job_parse_result_id",
        "requirement_type",
        "dimension",
        "requirement_text",
        "source_quote",
        "importance",
        "sort_order",
        "created_at",
    }
    assert_created_only(JobRequirement)
    assert isinstance(columns.requirement_type.type, Enum)
    assert columns.requirement_type.type.name == "requirement_type"
    assert columns.requirement_type.type.enums == [
        item.value for item in RequirementType
    ]
    assert isinstance(columns.dimension.type, Enum)
    assert columns.dimension.type.name == "match_dimension"
    assert columns.dimension.type.enums == [item.value for item in MatchDimension]
    assert columns.dimension.nullable
    assert isinstance(columns.requirement_text.type, Text)
    assert isinstance(columns.source_quote.type, Text)
    assert {
        "job_requirements_dimension_contract_ck",
        "job_requirements_importance_ck",
        "job_requirements_sort_order_positive_ck",
        "job_requirements_parse_sort_key",
    }.issubset(constraint_names(JobRequirement))
    assert {index.name for index in JobRequirement.__table__.indexes} == {
        "job_requirements_parse_result_id_idx"
    }

    requirement = JobRequirement(
        requirement_type=RequirementType.CORE,
        dimension=MatchDimension.RESPONSIBILITY,
        requirement_text="负责用户运营策略制定",
        source_quote="负责用户运营策略制定",
        importance=2,
        sort_order=3,
    )
    assert requirement.requirement_key == "R3"


def test_match_result_keeps_scores_snapshots_and_provider_trace() -> None:
    columns = JobMatchResult.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "user_id",
        "job_id",
        "resume_master_id",
        "job_parse_result_id",
        "ai_run_id",
        "eligibility_status",
        "total_score",
        "confidence_score",
        "confidence_level",
        "recommendation_level",
        "recommendation",
        "strengths",
        "gaps",
        "resume_snapshot",
        "job_snapshot",
        "prompt_version",
        "model",
        "created_at",
    }
    assert_created_only(JobMatchResult)
    assert isinstance(columns.total_score.type, Numeric)
    assert columns.total_score.type.precision == 5
    assert columns.total_score.type.scale == 2
    assert columns.total_score.type.python_type is Decimal
    assert isinstance(columns.confidence_score.type, Numeric)
    assert isinstance(columns.eligibility_status.type, Enum)
    assert columns.eligibility_status.type.name == "eligibility_status"
    assert isinstance(columns.confidence_level.type, Enum)
    assert columns.confidence_level.type.native is False
    assert isinstance(columns.recommendation_level.type, Enum)
    assert columns.recommendation_level.type.native is False
    assert isinstance(columns.recommendation.type, Text)
    for json_column in ("strengths", "gaps", "resume_snapshot", "job_snapshot"):
        assert isinstance(columns[json_column].type, JSONB)
        assert not columns[json_column].nullable
    assert columns.strengths.server_default is not None
    assert columns.gaps.server_default is not None
    assert columns.ai_run_id.nullable
    assert not columns.ai_run_id.foreign_keys

    assert {
        "job_match_results_total_score_range_ck",
        "job_match_results_confidence_score_range_ck",
        "job_match_results_job_owner_fkey",
        "job_match_results_resume_owner_fkey",
        "job_match_results_parse_job_fkey",
    }.issubset(constraint_names(JobMatchResult))

    indexes = {index.name: index for index in JobMatchResult.__table__.indexes}
    assert set(indexes) == {
        "job_match_results_job_created_idx",
        "job_match_results_user_created_idx",
    }


def test_match_child_rows_enforce_one_assessment_per_requirement() -> None:
    gate_columns = MatchGateCheck.__table__.columns
    assessment_columns = MatchRequirementAssessment.__table__.columns
    dimension_columns = MatchDimensionScore.__table__.columns

    for model in (
        MatchGateCheck,
        MatchRequirementAssessment,
        MatchDimensionScore,
    ):
        assert_created_only(model)

    assert isinstance(gate_columns.resume_evidence.type, JSONB)
    assert isinstance(gate_columns.status.type, Enum)
    assert "match_gate_checks_result_requirement_key" in constraint_names(
        MatchGateCheck
    )

    assert isinstance(assessment_columns.evidence_grade.type, Enum)
    assert assessment_columns.evidence_grade.type.name == "evidence_grade"
    assert isinstance(assessment_columns.assessment_status.type, Enum)
    assert assessment_columns.assessment_status.type.native is False
    assert isinstance(assessment_columns.weighted_score.type, Numeric)
    assert {
        "match_requirement_assessments_match_level_range_ck",
        "match_requirement_assessments_evidence_cap_range_ck",
        "match_requirement_assessments_weighted_score_nonnegative_ck",
        "match_requirement_assessments_result_requirement_key",
    }.issubset(constraint_names(MatchRequirementAssessment))

    assert isinstance(dimension_columns.dimension.type, Enum)
    assert dimension_columns.dimension.type.name == "match_dimension"
    assert {
        "match_dimension_scores_raw_score_range_ck",
        "match_dimension_scores_max_score_positive_ck",
        "match_dimension_scores_normalized_score_range_ck",
        "match_dimension_scores_result_dimension_key",
    }.issubset(constraint_names(MatchDimensionScore))


def test_match_relationships_own_only_their_immutable_children() -> None:
    assert "delete-orphan" in Job.__mapper__.relationships["parse_results"].cascade
    assert "delete-orphan" in Job.__mapper__.relationships["match_results"].cascade
    assert (
        "delete-orphan"
        in JobParseResult.__mapper__.relationships["requirements"].cascade
    )
    for relationship_name in (
        "gate_checks",
        "requirement_assessments",
        "dimension_scores",
    ):
        assert (
            "delete-orphan"
            in JobMatchResult.__mapper__.relationships[relationship_name].cascade
        )
