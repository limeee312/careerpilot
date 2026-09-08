# CareerPilot Backend

FastAPI service for authentication, resumes, job matching, resume tailoring, and applications.

## Development

```bash
uv sync --all-groups
uv run fastapi dev app/main.py
```

The API is available at <http://localhost:8000>, with OpenAPI documentation at <http://localhost:8000/docs>.

## Quality checks

```bash
uv run ruff check .
uv run pytest
```

`GET /health` is the liveness probe. `GET /health/ready` also verifies that PostgreSQL accepts connections.
