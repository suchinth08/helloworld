"""
Template service: Create plans from previous year templates.

Loads tasks from historical plans (congress-2022, congress-2023, congress-2024),
clones with new IDs and shifted dates, runs Monte Carlo + Markov for suggestions.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from congress_twin.db.planner_repo import (
    get_planner_task_details,
    get_planner_task_dependencies,
    get_planner_tasks,
    upsert_planner_plan,
    upsert_planner_task_details,
    upsert_planner_task_dependencies,
    upsert_planner_tasks,
)
from congress_twin.services.historical_data_generator import generate_historical_plan
from congress_twin.services.planner_simulated_data import get_simulated_buckets

HISTORICAL_PLAN_IDS = ["congress-2022", "congress-2023", "congress-2024"]


def list_historical_plans() -> list[dict[str, Any]]:
    """Return available template plans (congress-2022, congress-2023, congress-2024)."""
    return [
        {"plan_id": "congress-2022", "name": "Congress 2022", "congress_date": "2022-03-15"},
        {"plan_id": "congress-2023", "name": "Congress 2023", "congress_date": "2023-03-20"},
        {"plan_id": "congress-2024", "name": "Congress 2024", "congress_date": "2024-03-18"},
    ]


def _parse_congress_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _shift_task_dates(task: dict[str, Any], days_offset: int) -> dict[str, Any]:
    """Shift start/due/completed dates by days_offset."""
    t = dict(task)

    def shift(iso: str | None) -> str | None:
        if not iso:
            return None
        try:
            s = iso.replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            shifted = dt + timedelta(days=days_offset)
            return shifted.isoformat().replace("+00:00", "Z")
        except (ValueError, TypeError):
            return iso

    for key in ("startDateTime", "dueDateTime", "completedDateTime", "createdDateTime", "lastModifiedAt"):
        if t.get(key):
            t[key] = shift(t[key])
    return t


def _generate_new_task_id(prefix: str, index: int) -> str:
    """Generate a new task ID for the target plan."""
    return f"{prefix}-task-{index:03d}"


def create_plan_from_template(
    target_plan_id: str,
    source_plan_id: str,
    congress_date: str | datetime | None = None,
    run_simulation: bool = True,
) -> dict[str, Any]:
    """
    Create a new plan from a template (historical plan).
    Loads tasks from source (DB or generates if missing), clones with new IDs,
    shifts dates to congress_date, optionally runs Monte Carlo for suggestions.

    Returns: { tasks_created, suggested_assignments, p50_date, p95_date, ... }
    """
    # Resolve congress date
    if congress_date is None:
        congress_dt = datetime.now(timezone.utc) + timedelta(days=90)
    elif isinstance(congress_date, str):
        congress_dt = _parse_congress_date(congress_date) or datetime.now(timezone.utc) + timedelta(days=90)
    else:
        congress_dt = congress_date
        if congress_dt.tzinfo is None:
            congress_dt = congress_dt.replace(tzinfo=timezone.utc)

    # Load source tasks
    source_tasks = get_planner_tasks(source_plan_id)
    if not source_tasks:
        # Generate historical plan if not in DB
        if source_plan_id in HISTORICAL_PLAN_IDS:
            year = int(source_plan_id.split("-")[1])
            source_congress = datetime(year, 4, 15, tzinfo=timezone.utc)
            generate_historical_plan(source_plan_id, source_congress, year)
            source_tasks = get_planner_tasks(source_plan_id)

    if not source_tasks:
        return {
            "target_plan_id": target_plan_id,
            "source_plan_id": source_plan_id,
            "tasks_created": 0,
            "error": f"No tasks found in source plan {source_plan_id}",
        }

    # Map old task ID -> new task ID
    id_map: dict[str, str] = {}
    target_tasks: list[dict[str, Any]] = []

    # Compute date shift (from source plan's avg due to target congress)
    sample_due = None
    for t in source_tasks:
        if t.get("dueDateTime"):
            sample_due = t["dueDateTime"]
            break
    if sample_due:
        try:
            source_due = datetime.fromisoformat(sample_due.replace("Z", "+00:00"))
            days_offset = (congress_dt - source_due).days
        except (ValueError, TypeError):
            days_offset = 90
    else:
        days_offset = 90

    # Clone tasks
    for i, t in enumerate(source_tasks):
        new_id = _generate_new_task_id(target_plan_id, i + 1)
        id_map[t["id"]] = new_id
        cloned = _shift_task_dates(t, days_offset)
        cloned["id"] = new_id
        # Rewrite bucketId to target plan prefix
        old_bucket = cloned.get("bucketId", "")
        if source_plan_id and old_bucket.startswith(source_plan_id):
            cloned["bucketId"] = target_plan_id + old_bucket[len(source_plan_id):]
            cloned["bucketName"] = cloned.get("bucketName", "")
        target_tasks.append(cloned)

    # Upsert plan
    upsert_planner_plan(target_plan_id, name=target_plan_id, congress_date=congress_dt)
    tasks_created = upsert_planner_tasks(target_plan_id, target_tasks)

    # Copy checklist and details
    for old_id, new_id in id_map.items():
        details = get_planner_task_details(source_plan_id, old_id)
        if details:
            upsert_planner_task_details(target_plan_id, new_id, details)

    # Copy dependencies (remap task IDs)
    for old_id, new_id in id_map.items():
        deps = get_planner_task_dependencies(source_plan_id, old_id)
        if deps:
            remapped = []
            for d in deps:
                dep_task = d.get("dependsOnTaskId") or d.get("depends_on_task_id")
                if dep_task and dep_task in id_map:
                    remapped.append({"dependsOnTaskId": id_map[dep_task], "dependencyType": d.get("dependencyType", "FS")})
            if remapped:
                upsert_planner_task_dependencies(target_plan_id, new_id, remapped)

    result: dict[str, Any] = {
        "target_plan_id": target_plan_id,
        "source_plan_id": source_plan_id,
        "tasks_created": tasks_created,
        "congress_date": congress_dt.isoformat(),
    }

    if run_simulation:
        try:
            from congress_twin.services.monte_carlo_service import run_monte_carlo
            sim = run_monte_carlo(target_plan_id, n_simulations=100, event_date_iso=congress_dt.isoformat())
            result["p50_completion"] = sim.get("percentile_end_dates", {}).get("p50")
            result["p95_completion"] = sim.get("percentile_end_dates", {}).get("p90")
            result["probability_on_time"] = sim.get("probability_on_time_percent", 0)
        except Exception:
            pass

    return result
