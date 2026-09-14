# CareerPilot Backend

FastAPI service for authentication, resumes, job matching, resume tailoring, and applications.

## Development

```bash
uv sync --all-groups
uv run fastapi dev app/main.py
```

The API is available at <http://localhost:8000>, with OpenAPI documentation at <http://localhost:8000/docs>.

## AI provider configuration

Job Parser uses the OpenAI Responses API with strict Pydantic Structured Outputs.
Set `OPENAI_API_KEY` and `OPENAI_MODEL` on the backend only; neither value is sent
to the browser. `OPENAI_TIMEOUT_SECONDS` defaults to 30 seconds.

The OpenAI SDK retry loop is disabled. Each CareerPilot skill owns its documented
retry policy, so `job_parser_v1` makes at most two provider attempts: the original
request plus one retry for a timeout, provider 5xx response, or invalid structured
output. It does not retry empty input, configuration errors, 4xx responses, or
connection failures.

Job parsing and matching history is stored in append-oriented records. Parser runs
own atomic requirements; each match result owns gate checks, non-hard requirement
assessments, and dimension subtotals. Composite foreign keys require the selected
Job, Resume Master, and parse result to share the same user and job context.

`POST /api/v1/job-match/batches/{batch_id}/analyze` creates a fresh Parser run
for every job, then executes Parser and Matcher with per-job failure isolation.
Successful results are committed independently, so a mixed batch finishes as
`PARTIAL_FAILED` without discarding completed jobs. Reanalysis appends history.

`GET /api/v1/job-match/{batch_id}` returns the current run's progress and ranked
result summaries. `GET /api/v1/job-match/batches/{batch_id}/results` is a
compatibility alias for the same owner-filtered response. Normal candidates use
the deterministic near-tie ranking rules; hard-gate failures remain unranked and
appear after the normal sequence.

## Quality checks

```bash
uv run ruff check .
uv run pytest
```

`GET /health` is the liveness probe. `GET /health/ready` also verifies that PostgreSQL accepts connections.

## Authentication

`POST /api/v1/auth/register` creates an account. Emails are trimmed and lowercased,
passwords must contain 15–128 characters, and stored credentials use salted Argon2id
hashes. Authentication secrets are never returned by the API.

`POST /api/v1/auth/login` stores a 60-minute JWT in the HttpOnly
`careerpilot_session` cookie. `GET /api/v1/auth/me` resolves the user from that
cookie, and `POST /api/v1/auth/logout` clears it. Cookies are marked Secure outside
development and test environments. Deployed environments refuse the built-in
development JWT secret and require a value of at least 32 characters.
