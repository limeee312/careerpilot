#!/usr/bin/env bash
set -euo pipefail

# Verify a first local startup against a fresh PostgreSQL volume.
cp_local=(docker compose -f docker-compose.yml)
export POSTGRES_DB=careerpilot
export POSTGRES_USER=careerpilot
export POSTGRES_PASSWORD=careerpilot

cleanup() {
  result=$?
  if [ "$result" -ne 0 ]; then
    "${cp_local[@]}" logs --tail=80
  fi
  "${cp_local[@]}" down --volumes
  exit "$result"
}
trap cleanup EXIT

"${cp_local[@]}" config --quiet
"${cp_local[@]}" up -d --build

curl --fail --silent --show-error --retry 30 --retry-delay 2 \
  --retry-connrefused http://localhost:8000/health/ready > /dev/null

curl --fail --silent --show-error \
  -H 'Content-Type: application/json' \
  -d '{"email":"local-smoke@example.com","password":"correct-horse-battery-staple"}' \
  http://localhost:8000/api/v1/auth/register > /dev/null

curl --fail --silent --show-error --retry 30 --retry-delay 2 \
  --retry-all-errors http://localhost:3000/login > /dev/null

echo 'Local Compose smoke check passed.'
