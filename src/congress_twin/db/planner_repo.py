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
    """Map DB row to API task shape (MS Planner–like: all fields per ACP_05 PDF reference)."""
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
    def _parse_json(s: Any, default: Any = None):
        if s is None:
            return default if default is not None else []
        if isinstance(s, (list, dict)):
            return s
        try:
            return json.loads(s) if s else (default if default is not None else [])
        except (json.JSONDecodeError, TypeError):
            return default if default is not None else []
    
    due = getattr(row, "due_date", None)
    start = getattr(row, "start_date", None)
    last_mod = getattr(row, "last_modified_at", None)
    completed = getattr(row, "completed_date_time", None)
    created = getattr(row, "created_date_time", None)
    raw_a = getattr(row, "assignees", None)
    raw_an = getattr(row, "assignee_names", None)
    assignees = raw_a if isinstance(raw_a, list) else (json.loads(raw_a) if raw_a else [])
    assignee_names = raw_an if isinstance(raw_an, list) else (json.loads(raw_an) if raw_an else [])
    applied_cats = _parse_json(getattr(row, "applied_categories", None), [])
    
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
    # Add new fields (may be None if columns don't exist yet)
    priority = getattr(row, "priority", None)
    if priority is not None:
        out["priority"] = priority
    if completed is not None:
        out["completedDateTime"] = _iso(completed)
    if created is not None:
        out["createdDateTime"] = _iso(created)
    order_hint = getattr(row, "order_hint", None)
    if order_hint is not None:
        out["orderHint"] = order_hint
    assignee_priority = getattr(row, "assignee_priority", None)
    if assignee_priority is not None:
        out["assigneePriority"] = assignee_priority
    if applied_cats:
        out["appliedCategories"] = applied_cats
    conversation_thread = getattr(row, "conversation_thread_id", None)
    if conversation_thread is not None:
        out["conversationThreadId"] = conversation_thread
    description = getattr(row, "description", None)
    if description is not None:
        out["description"] = description
    preview_type = getattr(row, "preview_type", None)
    if preview_type is not None:
        out["previewType"] = preview_type
    created_by = getattr(row, "created_by", None)
    if created_by is not None:
        out["createdBy"] = created_by
    completed_by = getattr(row, "completed_by", None)
    if completed_by is not None:
        out["completedBy"] = completed_by
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


def _to_iso_str(dt: datetime | str | None) -> str | None:
    """Convert datetime or ISO string to ISO format string for SQLite."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def set_plan_sync_state(plan_id: str, last_sync_at: datetime, previous_sync_at: Optional[datetime | str] = None) -> None:
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
                "last_sync_at": _to_iso_str(last_sync_at),
                "previous_sync_at": _to_iso_str(previous_sync_at),
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
    Load tasks for a plan from SQLite with all fields. Returns empty list if table missing or no rows.
    """
    try:
        with get_engine().connect() as conn:
            r = conn.execute(
                text("""
                    SELECT planner_task_id, planner_bucket_id, bucket_name, title, status,
                           percent_complete, due_date, start_date, last_modified_at, assignees, assignee_names,
                           priority, completed_date_time, created_date_time, order_hint, assignee_priority,
                           applied_categories, conversation_thread_id, description, preview_type, created_by, completed_by
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
    Upsert tasks into planner_tasks with all MS Planner fields. Uses ON CONFLICT (planner_plan_id, planner_task_id) DO UPDATE.
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
                completed = _parse_dt(t.get("completedDateTime"))
                created = _parse_dt(t.get("createdDateTime"))
                assignees = t.get("assignees") or []
                assignee_names = t.get("assigneeNames") or assignees
                applied_cats = t.get("appliedCategories") or []
                conn.execute(
                    text("""
                        INSERT INTO planner_tasks (
                            planner_task_id, planner_plan_id, planner_bucket_id, bucket_name,
                            title, status, percent_complete, due_date, start_date, last_modified_at,
                            assignees, assignee_names, priority, completed_date_time, created_date_time,
                            order_hint, assignee_priority, applied_categories, conversation_thread_id,
                            description, preview_type, created_by, completed_by
                        ) VALUES (
                            :tid, :plan_id, :bucket_id, :bucket_name, :title, :status,
                            :percent_complete, :due_date, :start_date, :last_modified_at,
                            :assignees, :assignee_names, :priority, :completed_date_time, :created_date_time,
                            :order_hint, :assignee_priority, :applied_categories, :conversation_thread_id,
                            :description, :preview_type, :created_by, :completed_by
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
                            assignee_names = EXCLUDED.assignee_names,
                            priority = EXCLUDED.priority,
                            completed_date_time = EXCLUDED.completed_date_time,
                            created_date_time = EXCLUDED.created_date_time,
                            order_hint = EXCLUDED.order_hint,
                            assignee_priority = EXCLUDED.assignee_priority,
                            applied_categories = EXCLUDED.applied_categories,
                            conversation_thread_id = EXCLUDED.conversation_thread_id,
                            description = EXCLUDED.description,
                            preview_type = EXCLUDED.preview_type,
                            created_by = EXCLUDED.created_by,
                            completed_by = EXCLUDED.completed_by
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
                        "priority": t.get("priority"),
                        "completed_date_time": completed.isoformat() if completed else None,
                        "created_date_time": created.isoformat() if created else None,
                        "order_hint": t.get("orderHint"),
                        "assignee_priority": t.get("assigneePriority"),
                        "applied_categories": json.dumps(applied_cats),
                        "conversation_thread_id": t.get("conversationThreadId"),
                        "description": t.get("description"),
                        "preview_type": t.get("previewType"),
                        "created_by": t.get("createdBy"),
                        "completed_by": t.get("completedBy"),
                    },
                )
                count += 1
            conn.commit()
    except Exception as e:
        logger.warning("upsert_planner_tasks failed: %s", e)
        raise
    return count


def ensure_planner_task_details_table() -> None:
    """Create planner_task_details table for extended properties (checklist, references)."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS planner_task_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                planner_task_id VARCHAR(255) NOT NULL,
                planner_plan_id VARCHAR(255) NOT NULL,
                checklist_items TEXT DEFAULT '[]',
                references TEXT DEFAULT '[]',
                last_modified_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (planner_plan_id, planner_task_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_task_details_task ON planner_task_details(planner_plan_id, planner_task_id)"))
        conn.commit()


def ensure_planner_task_dependencies_table() -> None:
    """Create planner_task_dependencies table for explicit task dependencies."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS planner_task_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                planner_plan_id VARCHAR(255) NOT NULL,
                task_id VARCHAR(255) NOT NULL,
                depends_on_task_id VARCHAR(255) NOT NULL,
                dependency_type VARCHAR(10) DEFAULT 'FS',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (planner_plan_id, task_id, depends_on_task_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_task_dependencies_task ON planner_task_dependencies(planner_plan_id, task_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_task_dependencies_depends_on ON planner_task_dependencies(planner_plan_id, depends_on_task_id)"))
        conn.commit()


def upsert_planner_task_details(plan_id: str, task_id: str, details: dict[str, Any]) -> None:
    """
    Upsert task details (checklist, references) for a task.
    """
    ensure_planner_task_details_table()
    engine = get_engine()
    checklist = details.get("checklist") or []
    references = details.get("references") or []
    last_mod = _to_iso_str(details.get("lastModifiedAt"))
    
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO planner_task_details (
                    planner_task_id, planner_plan_id, checklist_items, references, last_modified_at
                ) VALUES (
                    :task_id, :plan_id, :checklist_items, :references, :last_modified_at
                )
                ON CONFLICT (planner_plan_id, planner_task_id) DO UPDATE SET
                    checklist_items = EXCLUDED.checklist_items,
                    references = EXCLUDED.references,
                    last_modified_at = EXCLUDED.last_modified_at
            """),
            {
                "task_id": task_id,
                "plan_id": plan_id,
                "checklist_items": json.dumps(checklist),
                "references": json.dumps(references),
                "last_modified_at": last_mod,
            },
        )
        conn.commit()


def get_planner_task_details(plan_id: str, task_id: str) -> dict[str, Any] | None:
    """Get task details (checklist, references) for a task."""
    ensure_planner_task_details_table()
    try:
        with get_engine().connect() as conn:
            r = conn.execute(
                text("""
                    SELECT checklist_items, references, last_modified_at
                    FROM planner_task_details
                    WHERE planner_plan_id = :plan_id AND planner_task_id = :task_id
                """),
                {"plan_id": plan_id, "task_id": task_id},
            )
            row = r.fetchone()
    except Exception as e:
        logger.warning("get_planner_task_details failed: %s", e)
        return None
    if not row:
        return None
    return {
        "checklist": json.loads(getattr(row, "checklist_items", "[]") or "[]"),
        "references": json.loads(getattr(row, "references", "[]") or "[]"),
        "lastModifiedAt": getattr(row, "last_modified_at", None),
    }


def upsert_planner_task_dependencies(plan_id: str, task_id: str, dependencies: list[dict[str, Any]]) -> int:
    """
    Upsert task dependencies. dependencies is a list of {dependsOnTaskId, dependencyType}.
    Returns number of dependencies upserted.
    """
    ensure_planner_task_dependencies_table()
    engine = get_engine()
    count = 0
    try:
        with engine.connect() as conn:
            # Delete existing dependencies for this task
            conn.execute(
                text("DELETE FROM planner_task_dependencies WHERE planner_plan_id = :plan_id AND task_id = :task_id"),
                {"plan_id": plan_id, "task_id": task_id},
            )
            # Insert new dependencies
            for dep in dependencies:
                dep_task_id = dep.get("dependsOnTaskId") or dep.get("depends_on_task_id")
                dep_type = dep.get("dependencyType") or dep.get("dependency_type") or "FS"
                if dep_task_id:
                    conn.execute(
                        text("""
                            INSERT INTO planner_task_dependencies (
                                planner_plan_id, task_id, depends_on_task_id, dependency_type
                            ) VALUES (
                                :plan_id, :task_id, :depends_on_task_id, :dependency_type
                            )
                        """),
                        {
                            "plan_id": plan_id,
                            "task_id": task_id,
                            "depends_on_task_id": dep_task_id,
                            "dependency_type": dep_type,
                        },
                    )
                    count += 1
            conn.commit()
    except Exception as e:
        logger.warning("upsert_planner_task_dependencies failed: %s", e)
        raise
    return count


def get_planner_task_dependencies(plan_id: str, task_id: str | None = None) -> list[dict[str, Any]]:
    """
    Get task dependencies for a plan. If task_id provided, return only dependencies for that task.
    Returns list of {taskId, dependsOnTaskId, dependencyType}.
    """
    ensure_planner_task_dependencies_table()
    try:
        with get_engine().connect() as conn:
            if task_id:
                r = conn.execute(
                    text("""
                        SELECT task_id, depends_on_task_id, dependency_type
                        FROM planner_task_dependencies
                        WHERE planner_plan_id = :plan_id AND task_id = :task_id
                    """),
                    {"plan_id": plan_id, "task_id": task_id},
                )
            else:
                r = conn.execute(
                    text("""
                        SELECT task_id, depends_on_task_id, dependency_type
                        FROM planner_task_dependencies
                        WHERE planner_plan_id = :plan_id
                    """),
                    {"plan_id": plan_id},
                )
            rows = r.fetchall()
    except Exception as e:
        logger.warning("get_planner_task_dependencies failed: %s", e)
        return []
    return [
        {
            "taskId": getattr(row, "task_id", ""),
            "dependsOnTaskId": getattr(row, "depends_on_task_id", ""),
            "dependencyType": getattr(row, "dependency_type", "FS"),
        }
        for row in rows
    ]


def get_planner_task_with_details(plan_id: str, task_id: str) -> dict[str, Any] | None:
    """
    Get a single task with all details (checklist, references, dependencies).
    Returns None if task not found.
    """
    tasks = get_planner_tasks(plan_id)
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        return None
    
    # Add task details
    details = get_planner_task_details(plan_id, task_id)
    if details:
        task["checklist"] = details.get("checklist", [])
        task["references"] = details.get("references", [])
    
    # Add dependencies
    deps = get_planner_task_dependencies(plan_id, task_id)
    task["dependencies"] = deps
    
    return task
