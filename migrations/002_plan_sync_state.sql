-- Congress Twin: plan_sync_state for "changes since sync" (last_sync_at, previous_sync_at).
-- Run: psql "postgresql://admin:admin@localhost:5432/tpcds" -f migrations/002_plan_sync_state.sql

SET search_path TO public;

CREATE TABLE IF NOT EXISTS public.plan_sync_state (
    planner_plan_id VARCHAR(255) PRIMARY KEY,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    previous_sync_at TIMESTAMP WITH TIME ZONE
);
