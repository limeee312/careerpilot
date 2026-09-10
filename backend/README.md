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

## Authentication

`POST /api/v1/auth/register` creates an account. Emails are trimmed and lowercased,
passwords must contain 15–128 characters, and stored credentials use salted Argon2id
hashes. Authentication secrets are never returned by the API.

`POST /api/v1/auth/login` stores a 60-minute JWT in the HttpOnly
`careerpilot_session` cookie. `GET /api/v1/auth/me` resolves the user from that
cookie, and `POST /api/v1/auth/logout` clears it. Cookies are marked Secure outside
development and test environments. Deployed environments refuse the built-in
development JWT secret and require a value of at least 32 characters.
