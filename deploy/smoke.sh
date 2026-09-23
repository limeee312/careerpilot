#!/usr/bin/env bash
set -euo pipefail

# Exercise the production topology locally with disposable CI credentials.
export APP_DOMAIN=localhost
export BASIC_AUTH_USER=ci
export BASIC_AUTH_HASH
BASIC_AUTH_HASH=$(printf 'ci-only-password' | docker run --rm -i caddy:2-alpine caddy hash-password)
export POSTGRES_DB=careerpilot
export POSTGRES_USER=careerpilot
export POSTGRES_PASSWORD=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
export JWT_SECRET=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
export OPENAI_API_KEY=ci-only-not-a-real-key
export OPENAI_MODEL=ci-only-not-a-real-model
export RELEASE_TAG=ci

cp_prod=(docker compose -f docker-compose.prod.yml)
cookie_jar=$(mktemp)
cleanup() {
  result=$?
  if [ "$result" -ne 0 ]; then
    "${cp_prod[@]}" logs --tail=80
  fi
  "${cp_prod[@]}" down
  rm -f "$cookie_jar"
  exit "$result"
}
trap cleanup EXIT

"${cp_prod[@]}" config --quiet
docker run --rm \
  -e APP_DOMAIN="$APP_DOMAIN" -e BASIC_AUTH_USER="$BASIC_AUTH_USER" \
  -e BASIC_AUTH_HASH="$BASIC_AUTH_HASH" \
  -v "$PWD/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
"${cp_prod[@]}" up -d --build
docker run --rm careerpilot-backend:ci alembic heads

curl --fail --silent --show-error --insecure --retry 30 --retry-delay 2 \
  --retry-connrefused --user ci:ci-only-password \
  https://localhost/health > /dev/null

curl --fail --silent --show-error --insecure --user ci:ci-only-password \
  -H 'Content-Type: application/json' \
  -d '{"email":"ci-user@example.com","password":"correct-horse-battery-staple"}' \
  https://localhost/api/v1/auth/register > /dev/null

curl --fail --silent --show-error --insecure --user ci:ci-only-password \
  --cookie-jar "$cookie_jar" -H 'Content-Type: application/json' \
  -d '{"email":"ci-user@example.com","password":"correct-horse-battery-staple"}' \
  https://localhost/api/v1/auth/login > /dev/null

if ! grep -q 'careerpilot_session' "$cookie_jar"; then
  echo 'Login failed to set a browser session cookie' >&2
  exit 1
fi

curl --fail --silent --show-error --insecure --user ci:ci-only-password \
  --cookie "$cookie_jar" https://localhost/api/v1/auth/me > /dev/null
page_status=$(curl --silent --show-error --insecure --user ci:ci-only-password \
  --cookie "$cookie_jar" --output /dev/null --write-out '%{http_code}' \
  https://localhost/dashboard)
if [ "$page_status" != "200" ]; then
  echo "Authenticated dashboard returned HTTP $page_status" >&2
  exit 1
fi

echo 'Production topology smoke check passed.'
