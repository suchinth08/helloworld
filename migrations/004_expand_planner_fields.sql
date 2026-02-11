-- Congress Twin: Expand planner_tasks with all MS Planner fields per ACP_05 PDF reference.
-- Run: sqlite3 congress_twin.db < migrations/004_expand_planner_fields.sql
-- Or: Python will auto-apply via ensure_planner_tasks_table() and related functions.

-- Add new columns to planner_tasks (backward compatible - all nullable)
ALTER TABLE planner_tasks ADD COLUMN priority INTEGER CHECK (priority >= 0 AND priority <= 10);
ALTER TABLE planner_tasks ADD COLUMN completed_date_time TEXT;
ALTER TABLE planner_tasks ADD COLUMN created_date_time TEXT;
ALTER TABLE planner_tasks ADD COLUMN order_hint TEXT;
ALTER TABLE planner_tasks ADD COLUMN assignee_priority TEXT;
ALTER TABLE planner_tasks ADD COLUMN applied_categories TEXT DEFAULT '[]'; -- JSON array
ALTER TABLE planner_tasks ADD COLUMN conversation_thread_id TEXT;
ALTER TABLE planner_tasks ADD COLUMN description TEXT;
ALTER TABLE planner_tasks ADD COLUMN preview_type TEXT;
ALTER TABLE planner_tasks ADD COLUMN created_by TEXT;
ALTER TABLE planner_tasks ADD COLUMN completed_by TEXT;

-- Create planner_task_details table for extended properties
CREATE TABLE IF NOT EXISTS planner_task_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    planner_task_id VARCHAR(255) NOT NULL,
    planner_plan_id VARCHAR(255) NOT NULL,
    checklist_items TEXT DEFAULT '[]', -- JSON array of {id, title, isChecked, lastModifiedDateTime, orderHint}
    references TEXT DEFAULT '[]', -- JSON array of {alias, type, lastModifiedBy, lastModifiedDateTime}
    last_modified_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (planner_plan_id, planner_task_id),
    FOREIGN KEY (planner_plan_id, planner_task_id) REFERENCES planner_tasks(planner_plan_id, planner_task_id)
);

CREATE INDEX IF NOT EXISTS idx_planner_task_details_task ON planner_task_details(planner_plan_id, planner_task_id);

-- Create planner_task_dependencies table for explicit dependencies
CREATE TABLE IF NOT EXISTS planner_task_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    planner_plan_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    depends_on_task_id VARCHAR(255) NOT NULL,
    dependency_type VARCHAR(10) DEFAULT 'FS', -- FS=Finish-to-Start, SS=Start-to-Start, FF=Finish-to-Finish, SF=Start-to-Finish
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (planner_plan_id, task_id, depends_on_task_id)
);

CREATE INDEX IF NOT EXISTS idx_planner_task_dependencies_task ON planner_task_dependencies(planner_plan_id, task_id);
CREATE INDEX IF NOT EXISTS idx_planner_task_dependencies_depends_on ON planner_task_dependencies(planner_plan_id, depends_on_task_id);

-- Create markov_transition_matrices table for storing calibrated transition probabilities
CREATE TABLE IF NOT EXISTS markov_transition_matrices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matrix_key VARCHAR(255) NOT NULL UNIQUE, -- e.g., "bucket:Venue&Logistics:phase:final_weeks"
    from_state VARCHAR(50) NOT NULL,
    to_state VARCHAR(50) NOT NULL,
    probability REAL NOT NULL CHECK (probability >= 0 AND probability <= 1),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (matrix_key, from_state, to_state)
);

CREATE INDEX IF NOT EXISTS idx_markov_matrices_key ON markov_transition_matrices(matrix_key);
