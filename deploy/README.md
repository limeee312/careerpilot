# CP-032 production deployment runbook

This is a single-host Docker Compose deployment for a **private demo**. A Caddy
entry point serves the Next.js site and proxies `/api/v1` to FastAPI on the same
HTTPS hostname. Browser requests therefore use the host-only `Secure`,
`HttpOnly`, `SameSite=Lax` session cookie; FastAPI and PostgreSQL expose no host
ports. Caddy requires a second, hashed demo password before any page or API
call. Frontend server rendering reaches the API over the private Docker network.

## Prerequisites

- A Linux host with Docker Engine and the Compose plugin, persistent disk space
  for PostgreSQL and Caddy certificates, and a DNS name pointing at the host.
- Public TCP ports 80 and 443 routed to that host; these allow Caddy to obtain
  and renew a certificate. Keep database port 5432 closed to the internet.
- A server-side OpenAI API key and selected supported model. Set a spending
  limit outside the app. Basic auth restricts who may use the demo; it is not a
  per-user AI usage quota.
- A plan to collect test evidence and review real resume/model outputs. CP-031's
  synthetic pilot is not production evaluation evidence.

## Configure and launch

From the repository root on the host:

```bash
cp deploy/production.env.example .env.production
chmod 600 .env.production
python3 -c 'import secrets; print(secrets.token_hex(32))'
docker run --rm -it caddy:2-alpine caddy hash-password
```

Generate **two different** 64-character hex strings for `POSTGRES_PASSWORD` and
`JWT_SECRET`. Copy the interactive Caddy hash into `BASIC_AUTH_HASH` in single
quotes. Fill every placeholder in `.env.production`; use a real DNS hostname in
`APP_DOMAIN`, no `https://`. Set `OPENAI_API_KEY` and `OPENAI_MODEL` on the host
only. The frontend receives only `/api/v1`, never the provider secret.

```bash
python3 deploy/check_env.py .env.production
docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

The migration container runs `alembic upgrade head` after PostgreSQL is healthy;
the API waits for the migration to finish, and the proxy waits for healthy API
and frontend containers. If migration fails, inspect its logs and resolve the
error before retrying. Never delete the named database volume to recover.

Verify `https://<APP_DOMAIN>/health` (Caddy asks for demo credentials), then
register a test user, log in, save a test resume, match a job, save a tailored
version, and create an application. The external API and pages should remain on
the **same** HTTPS hostname. Inspect the backend readiness probe inside the
network with `docker compose ... exec backend ...` or `docker compose ... ps`.
For an internal readiness check, run:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec backend \
  python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready').read().decode())"
```

Record the real demo URL only after these checks pass.

## Update, backup, and recovery

Before an upgrade, make a database backup in a protected directory on the host:

```bash
umask 077
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db \
  pg_dump -U careerpilot -Fc careerpilot > careerpilot-before-upgrade.dump
```

Use the configured `POSTGRES_USER` and `POSTGRES_DB` if they differ from the
example. Copy backups off the host, keep them encrypted, and test restoration
separately. Review migration changes, then pull the reviewed Git revision and
repeat the configure/launch commands. For application rollback, check out the
previous reviewed revision and rebuild; database migrations are **not**
automatically reversed. If schema recovery is required, restore from a verified
backup through a deliberate maintenance procedure.

For troubleshooting, use `docker compose --env-file .env.production -f
docker-compose.prod.yml logs --tail=100 backend` (or `frontend`, `migrate`,
`proxy`, `db`). Do not publish `.env.production`, database dumps, session
tokens, or personal resumes in a PR or issue. Once a shared public release is
planned, add persistent per-user AI usage controls and complete real-data
evaluation.
