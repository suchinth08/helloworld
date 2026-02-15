-- Congress Twin: planner_plans table for plan listing and selection.
-- Run: sqlite3 congress_twin.db < migrations/005_planner_plans.sql
-- Note: planner_repo.ensure_planner_plans_table() creates this if not exists.

CREATE TABLE IF NOT EXISTS planner_plans (
    plan_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500),
    congress_date TEXT,
    source_plan_id VARCHAR(255),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
