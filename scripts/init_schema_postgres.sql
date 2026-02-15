-- Congress Twin: Full PostgreSQL schema (congress_twin schema).
-- Run: psql "$DATABASE_URL" -f scripts/init_schema_postgres.sql
-- Or: PGPASSWORD=admin psql -h 192.168.0.100 -U admin -d tpcds -f scripts/init_schema_postgres.sql

CREATE SCHEMA IF NOT EXISTS congress_twin;
SET search_path TO congress_twin;

-- planner_plans (plan metadata)
CREATE TABLE IF NOT EXISTS planner_plans (
    plan_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500),
    congress_date TIMESTAMP WITH TIME ZONE,
    source_plan_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- planner_tasks (MS Planner–like fields)
CREATE TABLE IF NOT EXISTS planner_tasks (
    id SERIAL PRIMARY KEY,
    planner_task_id VARCHAR(255) NOT NULL,
    planner_plan_id VARCHAR(255) NOT NULL,
    planner_bucket_id VARCHAR(255),
    bucket_name VARCHAR(500),
    title TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'notStarted',
    percent_complete INTEGER DEFAULT 0 CHECK (percent_complete >= 0 AND percent_complete <= 100),
    due_date TIMESTAMP WITH TIME ZONE,
    start_date TIMESTAMP WITH TIME ZONE,
    last_modified_at TIMESTAMP WITH TIME ZONE,
    assignees JSONB DEFAULT '[]',
    assignee_names JSONB DEFAULT '[]',
    priority INTEGER CHECK (priority >= 0 AND priority <= 10),
    completed_date_time TIMESTAMP WITH TIME ZONE,
    created_date_time TIMESTAMP WITH TIME ZONE,
    order_hint TEXT,
    assignee_priority TEXT,
    applied_categories JSONB DEFAULT '[]',
    conversation_thread_id TEXT,
    description TEXT,
    preview_type TEXT,
    created_by TEXT,
    completed_by TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (planner_plan_id, planner_task_id)
);
CREATE INDEX IF NOT EXISTS idx_planner_tasks_plan_id ON planner_tasks(planner_plan_id);
CREATE INDEX IF NOT EXISTS idx_planner_tasks_status ON planner_tasks(status);
CREATE INDEX IF NOT EXISTS idx_planner_tasks_due_date ON planner_tasks(due_date);

-- planner_task_details (checklist, references)
CREATE TABLE IF NOT EXISTS planner_task_details (
    id SERIAL PRIMARY KEY,
    planner_task_id VARCHAR(255) NOT NULL,
    planner_plan_id VARCHAR(255) NOT NULL,
    checklist_items JSONB DEFAULT '[]',
    "references" JSONB DEFAULT '[]',
    last_modified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (planner_plan_id, planner_task_id)
);
CREATE INDEX IF NOT EXISTS idx_planner_task_details_task ON planner_task_details(planner_plan_id, planner_task_id);

-- planner_task_dependencies
CREATE TABLE IF NOT EXISTS planner_task_dependencies (
    id SERIAL PRIMARY KEY,
    planner_plan_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    depends_on_task_id VARCHAR(255) NOT NULL,
    dependency_type VARCHAR(10) DEFAULT 'FS',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (planner_plan_id, task_id, depends_on_task_id)
);
CREATE INDEX IF NOT EXISTS idx_planner_task_dependencies_task ON planner_task_dependencies(planner_plan_id, task_id);
CREATE INDEX IF NOT EXISTS idx_planner_task_dependencies_depends_on ON planner_task_dependencies(planner_plan_id, depends_on_task_id);

-- plan_sync_state
CREATE TABLE IF NOT EXISTS plan_sync_state (
    planner_plan_id VARCHAR(255) PRIMARY KEY,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    previous_sync_at TIMESTAMP WITH TIME ZONE
);

-- external_events
CREATE TABLE IF NOT EXISTS external_events (
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
CREATE INDEX IF NOT EXISTS idx_external_events_plan_id ON external_events(plan_id);

-- agent_proposed_actions
CREATE TABLE IF NOT EXISTS agent_proposed_actions (
    id SERIAL PRIMARY KEY,
    plan_id VARCHAR(255) NOT NULL,
    external_event_id INTEGER,
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
CREATE INDEX IF NOT EXISTS idx_agent_proposed_actions_plan_id ON agent_proposed_actions(plan_id);
CREATE INDEX IF NOT EXISTS idx_agent_proposed_actions_status ON agent_proposed_actions(status);

-- task_locks (transaction locks for collaborative editing)
CREATE TABLE IF NOT EXISTS task_locks (
    plan_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    locked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (plan_id, task_id)
);

-- markov_transition_matrices
CREATE TABLE IF NOT EXISTS markov_transition_matrices (
    id SERIAL PRIMARY KEY,
    matrix_key VARCHAR(255) NOT NULL,
    from_state VARCHAR(50) NOT NULL,
    to_state VARCHAR(50) NOT NULL,
    probability REAL NOT NULL CHECK (probability >= 0 AND probability <= 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (matrix_key, from_state, to_state)
);
CREATE INDEX IF NOT EXISTS idx_markov_matrices_key ON markov_transition_matrices(matrix_key);
