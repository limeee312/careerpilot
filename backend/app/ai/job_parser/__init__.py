"""Job Parser v1 contracts."""

from app.ai.job_parser.constants import (
    JOB_PARSER_SKILL_NAME,
    JOB_PARSER_VERSION,
    MAX_JOB_PARSER_ATTEMPTS,
)
from app.ai.job_parser.prompt import JOB_PARSER_PROMPT_V1
from app.ai.job_parser.schemas import (
    JobParserInput,
    JobParserOutput,
    MatchDimension,
    ParsedRequirement,
    RequirementType,
)
from app.ai.job_parser.service import JobParserResult, parse_job
from app.ai.job_parser.validator import validate_job_parser_output

__all__ = [
    "JOB_PARSER_SKILL_NAME",
    "JOB_PARSER_PROMPT_V1",
    "JOB_PARSER_VERSION",
    "MAX_JOB_PARSER_ATTEMPTS",
    "JobParserInput",
    "JobParserOutput",
    "JobParserResult",
    "MatchDimension",
    "ParsedRequirement",
    "RequirementType",
    "parse_job",
    "validate_job_parser_output",
]
