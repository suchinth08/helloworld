"""
Planner tasks repository: read/write normalized tasks.
Uses PostgreSQL when configured (shared infra), else SQLite.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

from congress_twin.config import get_settings

try:
    from psycopg2.extras import Json as PgJson
except ImportError:
    PgJson = None  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)

_engine: Optional[Engine] = None
_postgres_schema_ensured: bool = False


def _json_param(val: list | dict | None) -> Any:
    """Return value suitable for DB: json.dumps for SQLite TEXT; psycopg2 Json for Postgres JSONB (avoids list→ARRAY)."""
    if val is None:
        return None
    if get_settings().is_postgres and PgJson is not None:
        return PgJson(val if val else [])
    return json.dumps(val) if val else "[]"


def _parse_json_read(s: Any, default: Any = None) -> Any:
    """Parse JSON from DB: Postgres returns list/dict; SQLite returns str."""
    if s is None:
        return default if default is not None else []
    if isinstance(s, (list, dict)):
        return s
    try:
        return json.loads(s) if s else (default if default is not None else [])
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        conn_str = settings.database_url
        if settings.is_postgres:
            _engine = create_engine(conn_str)
            schema = settings.postgres_schema

            @event.listens_for(_engine, "connect")
            def set_postgres_search_path(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute(f'SET search_path TO "{schema}"')
                cursor.close()
        else:
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


def ensure_planner_plans_table() -> None:
    """Create planner_plans table if not exist. For PostgreSQL, ensures schema via _ensure_postgres_schema."""
    if get_settings().is_postgres:
        _ensure_postgres_schema()
        return
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS planner_plans (
                plan_id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(500),
                congress_date TEXT,
                source_plan_id VARCHAR(255),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()


def list_planner_plans() -> list[dict[str, Any]]:
    """List all plans from DB. Returns list of {plan_id, name, congress_date, source_plan_id, created_at}."""
    ensure_planner_plans_table()
    try:
        with get_engine().connect() as conn:
            r = conn.execute(
                text("SELECT plan_id, name, congress_date, source_plan_id, created_at FROM planner_plans ORDER BY created_at DESC"),
            )
            rows = r.fetchall()
    except Exception as e:
        logger.warning("list_planner_plans failed: %s", e)
        return []
    return [
        {
            "plan_id": getattr(row, "plan_id", ""),
            "name": getattr(row, "name", "") or "",
            "congress_date": getattr(row, "congress_date"),
            "source_plan_id": getattr(row, "source_plan_id"),
            "created_at": getattr(row, "created_at"),
        }
        for row in rows
    ]


def upsert_planner_plan(
    plan_id: str,
    name: Optional[str] = None,
    congress_date: Optional[datetime] = None,
    source_plan_id: Optional[str] = None,
) -> None:
    """Insert or update a plan in planner_plans."""
    ensure_planner_plans_table()
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO planner_plans (plan_id, name, congress_date, source_plan_id)
                VALUES (:plan_id, :name, :congress_date, :source_plan_id)
                ON CONFLICT (plan_id) DO UPDATE SET
                    name = COALESCE(EXCLUDED.name, planner_plans.name),
                    congress_date = COALESCE(EXCLUDED.congress_date, planner_plans.congress_date),
                    source_plan_id = COALESCE(EXCLUDED.source_plan_id, planner_plans.source_plan_id)
            """),
            {
                "plan_id": plan_id,
                "name": name or plan_id,
                "congress_date": congress_date.isoformat() if congress_date else None,
                "source_plan_id": source_plan_id,
            },
        )
        conn.commit()


def ensure_plan_sync_state_table() -> None:
    """Create plan_sync_state table if it does not exist. No-op when using PostgreSQL (schema from init script)."""
    if get_settings().is_postgres:
        return
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


def _ensure_postgres_schema() -> None:
    """Create schema, planner_plans, planner_task_dependencies, and ensure planner_tasks has all columns. Idempotent."""
    global _postgres_schema_ensured
    if not get_settings().is_postgres or _postgres_schema_ensured:
        return
    settings = get_settings()
    schema = settings.postgres_schema
    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS planner_plans (
                    plan_id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(500),
                    congress_date TIMESTAMP WITH TIME ZONE,
                    source_plan_id VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS planner_task_dependencies (
                    id SERIAL PRIMARY KEY,
                    planner_plan_id VARCHAR(255) NOT NULL,
                    task_id VARCHAR(255) NOT NULL,
                    depends_on_task_id VARCHAR(255) NOT NULL,
                    dependency_type VARCHAR(10) DEFAULT 'FS',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE (planner_plan_id, task_id, depends_on_task_id)
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_task_dependencies_task ON planner_task_dependencies(planner_plan_id, task_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_task_dependencies_depends_on ON planner_task_dependencies(planner_plan_id, depends_on_task_id)"))
            # planner_tasks: create if missing, else add missing columns
            r = conn.execute(text("""
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = current_schema() AND table_name = 'planner_tasks'
            """))
            if r.scalar() is None:
                conn.execute(text("""
                    CREATE TABLE planner_tasks (
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
                        priority INTEGER,
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
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_tasks_plan_id ON planner_tasks(planner_plan_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_tasks_status ON planner_tasks(status)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_tasks_due_date ON planner_tasks(due_date)"))
            else:
                for col, ddl in [
                    ("start_date", "ADD COLUMN start_date TIMESTAMP WITH TIME ZONE"),
                    ("priority", "ADD COLUMN priority INTEGER"),
                    ("completed_date_time", "ADD COLUMN completed_date_time TIMESTAMP WITH TIME ZONE"),
                    ("created_date_time", "ADD COLUMN created_date_time TIMESTAMP WITH TIME ZONE"),
                    ("order_hint", "ADD COLUMN order_hint TEXT"),
                    ("assignee_priority", "ADD COLUMN assignee_priority TEXT"),
                    ("applied_categories", "ADD COLUMN applied_categories JSONB DEFAULT '[]'"),
                    ("conversation_thread_id", "ADD COLUMN conversation_thread_id TEXT"),
                    ("description", "ADD COLUMN description TEXT"),
                    ("preview_type", "ADD COLUMN preview_type TEXT"),
                    ("created_by", "ADD COLUMN created_by TEXT"),
                    ("completed_by", "ADD COLUMN completed_by TEXT"),
                ]:
                    check = conn.execute(text("""
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = current_schema() AND table_name = 'planner_tasks' AND column_name = :col
                    """), {"col": col})
                    if check.scalar() is None:
                        conn.execute(text(f"ALTER TABLE planner_tasks {ddl}"))
            conn.commit()
        _postgres_schema_ensured = True
    except Exception as e:
        logger.warning("_ensure_postgres_schema failed (will retry next call): %s", e)


def ensure_planner_tasks_table() -> None:
    """Create planner_tasks table and indexes if they do not exist. For PostgreSQL, ensures schema and missing columns."""
    if get_settings().is_postgres:
        _ensure_postgres_schema()
        return
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
                priority INTEGER,
                completed_date_time TEXT,
                created_date_time TEXT,
                order_hint TEXT,
                assignee_priority TEXT,
                applied_categories TEXT DEFAULT '[]',
                conversation_thread_id TEXT,
                description TEXT,
                preview_type TEXT,
                created_by TEXT,
                completed_by TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (planner_plan_id, planner_task_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_tasks_plan_id ON planner_tasks(planner_plan_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_tasks_status ON planner_tasks(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_tasks_due_date ON planner_tasks(due_date)"))
        # Add extended columns if missing (migration 004)
        for col_def in [
            "priority INTEGER",
            "completed_date_time TEXT",
            "created_date_time TEXT",
            "order_hint TEXT",
            "assignee_priority TEXT",
            "applied_categories TEXT DEFAULT '[]'",
            "conversation_thread_id TEXT",
            "description TEXT",
            "preview_type TEXT",
            "created_by TEXT",
            "completed_by TEXT",
        ]:
            col_name = col_def.split()[0]
            try:
                conn.execute(text(f"ALTER TABLE planner_tasks ADD COLUMN {col_def}"))
            except Exception:
                pass  # Column already exists
        conn.commit()


def get_planner_tasks(plan_id: str) -> list[dict[str, Any]]:
    """
    Load tasks for a plan from SQLite with all fields. Returns empty list if table missing or no rows.
    When using SQLite, ensures table and extended columns exist (migration) before SELECT.
    """
    if not get_settings().is_postgres:
        ensure_planner_tasks_table()
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
                        "assignees": _json_param(assignees),
                        "assignee_names": _json_param(assignee_names),
                        "priority": t.get("priority"),
                        "completed_date_time": completed.isoformat() if completed else None,
                        "created_date_time": created.isoformat() if created else None,
                        "order_hint": t.get("orderHint"),
                        "assignee_priority": t.get("assigneePriority"),
                        "applied_categories": _json_param(applied_cats),
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
    """Create planner_task_details table for extended properties. No-op when using PostgreSQL."""
    if get_settings().is_postgres:
        return
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS planner_task_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                planner_task_id VARCHAR(255) NOT NULL,
                planner_plan_id VARCHAR(255) NOT NULL,
                checklist_items TEXT DEFAULT '[]',
                "references" TEXT DEFAULT '[]',
                last_modified_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (planner_plan_id, planner_task_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planner_task_details_task ON planner_task_details(planner_plan_id, planner_task_id)"))
        conn.commit()


def ensure_planner_task_dependencies_table() -> None:
    """Create planner_task_dependencies table for explicit task dependencies. For PostgreSQL, ensures schema via _ensure_postgres_schema."""
    if get_settings().is_postgres:
        _ensure_postgres_schema()
        return
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
                    planner_task_id, planner_plan_id, checklist_items, "references", last_modified_at
                ) VALUES (
                    :task_id, :plan_id, :checklist_items, :references, :last_modified_at
                )
                ON CONFLICT (planner_plan_id, planner_task_id) DO UPDATE SET
                    checklist_items = EXCLUDED.checklist_items,
                    "references" = EXCLUDED."references",
                    last_modified_at = EXCLUDED.last_modified_at
            """),
            {
                "task_id": task_id,
                "plan_id": plan_id,
                "checklist_items": _json_param(checklist),
                "references": _json_param(references),
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
                    SELECT checklist_items, "references", last_modified_at
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
        "checklist": _parse_json_read(getattr(row, "checklist_items", None), []),
        "references": _parse_json_read(getattr(row, "references", None), []),
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


def create_planner_task(plan_id: str, task: dict[str, Any]) -> dict[str, Any]:
    """
    Create a new task in planner_tasks. task must include title, bucketId.
    Returns the created task with id, checklist, dependencies.
    """
    import uuid
    ensure_planner_tasks_table()
    engine = get_engine()
    task_id = task.get("id") or f"task-{uuid.uuid4().hex[:8]}"
    due = _parse_dt_from_task(task.get("dueDateTime"))
    start = _parse_dt_from_task(task.get("startDateTime"))
    now_str = datetime.now().isoformat()
    assignees = task.get("assignees") or []
    assignee_names = task.get("assigneeNames") or assignees
    applied_cats = task.get("appliedCategories") or []

    with engine.connect() as conn:
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
            """),
            {
                "tid": task_id,
                "plan_id": plan_id,
                "bucket_id": task.get("bucketId") or None,
                "bucket_name": task.get("bucketName") or None,
                "title": task.get("title", ""),
                "status": task.get("status", "notStarted"),
                "percent_complete": task.get("percentComplete", 0),
                "due_date": due.isoformat() if due else None,
                "start_date": start.isoformat() if start else None,
                "last_modified_at": now_str,
                "assignees": _json_param(assignees),
                "assignee_names": _json_param(assignee_names),
                "priority": task.get("priority"),
                "completed_date_time": None,
                "created_date_time": now_str,
                "order_hint": task.get("orderHint"),
                "assignee_priority": task.get("assigneePriority"),
                "applied_categories": _json_param(applied_cats),
                "conversation_thread_id": task.get("conversationThreadId"),
                "description": task.get("description"),
                "preview_type": task.get("previewType"),
                "created_by": task.get("createdBy"),
                "completed_by": None,
            },
        )
        conn.commit()

    return get_planner_task_with_details(plan_id, task_id) or {}


def _parse_dt_from_task(val: str | None) -> datetime | None:
    """Parse datetime from task payload."""
    if not val:
        return None
    s = (val or "").replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def update_planner_task(plan_id: str, task_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """
    Partially update a task. Only provided fields are updated.
    Returns updated task or None if not found.
    """
    existing = get_planner_tasks(plan_id)
    if not any(t.get("id") == task_id for t in existing):
        return None

    ensure_planner_tasks_table()
    engine = get_engine()

    # Build dynamic SET clause for provided fields
    set_parts: list[str] = []
    params: dict[str, Any] = {"task_id": task_id, "plan_id": plan_id}

    if "title" in updates:
        set_parts.append("title = :title")
        params["title"] = updates["title"]
    if "bucketId" in updates:
        set_parts.append("planner_bucket_id = :bucket_id")
        params["bucket_id"] = updates["bucketId"]
    if "bucketName" in updates:
        set_parts.append("bucket_name = :bucket_name")
        params["bucket_name"] = updates["bucketName"]
    if "status" in updates:
        set_parts.append("status = :status")
        params["status"] = updates["status"]
    if "percentComplete" in updates:
        set_parts.append("percent_complete = :percent_complete")
        params["percent_complete"] = updates["percentComplete"]
    if "dueDateTime" in updates:
        due = _parse_dt_from_task(updates["dueDateTime"])
        set_parts.append("due_date = :due_date")
        params["due_date"] = due.isoformat() if due else None
    if "startDateTime" in updates:
        start = _parse_dt_from_task(updates["startDateTime"])
        set_parts.append("start_date = :start_date")
        params["start_date"] = start.isoformat() if start else None
    if "assignees" in updates:
        set_parts.append("assignees = :assignees")
        params["assignees"] = _json_param(updates["assignees"] or [])
    if "assigneeNames" in updates:
        set_parts.append("assignee_names = :assignee_names")
        params["assignee_names"] = _json_param(updates["assigneeNames"] or [])
    if "priority" in updates:
        set_parts.append("priority = :priority")
        params["priority"] = updates["priority"]
    if "description" in updates:
        set_parts.append("description = :description")
        params["description"] = updates["description"]

    set_parts.append("last_modified_at = :last_modified_at")
    params["last_modified_at"] = datetime.now().isoformat()

    if not set_parts:
        return get_planner_task_with_details(plan_id, task_id)

    with engine.connect() as conn:
        conn.execute(
            text(f"""
                UPDATE planner_tasks
                SET {", ".join(set_parts)}
                WHERE planner_plan_id = :plan_id AND planner_task_id = :task_id
            """),
            params,
        )
        conn.commit()

    return get_planner_task_with_details(plan_id, task_id)


def delete_planner_task(plan_id: str, task_id: str) -> bool:
    """Delete a task and its details, dependencies. Returns True if deleted."""
    ensure_planner_tasks_table()
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM planner_task_details WHERE planner_plan_id = :plan_id AND planner_task_id = :task_id"),
            {"plan_id": plan_id, "task_id": task_id},
        )
        conn.execute(
            text("DELETE FROM planner_task_dependencies WHERE planner_plan_id = :plan_id AND (task_id = :task_id OR depends_on_task_id = :task_id)"),
            {"plan_id": plan_id, "task_id": task_id},
        )
        r = conn.execute(
            text("DELETE FROM planner_tasks WHERE planner_plan_id = :plan_id AND planner_task_id = :task_id"),
            {"plan_id": plan_id, "task_id": task_id},
        )
        conn.commit()
        return r.rowcount and r.rowcount > 0


def upsert_checklist_item(plan_id: str, task_id: str, item: dict[str, Any]) -> dict[str, Any]:
    """
    Add or update a checklist item (subtask). item: {id?, title, isChecked?, orderHint?}.
    If id not provided, generates one. Returns the full checklist.
    """
    import uuid
    details = get_planner_task_details(plan_id, task_id)
    checklist = list(details.get("checklist", [])) if details else []
    item_id = item.get("id") or f"checklist-{uuid.uuid4().hex[:8]}"
    new_item = {
        "id": item_id,
        "title": item.get("title", ""),
        "isChecked": item.get("isChecked", False),
        "orderHint": item.get("orderHint", ""),
    }
    # Update existing or append
    found = False
    for i, c in enumerate(checklist):
        if isinstance(c, dict) and c.get("id") == item_id:
            checklist[i] = {**c, **new_item}
            found = True
            break
    if not found:
        checklist.append(new_item)

    ensure_planner_task_details_table()
    upsert_planner_task_details(plan_id, task_id, {
        "checklist": checklist,
        "references": details.get("references", []) if details else [],
        "lastModifiedAt": datetime.now().isoformat(),
    })
    return new_item


def delete_checklist_item(plan_id: str, task_id: str, subtask_id: str) -> bool:
    """Remove a checklist item by id. Returns True if removed."""
    details = get_planner_task_details(plan_id, task_id)
    if not details:
        return False
    checklist = list(details.get("checklist", []))
    original_len = len(checklist)
    checklist = [c for c in checklist if not (isinstance(c, dict) and c.get("id") == subtask_id)]
    if len(checklist) == original_len:
        return False
    ensure_planner_task_details_table()
    upsert_planner_task_details(plan_id, task_id, {
        "checklist": checklist,
        "references": details.get("references", []),
        "lastModifiedAt": datetime.now().isoformat(),
    })
    return True


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
