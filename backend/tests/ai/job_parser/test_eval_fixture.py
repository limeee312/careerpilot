"""Keep the first Job Parser eval case synchronized with the live contract."""

import json
from pathlib import Path

from app.ai.job_parser.schemas import JobParserInput, JobParserOutput, RequirementType
from app.ai.job_parser.validator import validate_job_parser_output

EVAL_DIRECTORY = (
    Path(__file__).parents[4] / "tests" / "evals" / "job_parser" / "product_operations"
)


def load_json(name: str) -> object:
    return json.loads((EVAL_DIRECTORY / name).read_text(encoding="utf-8"))


def test_product_operations_eval_matches_parser_v1_contract() -> None:
    parser_input = JobParserInput.model_validate(load_json("input.json"))
    output = JobParserOutput.model_validate(load_json("expected.json"))

    validate_job_parser_output(parser_input, output)

    sql_requirement = output.requirements[-1]
    assert sql_requirement.requirement_type is RequirementType.PREFERRED
    assert sql_requirement.dimension is not None
    assert all(
        requirement.requirement_key == f"R{index}"
        for index, requirement in enumerate(output.requirements, start=1)
    )
