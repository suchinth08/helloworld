# Congress Twin migrations

Run the SQL migration once so that **sync from Graph** can persist tasks to Postgres.

## Target Postgres

| Setting   | Value    |
|-----------|----------|
| Host      | localhost |
| Port      | 5432     |
| Database  | tpcds    |
| Schema    | public   |
| Username  | admin    |
| Password  | admin    |

## Run migration

```bash
# From congress-twin directory
psql "postgresql://admin:admin@localhost:5432/tpcds" -f migrations/001_planner_tasks.sql
psql "postgresql://admin:admin@localhost:5432/tpcds" -f migrations/002_plan_sync_state.sql
```

Or with env var:

```bash
export PG_CONN="postgresql://admin:admin@localhost:5432/tpcds"
psql "$PG_CONN" -f migrations/001_planner_tasks.sql
```

If the table does not exist, `GET /api/v1/planner/tasks/{plan_id}` still works (it returns simulated data for the default plan). Sync from Graph will fail with a DB error until the migration is applied.
