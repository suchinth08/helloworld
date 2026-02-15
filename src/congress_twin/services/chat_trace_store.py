"""
Optional trace store for chat (Phase 1 Hybrid).

Stores successful user_query -> intent + response snippet for future few-shot or RAG.
Disabled if chat_trace_store_path is not set; no-op functions when disabled.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from congress_twin.config import get_settings


def _get_trace_db_path() -> Path | None:
    """Path to SQLite file for traces. Uses chat_trace_store_path if set; else default next to sqlite_db_path."""
    settings = get_settings()
    if settings.chat_trace_store_path:
        return Path(settings.chat_trace_store_path)
    # Default: project root / congress_twin.db -> same dir, chat_traces.db
    try:
        db_path = settings.sqlite_db_path
        if not os.path.isabs(db_path):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(project_root, db_path)
        return Path(db_path).parent / "chat_traces.db"
    except Exception:
        return None


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT NOT NULL,
            user_query TEXT NOT NULL,
            intent TEXT NOT NULL,
            entities TEXT,
            response_snippet TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_traces_plan ON chat_traces(plan_id)")
    conn.commit()


def save_trace(
    plan_id: str,
    user_query: str,
    intent: str,
    entities: dict[str, Any] | None = None,
    response_snippet: str | None = None,
) -> None:
    """Append a trace for successful chat turn. No-op if trace store not configured."""
    path = _get_trace_db_path()
    if not path:
        return
    try:
        conn = sqlite3.connect(str(path))
        _ensure_table(conn)
        conn.execute(
            "INSERT INTO chat_traces (plan_id, user_query, intent, entities, response_snippet) VALUES (?, ?, ?, ?, ?)",
            (plan_id, user_query[:2000], intent, json.dumps(entities) if entities else None, (response_snippet or "")[:1000]),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_recent_traces(plan_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return recent traces for plan (for few-shot in LLM prompt). Empty if store disabled."""
    path = _get_trace_db_path()
    if not path or not path.exists():
        return []
    try:
        conn = sqlite3.connect(str(path))
        _ensure_table(conn)
        cur = conn.execute(
            "SELECT user_query, intent, entities, response_snippet FROM chat_traces WHERE plan_id = ? ORDER BY id DESC LIMIT ?",
            (plan_id, limit),
        )
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "user_query": r[0],
                "intent": r[1],
                "entities": json.loads(r[2]) if r[2] else {},
                "response_snippet": r[3],
            }
            for r in rows
        ]
    except Exception:
        return []
