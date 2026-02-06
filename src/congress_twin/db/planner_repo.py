"""
Planner tasks repository: read/write normalized tasks to SQLite (embedded database).
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine

from congress_twin.config import get_settings

logger = logging.getLogger(__name__)

_engine: Optional[Engine] = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        # SQLite: enable foreign keys and use check_same_thread=False for async compatibility
        conn_str = get_settings().sqlite_conn
        _engine = create_engine(conn_str, connect_args={"check_same_thread": False})
    return _engine


def _task_row_to_dict(row: Any) -> dict[str, Any]:
    """Map DB row to API task shape (MS Planner–like: start/due, assignees, % complete, last modified)."""
    def _iso(dt: Any) -> str | None:
        if dt is None:
            return None
        # SQLite stores dates as TEXT, so they're already strings
        if isinstance(dt, str):
            s = dt
        elif hasattr(dt, "isoformat"):
            s = dt.isoformat()
        else:
            s = str(dt)
        if s and not s.endswith("Z") and "+" not in s:
            s = f"{s}Z"
        return s
    due = getattr(row, "due_date", None)
    start = getattr(row, "start_date", None)
    last_mod = getattr(row, "last_modified_at", None)
    raw_a = getattr(row, "assignees", None)
    raw_an = getattr(row, "assignee_names", None)
    assignees = raw_a if isinstance(raw_a, list) else (json.loads(raw_a) if raw_a else [])
    assignee_names = raw_an if isinstance(raw_an, list) else (json.loads(raw_an) if raw_an else [])
    out: dict[str, Any] = {
        "id": getattr(row, "planner_task_id", ""),
        "title": getattr(row, "title", "") or "",
        "bucketId": getattr(row, "planner_bucket_id", "") or "",
        "bucketName": getattr(row, "bucket_name", "") or "",
        "percentComplete": getattr(row, "percent_complete", 0) or 0,
        "status": getattr(row, "status", "notStarted") or "notStarted",
        "dueDateTime": _iso(due),
        "assignees": assignees,
        "assigneeNames": assignee_names,
        "lastModifiedAt": _iso(last_mod),
    }
    if start is not None:
        out["startDateTime"] = _iso(start)
    return out


def ensure_plan_sync_state_table() -> None:
    """Create plan_sync_state table if it does not exist (last_sync_at, previous_sync_at for changes-since-sync)."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS plan_sync_state (
                planner_plan_id VARCHAR(255) PRIMARY KEY,
                last_sync_at TEXT,
                previous_sync_at TEXT
            )
        """))
        conn.commit()


def get_plan_sync_state(plan_id: str) -> tuple[Optional[datetime], Optional[datetime]]:
    """Return (last_sync_at, previous_sync_at) for the plan. (None, None) if not found."""
    ensure_plan_sync_state_table()
    try:
        with get_engine().connect() as conn:
            r = conn.execute(
                text("SELECT last_sync_at, previous_sync_at FROM plan_sync_state WHERE planner_plan_id = :plan_id"),
                {"plan_id": plan_id},
            )
            row = r.fetchone()
    except Exception as e:
        logger.warning("get_plan_sync_state failed: %s", e)
        return (None, None)
    if not row:
        return (None, None)
    return (getattr(row, "last_sync_at", None), getattr(row, "previous_sync_at", None))


def set_plan_sync_state(plan_id: str, last_sync_at: datetime, previous_sync_at: Optional[datetime] = None) -> None:
    """Update sync timestamps after a sync. If previous_sync_at not provided, use old last_sync_at."""
    ensure_plan_sync_state_table()
    engine = get_engine()
    with engine.connect() as conn:
        if previous_sync_at is None:
            old_last, _ = get_plan_sync_state(plan_id)
            previous_sync_at = old_last
        conn.execute(
            text("""
                INSERT INTO plan_sync_state (planner_plan_id, last_sync_at, previous_sync_at)
                VALUES (:plan_id, :last_sync_at, :previous_sync_at)
                ON CONFLICT (planner_plan_id) DO UPDATE SET
                    previous_sync_at = EXCLUDED.previous_sync_at,
                    last_sync_at = EXCLUDED.last_sync_at
            """),
            {
                "plan_id": plan_id,
                "last_sync_at": last_sync_at.isoformat() if last_sync_at else None,
                "previous_sync_at": previous_sync_at.isoformat() if previous_sync_at else None,
            },
        )
        conn.commit()


def ensure_planner_tasks_table() -> None:
    """Create planner_tasks table and indexes if they do not exist."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS planner_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                planner_task_id VARCHAR(255) NOT NULL,
                planner_plan_id VARCHAR(255) NOT NULL,
                planner_bucket_id VARCHAR(255),
                bucket_name VARCHAR(500),
                title TEXT NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'notStarted',
                percent_complete INTEGER DEFAULT 0 CHECK (percent_complete >= 0 AND percent_complete <= 100),
                due_date TEXT,
                start_date TEXT,
                last_modified_at TEXT,
                assignees TEXT DEFAULT '[]',
                assignee_names TEXT DEFAULT '[]',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (planner_plan_id, planner_task_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_tasks_plan_id ON planner_tasks(planner_plan_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_tasks_status ON planner_tasks(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_tasks_due_date ON planner_tasks(due_date)"))
        conn.commit()


def get_planner_tasks(plan_id: str) -> list[dict[str, Any]]:
    """
    Load tasks for a plan from SQLite. Returns empty list if table missing or no rows.
    """
    try:
        with get_engine().connect() as conn:
            r = conn.execute(
                text("""
                    SELECT planner_task_id, planner_bucket_id, bucket_name, title, status,
                           percent_complete, due_date, start_date, last_modified_at, assignees, assignee_names
                    FROM planner_tasks
                    WHERE planner_plan_id = :plan_id
                    ORDER BY due_date IS NULL, due_date, planner_task_id
                """),
                {"plan_id": plan_id},
            )
            rows = r.fetchall()
    except Exception as e:
        logger.warning("get_planner_tasks failed: %s", e)
        return []
    if not rows:
        return []
    return [_task_row_to_dict(row) for row in rows]


def upsert_planner_tasks(plan_id: str, tasks: list[dict[str, Any]]) -> int:
    """
    Upsert tasks into planner_tasks. Uses ON CONFLICT (planner_plan_id, planner_task_id) DO UPDATE.
    Returns number of rows upserted. Ensures table exists before upserting.
    """
    if not tasks:
        return 0
    ensure_planner_tasks_table()
    engine = get_engine()
    # Parse datetimes
    def _parse_dt(s: str | None):
        if not s:
            return None
        s = (s or "").replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    count = 0
    try:
        with engine.connect() as conn:
            for t in tasks:
                due = _parse_dt(t.get("dueDateTime"))
                start = _parse_dt(t.get("startDateTime"))
                last_mod = _parse_dt(t.get("lastModifiedAt"))
                assignees = t.get("assignees") or []
                assignee_names = t.get("assigneeNames") or assignees
                conn.execute(
                    text("""
                        INSERT INTO planner_tasks (
                            planner_task_id, planner_plan_id, planner_bucket_id, bucket_name,
                            title, status, percent_complete, due_date, start_date, last_modified_at,
                            assignees, assignee_names
                        ) VALUES (
                            :tid, :plan_id, :bucket_id, :bucket_name, :title, :status,
                            :percent_complete, :due_date, :start_date, :last_modified_at,
                            :assignees, :assignee_names
                        )
                        ON CONFLICT (planner_plan_id, planner_task_id) DO UPDATE SET
                            planner_bucket_id = EXCLUDED.planner_bucket_id,
                            bucket_name = EXCLUDED.bucket_name,
                            title = EXCLUDED.title,
                            status = EXCLUDED.status,
                            percent_complete = EXCLUDED.percent_complete,
                            due_date = EXCLUDED.due_date,
                            start_date = EXCLUDED.start_date,
                            last_modified_at = EXCLUDED.last_modified_at,
                            assignees = EXCLUDED.assignees,
                            assignee_names = EXCLUDED.assignee_names
                    """),
                    {
                        "tid": t.get("id", ""),
                        "plan_id": plan_id,
                        "bucket_id": t.get("bucketId") or None,
                        "bucket_name": t.get("bucketName") or None,
                        "title": t.get("title", ""),
                        "status": t.get("status", "notStarted"),
                        "percent_complete": t.get("percentComplete", 0),
                        "due_date": due.isoformat() if due else None,
                        "start_date": start.isoformat() if start else None,
                        "last_modified_at": last_mod.isoformat() if last_mod else None,
                        "assignees": json.dumps(assignees),
                        "assignee_names": json.dumps(assignee_names),
                    },
                )
                count += 1
            conn.commit()
    except Exception as e:
        logger.warning("upsert_planner_tasks failed: %s", e)
        raise
    return count
