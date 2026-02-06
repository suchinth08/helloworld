"""
External events and agent proposed actions (alerts, HITL approval).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from congress_twin.config import get_settings
from congress_twin.db.planner_repo import get_engine

logger = logging.getLogger(__name__)


def _ensure_tables(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS external_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id VARCHAR(255) NOT NULL,
                event_type VARCHAR(100) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                severity VARCHAR(50) DEFAULT 'medium',
                affected_task_ids TEXT DEFAULT '[]',
                payload TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                acknowledged_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_proposed_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id VARCHAR(255) NOT NULL,
                external_event_id INTEGER,
                task_id VARCHAR(255),
                action_type VARCHAR(100) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                payload TEXT DEFAULT '{}',
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                decided_at TEXT,
                decided_by VARCHAR(255)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_external_events_plan_id ON external_events(plan_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_proposed_actions_plan_id ON agent_proposed_actions(plan_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_proposed_actions_status ON agent_proposed_actions(status)"))
        conn.commit()


def insert_external_event(
    plan_id: str,
    event_type: str,
    title: str,
    description: Optional[str] = None,
    severity: str = "medium",
    affected_task_ids: Optional[list[str]] = None,
    payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    _ensure_tables(get_engine())
    with get_engine().connect() as conn:
        # SQLite doesn't support RETURNING, so insert then fetch
        conn.execute(
            text("""
                INSERT INTO external_events
                (plan_id, event_type, title, description, severity, affected_task_ids, payload)
                VALUES (:plan_id, :event_type, :title, :description, :severity, :affected_task_ids, :payload)
            """),
            {
                "plan_id": plan_id,
                "event_type": event_type,
                "title": title,
                "description": description or "",
                "severity": severity,
                "affected_task_ids": json.dumps(affected_task_ids or []),
                "payload": json.dumps(payload or {}),
            },
        )
        conn.commit()
        # Fetch the inserted row
        event_id = conn.execute(text("SELECT last_insert_rowid()")).scalar()
        r = conn.execute(
            text("""
                SELECT id, plan_id, event_type, title, description, severity,
                       affected_task_ids, payload, created_at, acknowledged_at
                FROM external_events WHERE id = :id
            """),
            {"id": event_id},
        )
        row = r.fetchone()
    return _event_row_to_dict(row)


def _event_row_to_dict(row: Any) -> dict[str, Any]:
    created = getattr(row, "created_at", None)
    ack = getattr(row, "acknowledged_at", None)
    aff = getattr(row, "affected_task_ids", None)
    pl = getattr(row, "payload", None)
    # SQLite stores dates as TEXT, so they're already strings
    def _to_iso(dt: Any) -> str | None:
        if dt is None:
            return None
        if isinstance(dt, str):
            return dt
        if hasattr(dt, "isoformat"):
            return dt.isoformat()
        return str(dt)
    return {
        "id": getattr(row, "id", None),
        "plan_id": getattr(row, "plan_id", ""),
        "event_type": getattr(row, "event_type", ""),
        "title": getattr(row, "title", ""),
        "description": getattr(row, "description", "") or "",
        "severity": getattr(row, "severity", "medium"),
        "affected_task_ids": aff if isinstance(aff, list) else (json.loads(aff) if aff else []),
        "payload": pl if isinstance(pl, dict) else (json.loads(pl) if pl else {}),
        "created_at": _to_iso(created),
        "acknowledged_at": _to_iso(ack),
    }


def get_external_events(plan_id: str, limit: int = 50) -> list[dict[str, Any]]:
    try:
        _ensure_tables(get_engine())
        with get_engine().connect() as conn:
            r = conn.execute(
                text("""
                    SELECT id, plan_id, event_type, title, description, severity,
                           affected_task_ids, payload, created_at, acknowledged_at
                    FROM external_events
                    WHERE plan_id = :plan_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"plan_id": plan_id, "limit": limit},
            )
            return [_event_row_to_dict(row) for row in r]
    except Exception as e:
        logger.warning("get_external_events failed: %s", e)
        return []


def insert_proposed_action(
    plan_id: str,
    action_type: str,
    title: str,
    description: Optional[str] = None,
    task_id: Optional[str] = None,
    external_event_id: Optional[int] = None,
    payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    _ensure_tables(get_engine())
    with get_engine().connect() as conn:
        # SQLite doesn't support RETURNING, so insert then fetch
        conn.execute(
            text("""
                INSERT INTO agent_proposed_actions
                (plan_id, external_event_id, task_id, action_type, title, description, payload)
                VALUES (:plan_id, :external_event_id, :task_id, :action_type, :title, :description, :payload)
            """),
            {
                "plan_id": plan_id,
                "external_event_id": external_event_id,
                "task_id": task_id,
                "action_type": action_type,
                "title": title,
                "description": description or "",
                "payload": json.dumps(payload or {}),
            },
        )
        conn.commit()
        # Fetch the inserted row
        action_id = conn.execute(text("SELECT last_insert_rowid()")).scalar()
        r = conn.execute(
            text("""
                SELECT id, plan_id, external_event_id, task_id, action_type, title, description,
                       payload, status, created_at, decided_at, decided_by
                FROM agent_proposed_actions WHERE id = :id
            """),
            {"id": action_id},
        )
        row = r.fetchone()
    return _action_row_to_dict(row)


def _action_row_to_dict(row: Any) -> dict[str, Any]:
    created = getattr(row, "created_at", None)
    decided = getattr(row, "decided_at", None)
    pl = getattr(row, "payload", None)
    # SQLite stores dates as TEXT, so they're already strings
    def _to_iso(dt: Any) -> str | None:
        if dt is None:
            return None
        if isinstance(dt, str):
            return dt
        if hasattr(dt, "isoformat"):
            return dt.isoformat()
        return str(dt)
    return {
        "id": getattr(row, "id", None),
        "plan_id": getattr(row, "plan_id", ""),
        "external_event_id": getattr(row, "external_event_id", None),
        "task_id": getattr(row, "task_id", None),
        "action_type": getattr(row, "action_type", ""),
        "title": getattr(row, "title", ""),
        "description": getattr(row, "description", "") or "",
        "payload": pl if isinstance(pl, dict) else (json.loads(pl) if pl else {}),
        "status": getattr(row, "status", "pending"),
        "created_at": _to_iso(created),
        "decided_at": _to_iso(decided),
        "decided_by": getattr(row, "decided_by", None),
    }


def get_proposed_actions(plan_id: str, status: Optional[str] = None, limit: int = 100) -> list[dict[str, Any]]:
    try:
        _ensure_tables(get_engine())
        with get_engine().connect() as conn:
            if status:
                r = conn.execute(
                    text("""
                        SELECT id, plan_id, external_event_id, task_id, action_type, title, description,
                               payload, status, created_at, decided_at, decided_by
                        FROM agent_proposed_actions
                        WHERE plan_id = :plan_id AND status = :status
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"plan_id": plan_id, "status": status, "limit": limit},
                )
            else:
                r = conn.execute(
                    text("""
                        SELECT id, plan_id, external_event_id, task_id, action_type, title, description,
                               payload, status, created_at, decided_at, decided_by
                        FROM agent_proposed_actions
                        WHERE plan_id = :plan_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"plan_id": plan_id, "limit": limit},
                )
            return [_action_row_to_dict(row) for row in r]
    except Exception as e:
        logger.warning("get_proposed_actions failed: %s", e)
        return []


def update_proposed_action_status(
    action_id: int,
    plan_id: str,
    status: str,
    decided_by: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if status not in ("approved", "rejected"):
        return None
    try:
        with get_engine().connect() as conn:
            now = datetime.now(timezone.utc)
            conn.execute(
                text("""
                    UPDATE agent_proposed_actions
                    SET status = :status, decided_at = :decided_at, decided_by = :decided_by
                    WHERE id = :id AND plan_id = :plan_id AND status = 'pending'
                """),
                {
                    "id": action_id,
                    "plan_id": plan_id,
                    "status": status,
                    "decided_at": now.isoformat(),
                    "decided_by": decided_by or "",
                },
            )
            r = conn.execute(
                text("""
                    SELECT id, plan_id, external_event_id, task_id, action_type, title, description,
                           payload, status, created_at, decided_at, decided_by
                    FROM agent_proposed_actions WHERE id = :id
                """),
                {"id": action_id},
            )
            row = r.fetchone()
            conn.commit()
            return _action_row_to_dict(row) if row else None
    except Exception as e:
        logger.warning("update_proposed_action_status failed: %s", e)
        return None


def get_proposed_action_by_id(action_id: int, plan_id: str) -> Optional[dict[str, Any]]:
    try:
        with get_engine().connect() as conn:
            r = conn.execute(
                text("""
                    SELECT id, plan_id, external_event_id, task_id, action_type, title, description,
                           payload, status, created_at, decided_at, decided_by
                    FROM agent_proposed_actions WHERE id = :id AND plan_id = :plan_id
                """),
                {"id": action_id, "plan_id": plan_id},
            )
            row = r.fetchone()
            return _action_row_to_dict(row) if row else None
    except Exception:
        return None


def delete_proposed_actions_by_event_id(external_event_id: int) -> int:
    """Delete all proposed actions linked to an external event. Returns count deleted."""
    try:
        with get_engine().connect() as conn:
            r = conn.execute(
                text("DELETE FROM agent_proposed_actions WHERE external_event_id = :eid"),
                {"eid": external_event_id},
            )
            conn.commit()
            return r.rowcount if r.rowcount is not None else 0
    except Exception as e:
        logger.warning("delete_proposed_actions_by_event_id failed: %s", e)
        return 0


def delete_external_event(event_id: int, plan_id: str) -> bool:
    """Delete an external event and its proposed actions. Returns True if event existed and was deleted."""
    try:
        delete_proposed_actions_by_event_id(event_id)
        with get_engine().connect() as conn:
            r = conn.execute(
                text("DELETE FROM external_events WHERE id = :id AND plan_id = :plan_id"),
                {"id": event_id, "plan_id": plan_id},
            )
            conn.commit()
            return r.rowcount > 0 if r.rowcount is not None else False
    except Exception as e:
        logger.warning("delete_external_event failed: %s", e)
        return False


def delete_proposed_action(action_id: int, plan_id: str) -> bool:
    """Delete a single proposed action. Returns True if it existed and was deleted."""
    try:
        with get_engine().connect() as conn:
            r = conn.execute(
                text("DELETE FROM agent_proposed_actions WHERE id = :id AND plan_id = :plan_id"),
                {"id": action_id, "plan_id": plan_id},
            )
            conn.commit()
            return r.rowcount > 0 if r.rowcount is not None else False
    except Exception as e:
        logger.warning("delete_proposed_action failed: %s", e)
        return False
