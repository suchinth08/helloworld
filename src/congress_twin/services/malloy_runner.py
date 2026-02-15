"""
Malloy semantic layer runner for Congress Twin.

Exports plan tasks and dependencies to DuckDB, then runs Malloy queries for
analytical questions (e.g. "completion by bucket", "tasks by status").
Requires optional deps: uv pip install -e ".[malloy]"
"""

import asyncio
import json
import logging
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default model path (project root semantic_layer.malloy)
_MODEL_PATH = Path(__file__).resolve().parents[3] / "semantic_layer.malloy"


def _export_plan_to_duckdb(
    plan_id: str,
    tasks: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    duckdb_path: Path,
) -> None:
    """Write tasks and dependencies to a DuckDB file for Malloy."""
    try:
        import duckdb
    except ImportError:
        raise RuntimeError("duckdb not installed. Install with: uv pip install duckdb")

    conn = duckdb.connect(str(duckdb_path))

    def _str(x: Any) -> str:
        if x is None:
            return ""
        return str(x) if not isinstance(x, str) else x

    conn.execute("DROP TABLE IF EXISTS tasks")
    conn.execute("""
        CREATE TABLE tasks (
            planner_task_id VARCHAR,
            planner_plan_id VARCHAR,
            bucket_id VARCHAR,
            bucket_name VARCHAR,
            title VARCHAR,
            status VARCHAR,
            percent_complete INTEGER,
            due_date VARCHAR,
            start_date VARCHAR,
            assignee_names VARCHAR
        )
    """)
    for t in tasks:
        row = (
            _str(t.get("id")),
            plan_id,
            _str(t.get("bucketId")),
            _str(t.get("bucketName")),
            _str(t.get("title")),
            _str(t.get("status") or "notStarted"),
            int(t.get("percentComplete") or 0),
            _str(t.get("dueDateTime")),
            _str(t.get("startDateTime")),
            json.dumps(t.get("assigneeNames") or []),
        )
        conn.execute("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", list(row))

    conn.execute("DROP TABLE IF EXISTS dependencies")
    conn.execute("""
        CREATE TABLE dependencies (
            planner_plan_id VARCHAR,
            task_id VARCHAR,
            depends_on_task_id VARCHAR,
            dependency_type VARCHAR
        )
    """)
    for d in dependencies:
        dep_row = (
            plan_id,
            _str(d.get("taskId") or d.get("task_id")),
            _str(d.get("dependsOnTaskId") or d.get("depends_on_task_id")),
            _str(d.get("dependencyType") or d.get("dependency_type") or "FS"),
        )
        conn.execute("INSERT INTO dependencies VALUES (?, ?, ?, ?)", list(dep_row))

    conn.close()


# SQL equivalents of Malloy named queries (DuckDB-only path; Malloy connection often hits wrong catalog)
_NAMED_QUERY_SQL: dict[str, str] = {
    "completion_by_bucket": """
        SELECT bucket_name,
               COUNT(*) AS task_count,
               SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_count,
               ROUND(100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS completion_pct
        FROM tasks
        GROUP BY bucket_name
        ORDER BY bucket_name
    """,
    "tasks_by_status": """
        SELECT status, COUNT(*) AS task_count
        FROM tasks
        GROUP BY status
        ORDER BY task_count DESC
    """,
    "tasks_by_assignee": """
        SELECT assignee_names, COUNT(*) AS task_count
        FROM tasks
        GROUP BY assignee_names
        ORDER BY task_count DESC
    """,
    "incomplete_by_bucket": """
        SELECT bucket_name, COUNT(*) AS task_count
        FROM tasks
        WHERE status != 'completed'
        GROUP BY bucket_name
        ORDER BY task_count DESC
    """,
    "plan_summary": """
        SELECT COUNT(*) AS task_count,
               SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_count,
               ROUND(100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS completion_pct
        FROM tasks
    """,
    "top_buckets_by_count": """
        SELECT bucket_name, COUNT(*) AS task_count
        FROM tasks
        GROUP BY bucket_name
        ORDER BY task_count DESC
    """,
}


def _run_duckdb_named_query(duckdb_path: Path, named_query: str) -> list[dict[str, Any]]:
    """Run a known named query as SQL against our DuckDB file. Returns list of dicts."""
    sql = _NAMED_QUERY_SQL.get(named_query)
    if not sql:
        return []
    try:
        import duckdb
        conn = duckdb.connect(str(duckdb_path), read_only=True)
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = [dict(zip(columns, r)) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.warning("malloy_runner: DuckDB SQL for %s failed: %s", named_query, e)
        return []


def run_malloy_query(
    plan_id: str,
    tasks: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    malloy_query: str = "",
    model_path: Path | None = None,
    named_query: str | None = None,
) -> list[dict[str, Any]] | None:
    """
    Export plan data to DuckDB and run an analytical query. Returns list of dicts or None on failure.
    For known named_query (completion_by_bucket, tasks_by_status, etc.) uses DuckDB SQL directly so
    analytics work without relying on Malloy's connection (which can hit the wrong catalog).
    """
    try:
        import duckdb
    except ImportError:
        logger.warning("malloy_runner: duckdb not installed. Install with: pip install duckdb")
        return None

    logger.info(
        "malloy_runner: Running analytical query (plan_id=%s, tasks=%s, named_query=%s)",
        plan_id,
        len(tasks),
        named_query or "(inline)",
    )
    with tempfile.TemporaryDirectory(prefix="congress_twin_malloy_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        duckdb_path = tmpdir_path / "data.duckdb"
        _export_plan_to_duckdb(plan_id, tasks, dependencies, duckdb_path)
        logger.info("malloy_runner: Exported %s tasks, %s dependencies to DuckDB", len(tasks), len(dependencies))

        # Prefer DuckDB SQL for known named queries (avoids Malloy connection issues)
        if named_query and named_query in _NAMED_QUERY_SQL:
            rows = _run_duckdb_named_query(duckdb_path, named_query)
            logger.info("malloy_runner: DuckDB SQL returned %s row(s)", len(rows))
            return rows if rows is not None else []

        # Inline or unknown query: try Malloy if available
        try:
            import malloy
            from malloy.data.duckdb import DuckDbConnection
        except ImportError:
            logger.info("malloy_runner: Malloy not installed; only named_query analytics are supported")
            return []

        model_path = model_path or _MODEL_PATH
        if not model_path.exists():
            return []
        model_in_tmp = tmpdir_path / "semantic_layer.malloy"
        shutil.copy2(model_path, model_in_tmp)
        home_dir = str(tmpdir_path)

        async def _run() -> list[dict[str, Any]]:
            with malloy.Runtime() as runtime:
                runtime.add_connection(DuckDbConnection(home_dir=home_dir))
                loaded = runtime.load_file(str(model_in_tmp))
                if named_query:
                    data = await loaded.run(named_query=named_query)
                else:
                    data = await loaded.run(query=malloy_query or "run: planner_tasks -> { limit: 1 }")
                if data is None:
                    return []
                df = data.to_dataframe()
                return df.to_dict("records") if df is not None else []

        def _run_in_thread() -> list[dict[str, Any]]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_run())
            finally:
                loop.close()

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_in_thread)
                return future.result(timeout=60)
        except Exception as e:
            logger.warning("malloy_runner: Malloy query failed: %s", e)
            return None
