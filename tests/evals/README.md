# CP-031: AI evaluation data

`job_parser/product_operations/` is the earlier Job Parser example.
`matcher/` contains a **curated synthetic pilot**, not a real-candidate
benchmark. Its 20 fictional, non-identifying resume evidence sets are compared
with four of 17 job descriptions each (80 pairs). Five Resume Tailor probes cover
fabricated employer, degree, project, skill, and numeric outcome claims. The
pilot is useful for checking contracts and the evaluation procedure. It does
**not** satisfy the MVP requirement for 20 real or deidentified resumes. Do not
present its accuracy as evidence of real-world model quality or release readiness.

## Files and labels

- `matcher/jobs.json`: raw JD, curated parsed requirements, exact JD
  quotes and requirement types (`HARD`, `CORE`, `STANDARD`, `PREFERRED`).
- `matcher/cases.json`: source-addressable resume evidence with explicit
  `source_kind`, authored job order, best match, top three, clearly unsuitable
  job, hard-gate expectation (`PASS`, `WARN`, `FAIL`), quoted key strengths,
  and key gaps. A gate's `WARN` means available evidence does not resolve it;
  it is not a failure. These pilot labels are proposed reference answers and
  still need independent human adjudication. The order is not model output.
- `matcher/tailor_cases.json`: unsupported factual claims that a generated
  Resume Tailor draft must **not** introduce as existing experience.
- `build_synthetic_seed.py`: reproducible synthetic pilot authoring source.
  Rerun it after edits and commit the regenerated JSON together with the source.
- `validate.py`: structural coverage and source-quote checks. The backend
  pytest suite additionally validates every job and resume evidence set against
  the live Pydantic Parser/Matcher contracts and checks JD grounding.
- `score.py`: offline scorer for saved predictions and human claim reviews.
  No live AI request, API key, or model expense is involved in CI.

Run from the repository root:

```bash
python tests/evals/validate.py
cd backend && uv run pytest -q tests/ai/job_matcher/test_eval_dataset.py
python ../tests/evals/score.py /path/to/predictions.json
```

## Prediction input

`score.py` accepts a JSON array, one entry per case. Each entry contains:

```json
{
  "case_id": "C01",
  "ranked_job_ids": ["product_ops", "grad27_product", "community_ops", "backend_dev"],
  "hard_gates": {
    "product_ops": {"R1": "PASS"},
    "grad27_product": {"R1": "PASS"},
    "community_ops": {"R1": "PASS"},
    "backend_dev": {"R1": "FAIL"}
  },
  "evidence_refs": [
    {"job_id": "product_ops", "source_type": "experience", "source_id": "C01-exp", "source_quote": "用户行为分析和产品体验优化"}
  ],
  "claim_reviews": [
    {"job_id": "product_ops", "claim": "有用户行为分析经验", "supported": true, "reviewer": "reviewer-id"}
  ]
}
```

The example is shaped like an **ideal annotation**, not a measured prediction.
Record the actual ranked results and hard-gate statuses from a model run.
Extract every evidence reference supplied by the model for grounding checks.
Have a reviewer examine *all factual claims* (including strengths and tailored
resume bullets) against the source resume and fill `claim_reviews`; unsupported
claims are hallucinations even when a fabricated quote looks superficially
plausible. Model/version, prompt version, date, and reviewer IDs should be stored
alongside each run outside the fixture files. Never commit credentials or raw
personal data.

Scores include top-1 accuracy, top-3 recall, unsuitable-last rate, hard-gate
accuracy, false `PASS` on a gold `FAIL`, false `FAIL` on a gold `PASS`, evidence
quote grounding, and human-reviewed hallucination rate. Missing claim reviews or
evidence references yield a `null` rate and a zero denominator, not a passing
score. Partial case runs report coverage; do not interpret them as a full run.
For release assessment require complete coverage, zero major hard-gate errors,
zero invented resume facts, and review of every output claim. Tailor probes
also require a reviewer to verify that each forbidden claim remains absent.

## Replacing the pilot with real evidence

Obtain 20 consented real resumes or properly deidentified resumes through an
approved source. Remove names, emails, phone numbers, addresses, identifiers,
and unnecessary organization names before committing. Keep source IDs stable,
include 3–5 realistic jobs per resume, and have at least two independent
reviewers assign best match, top three, clearly unsuitable, gate statuses,
quoted strengths, and gaps. Resolve disagreements and record anonymized review
provenance. Explicit negative evidence is needed for a gold `FAIL`; lack of
evidence should be `WARN`. Use `source_kind: "deidentified_real"` only when
the provenance is genuine. Run `validate.py` and the Pydantic contract test,
then evaluate a saved model run. Review the resulting cases and metrics before
replacing the synthetic fixtures or reporting benchmark performance.
