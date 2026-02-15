-- Congress Twin: task_locks for concurrent edit prevention.
-- Run: sqlite3 congress_twin.db < migrations/006_task_locks.sql

CREATE TABLE IF NOT EXISTS task_locks (
    plan_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    locked_at TEXT NOT NULL,
    PRIMARY KEY (plan_id, task_id)
);
