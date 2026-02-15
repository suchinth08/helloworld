-- Congress Twin: Idempotent PostgreSQL catch-up migration.
-- Use when planner_tasks exists but is missing columns (priority, etc.) or when
-- planner_plans / planner_task_dependencies are missing.
-- If planner_tasks does not exist in congress_twin at all, run scripts/init_schema_postgres.sql first.
-- Run: psql "$DATABASE_URL" -f migrations/007_postgres_catchup.sql
-- Or: PGPASSWORD=admin psql -h HOST -U admin -d tpcds -f migrations/007_postgres_catchup.sql

CREATE SCHEMA IF NOT EXISTS congress_twin;
SET search_path TO congress_twin;

-- 1) planner_plans (if missing)
CREATE TABLE IF NOT EXISTS congress_twin.planner_plans (
    plan_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500),
    congress_date TIMESTAMP WITH TIME ZONE,
    source_plan_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2) planner_task_dependencies (if missing)
CREATE TABLE IF NOT EXISTS congress_twin.planner_task_dependencies (
    id SERIAL PRIMARY KEY,
    planner_plan_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    depends_on_task_id VARCHAR(255) NOT NULL,
    dependency_type VARCHAR(10) DEFAULT 'FS',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (planner_plan_id, task_id, depends_on_task_id)
);
CREATE INDEX IF NOT EXISTS idx_planner_task_dependencies_task ON congress_twin.planner_task_dependencies(planner_plan_id, task_id);
CREATE INDEX IF NOT EXISTS idx_planner_task_dependencies_depends_on ON congress_twin.planner_task_dependencies(planner_plan_id, depends_on_task_id);

-- 3) planner_tasks: add missing columns when table already existed (e.g. from 001/003)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'congress_twin' AND table_name = 'planner_tasks' AND column_name = 'start_date') THEN
    ALTER TABLE congress_twin.planner_tasks ADD COLUMN start_date TIMESTAMP WITH TIME ZONE;
  END IF;
END $$;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'congress_twin' AND table_name = 'planner_tasks' AND column_name = 'priority') THEN
    ALTER TABLE congress_twin.planner_tasks ADD COLUMN priority INTEGER;
  END IF;
END $$;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'congress_twin' AND table_name = 'planner_tasks' AND column_name = 'completed_date_time') THEN
    ALTER TABLE congress_twin.planner_tasks ADD COLUMN completed_date_time TIMESTAMP WITH TIME ZONE;
  END IF;
END $$;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'congress_twin' AND table_name = 'planner_tasks' AND column_name = 'created_date_time') THEN
    ALTER TABLE congress_twin.planner_tasks ADD COLUMN created_date_time TIMESTAMP WITH TIME ZONE;
  END IF;
END $$;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'congress_twin' AND table_name = 'planner_tasks' AND column_name = 'order_hint') THEN
    ALTER TABLE congress_twin.planner_tasks ADD COLUMN order_hint TEXT;
  END IF;
END $$;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'congress_twin' AND table_name = 'planner_tasks' AND column_name = 'assignee_priority') THEN
    ALTER TABLE congress_twin.planner_tasks ADD COLUMN assignee_priority TEXT;
  END IF;
END $$;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'congress_twin' AND table_name = 'planner_tasks' AND column_name = 'applied_categories') THEN
    ALTER TABLE congress_twin.planner_tasks ADD COLUMN applied_categories JSONB DEFAULT '[]';
  END IF;
END $$;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'congress_twin' AND table_name = 'planner_tasks' AND column_name = 'conversation_thread_id') THEN
    ALTER TABLE congress_twin.planner_tasks ADD COLUMN conversation_thread_id TEXT;
  END IF;
END $$;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'congress_twin' AND table_name = 'planner_tasks' AND column_name = 'description') THEN
    ALTER TABLE congress_twin.planner_tasks ADD COLUMN description TEXT;
  END IF;
END $$;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'congress_twin' AND table_name = 'planner_tasks' AND column_name = 'preview_type') THEN
    ALTER TABLE congress_twin.planner_tasks ADD COLUMN preview_type TEXT;
  END IF;
END $$;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'congress_twin' AND table_name = 'planner_tasks' AND column_name = 'created_by') THEN
    ALTER TABLE congress_twin.planner_tasks ADD COLUMN created_by TEXT;
  END IF;
END $$;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'congress_twin' AND table_name = 'planner_tasks' AND column_name = 'completed_by') THEN
    ALTER TABLE congress_twin.planner_tasks ADD COLUMN completed_by TEXT;
  END IF;
END $$;
