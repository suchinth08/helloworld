-- Congress Twin: agent proposed actions (re-adjustments) with human-in-the-loop approval.
-- Linked to external_events when event triggers proposal.

SET search_path TO public;

CREATE TABLE IF NOT EXISTS public.agent_proposed_actions (
    id SERIAL PRIMARY KEY,
    plan_id VARCHAR(255) NOT NULL,
    external_event_id INTEGER REFERENCES public.external_events(id) ON DELETE SET NULL,
    task_id VARCHAR(255),
    action_type VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    payload JSONB DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    decided_at TIMESTAMP WITH TIME ZONE,
    decided_by VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_agent_proposed_actions_plan_id ON public.agent_proposed_actions(plan_id);
CREATE INDEX IF NOT EXISTS idx_agent_proposed_actions_status ON public.agent_proposed_actions(status);
CREATE INDEX IF NOT EXISTS idx_agent_proposed_actions_external_event_id ON public.agent_proposed_actions(external_event_id);
