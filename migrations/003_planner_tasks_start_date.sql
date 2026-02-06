-- Congress Twin: add start_date to planner_tasks (MS Planner start/due).
-- Run after 001: from congress-twin dir, psql $CONGRESS_TWIN_PG_CONN -f migrations/003_planner_tasks_start_date.sql

SET search_path TO public;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'planner_tasks' AND column_name = 'start_date'
  ) THEN
    ALTER TABLE public.planner_tasks ADD COLUMN start_date TIMESTAMP WITH TIME ZONE;
  END IF;
END $$;
