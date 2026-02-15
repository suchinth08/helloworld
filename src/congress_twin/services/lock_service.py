"""
Lock service: Task-level locks for concurrent editing.

Acquire lock when user opens task for edit, release on save/cancel.
TTL: auto-release after 15 minutes.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from congress_twin.config import get_settings
from congress_twin.db.planner_repo import get_engine

LOCK_TTL_MINUTES = 15


def _ensure_task_locks_table() -> None:
    if get_settings().is_postgres:
        return
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS task_locks (
                plan_id VARCHAR(255) NOT NULL,
                task_id VARCHAR(255) NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                locked_at TEXT NOT NULL,
                PRIMARY KEY (plan_id, task_id)
            )
        """))
        conn.commit()


def acquire_lock(plan_id: str, task_id: str, user_id: str) -> tuple[bool, Optional[str]]:
    """
    Acquire lock for a task. Returns (success, locked_by_user_id_if_failed).
    """
    from sqlalchemy import text
    _ensure_task_locks_table()
    engine = get_engine()
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        r = conn.execute(
            text("SELECT user_id, locked_at FROM task_locks WHERE plan_id = :plan_id AND task_id = :task_id"),
            {"plan_id": plan_id, "task_id": task_id},
        )
        row = r.fetchone()
        if row:
            locked_by = getattr(row, "user_id", "")
            locked_at_s = getattr(row, "locked_at", "")
            try:
                locked_at = datetime.fromisoformat(locked_at_s.replace("Z", "+00:00"))
                if locked_at.tzinfo is None:
                    locked_at = locked_at.replace(tzinfo=timezone.utc)
                if now - locked_at > timedelta(minutes=LOCK_TTL_MINUTES):
                    # Expired, take over
                    conn.execute(
                        text("""
                            INSERT OR REPLACE INTO task_locks (plan_id, task_id, user_id, locked_at)
                            VALUES (:plan_id, :task_id, :user_id, :locked_at)
                        """),
                        {"plan_id": plan_id, "task_id": task_id, "user_id": user_id, "locked_at": now.isoformat()},
                    )
                    conn.commit()
                    return True, None
            except (ValueError, TypeError):
                pass
            if locked_by != user_id:
                return False, locked_by
        conn.execute(
            text("""
                INSERT OR REPLACE INTO task_locks (plan_id, task_id, user_id, locked_at)
                VALUES (:plan_id, :task_id, :user_id, :locked_at)
            """),
            {"plan_id": plan_id, "task_id": task_id, "user_id": user_id, "locked_at": now.isoformat()},
        )
        conn.commit()
    return True, None


def release_lock(plan_id: str, task_id: str, user_id: str) -> bool:
    """Release lock. Returns True if released."""
    from sqlalchemy import text
    _ensure_task_locks_table()
    engine = get_engine()
    with engine.connect() as conn:
        r = conn.execute(
            text("DELETE FROM task_locks WHERE plan_id = :plan_id AND task_id = :task_id AND user_id = :user_id"),
            {"plan_id": plan_id, "task_id": task_id, "user_id": user_id},
        )
        conn.commit()
        return r.rowcount is not None and r.rowcount > 0


def get_lock(plan_id: str, task_id: str) -> Optional[dict]:
    """Get lock info if any. Returns {user_id, locked_at} or None."""
    from sqlalchemy import text
    _ensure_task_locks_table()
    engine = get_engine()
    with engine.connect() as conn:
        r = conn.execute(
            text("SELECT user_id, locked_at FROM task_locks WHERE plan_id = :plan_id AND task_id = :task_id"),
            {"plan_id": plan_id, "task_id": task_id},
        )
        row = r.fetchone()
    if not row:
        return None
    return {"user_id": getattr(row, "user_id", ""), "locked_at": getattr(row, "locked_at", "")}
