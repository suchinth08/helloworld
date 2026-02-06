-- Congress Twin: minimal planner_tasks table (no FK to planner_plans for standalone use).
-- Target: Postgres localhost, database tpcds, schema public, user admin/admin
-- Run: psql "postgresql://admin:admin@localhost:5432/tpcds" -f migrations/001_planner_tasks.sql

SET search_path TO public;

CREATE TABLE IF NOT EXISTS public.planner_tasks (
    id SERIAL PRIMARY KEY,
    planner_task_id VARCHAR(255) NOT NULL,
    planner_plan_id VARCHAR(255) NOT NULL,
    planner_bucket_id VARCHAR(255),
    bucket_name VARCHAR(500),
    title TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'notStarted',
    percent_complete INTEGER DEFAULT 0 CHECK (percent_complete >= 0 AND percent_complete <= 100),
    due_date TIMESTAMP WITH TIME ZONE,
    last_modified_at TIMESTAMP WITH TIME ZONE,
    assignees JSONB DEFAULT '[]',
    assignee_names JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (planner_plan_id, planner_task_id)
);

CREATE INDEX IF NOT EXISTS idx_planner_tasks_plan_id ON public.planner_tasks(planner_plan_id);
CREATE INDEX IF NOT EXISTS idx_planner_tasks_status ON public.planner_tasks(status);
CREATE INDEX IF NOT EXISTS idx_planner_tasks_due_date ON public.planner_tasks(due_date);
