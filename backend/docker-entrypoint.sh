#!/usr/bin/env bash
#
# Runs before the container's main process. Compose already waits for Postgres
# to pass its healthcheck, so the database is up by the time we get here —
# this just brings the schema to head. Postgres is the only supported backend,
# so migrations own the schema; nothing calls create_all at boot.
set -euo pipefail

if [[ "${RUN_MIGRATIONS:-1}" == "1" ]]; then
  echo "→ alembic upgrade head"
  alembic upgrade head
fi

exec "$@"
