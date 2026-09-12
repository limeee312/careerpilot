"""Job Parser v1 contracts."""

from app.ai.job_parser.schemas import (
    JobParserInput,
    JobParserOutput,
    MatchDimension,
    ParsedRequirement,
    RequirementType,
)
from app.ai.job_parser.validator import validate_job_parser_output

JOB_PARSER_VERSION = "job_parser_v1"

__all__ = [
    "JOB_PARSER_VERSION",
    "JobParserInput",
    "JobParserOutput",
    "MatchDimension",
    "ParsedRequirement",
    "RequirementType",
    "validate_job_parser_output",
]
