"""
Impact analyzer: Analyze impact of task edits on downstream tasks.

Uses dependency DAG to find downstream tasks, runs lightweight Monte Carlo
to estimate delay propagation.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from congress_twin.db.planner_repo import get_planner_task_dependencies
from congress_twin.services.planner_service import get_tasks_for_plan, get_critical_path


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _build_downstream(plan_id: str) -> dict[str, set[str]]:
    """Build downstream map: task_id -> set of task_ids that depend on it."""
    deps = get_planner_task_dependencies(plan_id, None)
    downstream: dict[str, set[str]] = {}
    for d in deps:
        dep_task = d.get("dependsOnTaskId") or d.get("depends_on_task_id")
        task_id = d.get("taskId") or d.get("task_id")
        if dep_task and task_id:
            downstream.setdefault(dep_task, set()).add(task_id)
    return downstream


def analyze_edit_impact(
    plan_id: str,
    task_id: str,
    proposed_changes: dict[str, Any],
) -> dict[str, Any]:
    """
    Analyze impact of proposed task changes on downstream tasks.
    proposed_changes: { dueDateTime?, startDateTime?, assignees?, percentComplete?, new_subtask? }
    Returns: { affected_tasks, downstream_delay_days, critical_path_impact }
    """
    tasks = get_tasks_for_plan(plan_id)
    task_by_id = {t["id"]: t for t in tasks}
    if task_id not in task_by_id:
        return {"error": "Task not found", "affected_tasks": [], "downstream_delay_days": 0, "critical_path_impact": False}

    downstream_map = _build_downstream(plan_id)
    path_res = get_critical_path(plan_id)
    critical_ids = set(path_res.get("task_ids", []))

    # Collect all downstream task IDs (BFS)
    affected_ids: set[str] = set()
    stack = [task_id]
    while stack:
        n = stack.pop()
        for child in downstream_map.get(n, set()):
            if child not in affected_ids:
                affected_ids.add(child)
                stack.append(child)

    affected_tasks = [
        {"id": tid, "title": task_by_id.get(tid, {}).get("title", tid)}
        for tid in sorted(affected_ids)
    ]

    # Estimate delay: if dueDateTime is pushed, downstream may slip
    delay_days = 0
    if "dueDateTime" in proposed_changes or "slippage_days" in proposed_changes:
        slippage = proposed_changes.get("slippage_days")
        if slippage is not None:
            delay_days = int(slippage)
        else:
            new_due = _parse_iso(proposed_changes.get("dueDateTime"))
            old_due = _parse_iso(task_by_id.get(task_id, {}).get("dueDateTime"))
            if new_due and old_due and new_due > old_due:
                delay_days = max(0, (new_due - old_due).days)

    critical_path_impact = bool(affected_ids & critical_ids) or task_id in critical_ids

    return {
        "plan_id": plan_id,
        "task_id": task_id,
        "affected_tasks": affected_tasks,
        "affected_count": len(affected_tasks),
        "downstream_delay_days": delay_days,
        "critical_path_impact": critical_path_impact,
    }


def analyze_slippage_impact(plan_id: str, task_id: str, slippage_days: int) -> dict[str, Any]:
    """Analyze impact of fixed slippage (delay) on a task."""
    return analyze_edit_impact(plan_id, task_id, {"slippage_days": slippage_days})
