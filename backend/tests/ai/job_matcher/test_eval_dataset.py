"""Ensure the versioned eval data remains executable against live AI contracts."""

import json
import subprocess
import sys
from pathlib import Path

from app.ai.job_matcher.schemas import MatcherInput
from app.ai.job_parser.schemas import JobParserInput, JobParserOutput
from app.ai.job_parser.validator import validate_job_parser_output

EVAL_ROOT = Path(__file__).resolve().parents[4] / "tests" / "evals"


def test_matcher_eval_cases_are_grounded_and_schema_compatible() -> None:
    subprocess.run([sys.executable, str(EVAL_ROOT / "validate.py")], check=True)
    jobs = json.loads(
        (EVAL_ROOT / "matcher" / "jobs.json").read_text(encoding="utf-8")
    )
    cases = json.loads(
        (EVAL_ROOT / "matcher" / "cases.json").read_text(encoding="utf-8")
    )
    parsed = {}
    for job in jobs:
        parser_input = JobParserInput.model_validate(job["parser_input"])
        output = JobParserOutput.model_validate(job["parsed_job"])
        validate_job_parser_output(parser_input, output)
        parsed[job["id"]] = output

    for case in cases:
        for comparison in case["comparisons"]:
            MatcherInput.model_validate(
                {
                    "parsed_job": parsed[comparison["job_id"]],
                    "resume_evidence": case["resume_evidence"],
                }
            )
