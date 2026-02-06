-- Congress Twin: external events (flight cancellation, meeting cancelled, etc.) for alerts.
-- Run after 003. Creates alert events visible in dashboard.

SET search_path TO public;

CREATE TABLE IF NOT EXISTS public.external_events (
    id SERIAL PRIMARY KEY,
    plan_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity VARCHAR(50) DEFAULT 'medium',
    affected_task_ids JSONB DEFAULT '[]',
    payload JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_external_events_plan_id ON public.external_events(plan_id);
CREATE INDEX IF NOT EXISTS idx_external_events_created_at ON public.external_events(created_at DESC);
