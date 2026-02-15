#!/usr/bin/env bash
# Run Congress Twin PostgreSQL migrations in order.
# Usage: DATABASE_URL="postgresql://admin:admin@192.168.0.100:5432/tpcds" ./scripts/run_migrations.sh
# Or: POSTGRES_HOST=192.168.0.100 ./scripts/run_migrations.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONGRESS_TWIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -z "$DATABASE_URL" ]; then
  if [ -n "$POSTGRES_HOST" ]; then
    export DATABASE_URL="postgresql://${POSTGRES_USER:-admin}:${POSTGRES_PASSWORD:-admin}@${POSTGRES_HOST}:${POSTGRES_PORT:-5432}/${POSTGRES_DATABASE:-tpcds}"
  else
    echo "Error: DATABASE_URL or POSTGRES_HOST required"
    exit 1
  fi
fi

echo "Running migrations against $DATABASE_URL"

# Full schema init (idempotent)
psql "$DATABASE_URL" -f "$CONGRESS_TWIN_ROOT/scripts/init_schema_postgres.sql"

echo "Migrations complete."
