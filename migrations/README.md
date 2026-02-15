# Congress Twin – Database migrations

## PostgreSQL (schema `congress_twin`)

The app uses `postgres_schema=congress_twin` by default. Ensure that schema and tables exist.

- **Fresh install**: run the full schema script from the project root:
  ```bash
  psql "$DATABASE_URL" -f scripts/init_schema_postgres.sql
  ```
  Or with explicit host/user:
  ```bash
  PGPASSWORD=admin psql -h 192.168.0.100 -U admin -d tpcds -f scripts/init_schema_postgres.sql
  ```

- **Existing DB with errors** like `column "priority" of relation "planner_tasks" does not exist` or `relation "planner_plans" does not exist`: run the catch-up migration:
  ```bash
  psql "$DATABASE_URL" -f migrations/007_postgres_catchup.sql
  ```
  This creates `planner_plans` and `planner_task_dependencies` if missing, and adds any missing columns to `planner_tasks` in schema `congress_twin`.

## SQLite

Migrations 001–006 and the repo’s `ensure_*_table()` logic apply when not using PostgreSQL (no manual migration required for SQLite).
