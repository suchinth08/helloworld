"""
Planner service: attention metrics, dependencies, critical path.

Uses SQLite for persistence; simulated data fallback for DEFAULT_PLAN_ID if no DB data.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from congress_twin.config import get_settings
from congress_twin.db.planner_repo import (
    create_planner_task as repo_create_task,
    delete_checklist_item as repo_delete_checklist_item,
    delete_planner_task as repo_delete_task,
    get_plan_sync_state,
    get_planner_task_dependencies,
    list_planner_plans as repo_list_plans,
    get_planner_tasks as get_planner_tasks_from_db,
    set_plan_sync_state,
    upsert_checklist_item as repo_upsert_checklist_item,
    upsert_planner_tasks as db_upsert_planner_tasks,
    upsert_planner_task_details,
    upsert_planner_task_dependencies,
    update_planner_task as repo_update_task,
)
from congress_twin.services.graph_client import (
    fetch_plan_tasks_from_graph,
    fetch_task_details_from_graph,
    fetch_task_dependencies_from_graph,
    get_token,
    is_graph_configured,
)
from congress_twin.services.congress_seed_data import get_congress_seed_tasks
from congress_twin.services.planner_simulated_data import (
    DEFAULT_PLAN_ID,
    get_simulated_buckets,
    get_simulated_dependencies,
)


def get_dependencies_for_plan(plan_id: str) -> list[tuple[str, str]]:
    """
    Return (task_id, depends_on_task_id) list for a plan.
    From DB when dependencies exist; otherwise simulated.
    """
    rows = get_planner_task_dependencies(plan_id, None)
    if rows:
        return [(r.get("taskId") or r.get("task_id", ""), r.get("dependsOnTaskId") or r.get("depends_on_task_id", "")) for r in rows]
    return get_simulated_dependencies(plan_id)


def _seed_congress_dependencies(plan_id: str) -> None:
    """Upsert congress seed dependencies into DB for the default plan."""
    deps = get_simulated_dependencies(plan_id)
    # Group by task_id: task_id -> [depends_on_task_id, ...]
    by_task: dict[str, list[str]] = {}
    for task_id, depends_on_id in deps:
        by_task.setdefault(task_id, []).append(depends_on_id)
    for task_id, depends_on_ids in by_task.items():
        upsert_planner_task_dependencies(
            plan_id,
            task_id,
            [{"dependsOnTaskId": dep_id, "dependencyType": "FS"} for dep_id in depends_on_ids],
        )


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def get_attention_dashboard(plan_id: str = DEFAULT_PLAN_ID) -> dict[str, Any]:
    """
    Compute blockers, overdue, due next 7 days, recently changed.
    Blocked = not completed and at least one upstream dependency not completed.
    """
    tasks = get_tasks_for_plan(plan_id)
    deps = get_dependencies_for_plan(plan_id)
    task_by_id = {t["id"]: t for t in tasks}
    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(days=1)
    seven_days_later = now + timedelta(days=7)

    # Upstream: task_id -> list of task_ids it depends on (only for tasks in plan)
    upstream: dict[str, set[str]] = {t["id"]: set() for t in tasks}
    for t_id, depends_on in deps:
        if t_id in upstream:
            upstream[t_id].add(depends_on)

    path_res = get_critical_path(plan_id)
    critical_ids = set(path_res["task_ids"])

    blockers: list[dict[str, Any]] = []
    overdue: list[dict[str, Any]] = []
    due_next_7: list[dict[str, Any]] = []
    recently_changed: list[dict[str, Any]] = []
    critical_path_due_next: list[dict[str, Any]] = []

    for t in tasks:
        tid = t["id"]
        status = t.get("status", "notStarted")
        due_s = t.get("dueDateTime")
        due_dt = _parse_iso(due_s)
        last_mod_s = t.get("lastModifiedAt")
        last_mod_dt = _parse_iso(last_mod_s)

        # Blocked: not done and any upstream (in plan) not done
        if status != "completed" and upstream.get(tid):
            upstream_in_plan = [up_id for up_id in upstream[tid] if up_id in task_by_id]
            any_upstream_incomplete = any(
                task_by_id[up_id].get("status") != "completed"
                for up_id in upstream_in_plan
            )
            if upstream_in_plan and any_upstream_incomplete:
                blockers.append(t)

        # Overdue: due in the past and not completed
        if due_dt and due_dt < now and status != "completed":
            overdue.append(t)

        # Due next 7 days
        if due_dt and now <= due_dt <= seven_days_later and status != "completed":
            due_next_7.append(t)

        # Recently changed (last 24h)
        if last_mod_dt and last_mod_dt >= one_day_ago:
            recently_changed.append(t)

        # Critical path tasks due in next 7 days (not completed)
        if tid in critical_ids and status != "completed" and due_dt and now <= due_dt <= seven_days_later:
            critical_path_due_next.append(t)

    def _summarize(task_list: list[dict]) -> list[dict]:
        return [
            {
                "id": t["id"],
                "title": t["title"],
                "status": t.get("status"),
                "dueDateTime": t.get("dueDateTime"),
                "assigneeNames": t.get("assigneeNames", []),
            }
            for t in task_list
        ]

    return {
        "plan_id": plan_id,
        "blockers": {"count": len(blockers), "tasks": _summarize(blockers)},
        "overdue": {"count": len(overdue), "tasks": _summarize(overdue)},
        "due_next_7_days": {"count": len(due_next_7), "tasks": _summarize(due_next_7)},
        "critical_path_due_next": {"count": len(critical_path_due_next), "tasks": _summarize(critical_path_due_next)},
        "recently_changed": {"count": len(recently_changed), "tasks": _summarize(recently_changed)},
    }


def get_dependencies(task_id: str, plan_id: str = DEFAULT_PLAN_ID) -> dict[str, Any]:
    """Upstream = must finish before this; downstream = impacted if this slips."""
    tasks = get_tasks_for_plan(plan_id)
    deps = get_dependencies_for_plan(plan_id)
    task_by_id = {t["id"]: t for t in tasks}

    upstream_ids: set[str] = set()
    downstream_ids: set[str] = set()

    for t_id, depends_on in deps:
        if t_id == task_id and depends_on in task_by_id:
            upstream_ids.add(depends_on)
        if depends_on == task_id and t_id in task_by_id:
            downstream_ids.add(t_id)

    def _summarize(ids: set[str]) -> list[dict]:
        return [
            {
                "id": tid,
                "title": task_by_id[tid]["title"],
                "status": task_by_id[tid].get("status"),
                "dueDateTime": task_by_id[tid].get("dueDateTime"),
                "assigneeNames": task_by_id[tid].get("assigneeNames", []),
            }
            for tid in sorted(ids)
            if tid in task_by_id
        ]

    # Impact statement: "If Task X slips 3 days, these N tasks may move."
    downstream_count = len(downstream_ids)
    downstream_titles = [task_by_id[tid]["title"] for tid in sorted(downstream_ids) if tid in task_by_id]
    if downstream_count:
        impact = f"If this task slips 3 days, {downstream_count} downstream task(s) may move: {', '.join(downstream_titles[:5])}{'…' if len(downstream_titles) > 5 else ''}."
    else:
        impact = "No downstream dependencies."

    return {
        "task_id": task_id,
        "upstream": _summarize(upstream_ids),
        "downstream": _summarize(downstream_ids),
        "impact_statement": impact,
    }


def get_critical_path(plan_id: str = DEFAULT_PLAN_ID) -> dict[str, Any]:
    """Longest dependency chain (DAG longest path) as critical path."""
    deps = get_dependencies_for_plan(plan_id)
    tasks = get_tasks_for_plan(plan_id)
    task_by_id = {t["id"]: t for t in tasks}
    all_ids = {t["id"] for t in tasks}

    if not all_ids:
        return {"plan_id": plan_id, "critical_path": [], "task_ids": []}

    # Only consider dependencies where both ends are in the plan's task list
    deps_in_plan = [(t_id, depends_on) for t_id, depends_on in deps if t_id in all_ids and depends_on in all_ids]

    # dependents[depends_on] = set of task_ids that depend on it
    dependents: dict[str, set[str]] = {tid: set() for tid in all_ids}
    for t_id, depends_on in deps_in_plan:
        dependents[depends_on].add(t_id)

    # Topological order (Kahn): in_degree = number of deps that must complete before this task
    in_degree: dict[str, int] = {tid: 0 for tid in all_ids}
    for t_id, _ in deps_in_plan:
        in_degree[t_id] = in_degree.get(t_id, 0) + 1
    order: list[str] = []
    stack = [tid for tid in all_ids if in_degree[tid] == 0]
    while stack:
        n = stack.pop()
        order.append(n)
        for m in dependents.get(n, set()):
            in_degree[m] -= 1
            if in_degree[m] == 0:
                stack.append(m)
    if len(order) != len(all_ids):
        order = list(all_ids)  # fallback if cycle

    # Predecessors: task_id -> list of task_ids it depends on
    predecessors: dict[str, list[str]] = {tid: [] for tid in all_ids}
    for t_id, depends_on in deps_in_plan:
        predecessors[t_id].append(depends_on)

    # Longest path length ending at each node (DAG)
    dist: dict[str, int] = {}
    prev: dict[str, str] = {}
    for n in order:
        preds = predecessors[n]
        if not preds:
            dist[n] = 1
            prev[n] = ""
        else:
            best_p = max(preds, key=lambda p: dist.get(p, 0))
            dist[n] = dist.get(best_p, 0) + 1
            prev[n] = best_p

    # End node with max dist, backtrack for path
    end_node = max(all_ids, key=lambda x: dist.get(x, 0))
    path_ids: list[str] = []
    cur = end_node
    while cur:
        path_ids.append(cur)
        cur = prev.get(cur, "")

    path_ids.reverse()
    critical_tasks = [
        {
            "id": tid,
            "title": task_by_id[tid]["title"],
            "status": task_by_id[tid].get("status"),
            "dueDateTime": task_by_id[tid].get("dueDateTime"),
            "assigneeNames": task_by_id[tid].get("assigneeNames", []),
        }
        for tid in path_ids
    ]

    return {
        "plan_id": plan_id,
        "critical_path": critical_tasks,
        "task_ids": path_ids,
    }


def get_milestone_analysis(
    plan_id: str = DEFAULT_PLAN_ID,
    event_date: datetime | None = None,
) -> dict[str, Any]:
    """
    Milestone / Event Date lane: tasks that must complete before event date,
    and tasks at risk (not completed, due after event date).
    """
    tasks = get_tasks_for_plan(plan_id)
    path_res = get_critical_path(plan_id)
    critical_ids = set(path_res["task_ids"])
    task_by_id = {t["id"]: t for t in tasks}
    now = datetime.now(timezone.utc)
    if event_date is None:
        # Default: 21 days from now (e.g. go-live)
        event_date = now + timedelta(days=21)
    if event_date.tzinfo is None:
        event_date = event_date.replace(tzinfo=timezone.utc)

    tasks_before_event: list[dict[str, Any]] = []
    at_risk_tasks: list[dict[str, Any]] = []

    for t in tasks:
        due_s = t.get("dueDateTime")
        due_dt = _parse_iso(due_s)
        status = t.get("status", "notStarted")
        if due_dt and due_dt <= event_date:
            tasks_before_event.append(t)
        if status != "completed" and due_dt and due_dt > event_date:
            days_over = (due_dt - event_date).days
            at_risk_tasks.append({
                **t,
                "days_after_event": days_over,
            })
        elif status != "completed" and due_dt is None:
            at_risk_tasks.append({**t, "days_after_event": None})

    def _summarize(task_list: list[dict]) -> list[dict]:
        return [
            {
                "id": t["id"],
                "title": t["title"],
                "status": t.get("status"),
                "dueDateTime": t.get("dueDateTime"),
                "assigneeNames": t.get("assigneeNames", []),
                "on_critical_path": t["id"] in critical_ids,
            }
            for t in task_list
        ]

    return {
        "plan_id": plan_id,
        "event_date": event_date.isoformat(),
        "tasks_before_event": _summarize(tasks_before_event),
        "at_risk_tasks": [
            {
                "id": t["id"],
                "title": t["title"],
                "status": t.get("status"),
                "dueDateTime": t.get("dueDateTime"),
                "assigneeNames": t.get("assigneeNames", []),
                "days_after_event": t.get("days_after_event"),
            }
            for t in at_risk_tasks
        ],
        "at_risk_count": len(at_risk_tasks),
    }


def get_changes_since_sync(plan_id: str = DEFAULT_PLAN_ID) -> dict[str, Any]:
    """
    Tasks modified in Planner since previous sync (last_modified_at > previous_sync_at).
    Used for "Changes since publish" / "What changed since last sync".
    """
    tasks = get_tasks_for_plan(plan_id)
    _, previous_sync_at_raw = get_plan_sync_state(plan_id)
    previous_sync_at: datetime
    if not previous_sync_at_raw:
        previous_sync_at = datetime.now(timezone.utc) - timedelta(hours=24)
    else:
        # SQLite returns TEXT as str; parse to datetime for comparison
        previous_sync_at = _parse_iso(str(previous_sync_at_raw)) or datetime.now(timezone.utc) - timedelta(hours=24)
    changed = [
        {
            "id": t["id"],
            "title": t["title"],
            "status": t.get("status"),
            "dueDateTime": t.get("dueDateTime"),
            "assigneeNames": t.get("assigneeNames", []),
            "lastModifiedAt": t.get("lastModifiedAt"),
        }
        for t in tasks
        if _parse_iso(t.get("lastModifiedAt")) and _parse_iso(t.get("lastModifiedAt")) > previous_sync_at
    ]
    return {"plan_id": plan_id, "changes": changed, "count": len(changed)}


def get_execution_tasks(plan_id: str = DEFAULT_PLAN_ID) -> list[dict[str, Any]]:
    """
    Tasks enriched for execution/Dependency Lens: risk badges (blocked, blocking, at_risk, overdue)
    and upstream_count, downstream_count per task.
    """
    tasks = get_tasks_for_plan(plan_id)
    deps = get_dependencies_for_plan(plan_id)
    path_res = get_milestone_analysis(plan_id, event_date=None)
    path_res_cp = get_critical_path(plan_id)
    task_by_id = {t["id"]: t for t in tasks}
    now = datetime.now(timezone.utc)
    critical_ids = set(path_res_cp["task_ids"])
    at_risk_ids = {t["id"] for t in path_res.get("at_risk_tasks", [])}

    upstream: dict[str, set[str]] = {t["id"]: set() for t in tasks}
    downstream: dict[str, set[str]] = {t["id"]: set() for t in tasks}
    for t_id, depends_on in deps:
        if t_id in upstream and depends_on in downstream:
            upstream[t_id].add(depends_on)
            downstream[depends_on].add(t_id)

    blocker_ids: set[str] = set()
    for t in tasks:
        tid = t["id"]
        status = t.get("status", "notStarted")
        if status != "completed" and upstream.get(tid):
            upstream_in_plan = [up_id for up_id in upstream[tid] if up_id in task_by_id]
            if any(task_by_id[up_id].get("status") != "completed" for up_id in upstream_in_plan):
                blocker_ids.add(tid)

    blocking_ids: set[str] = set()  # not done and upstream of any critical path task
    for tid in critical_ids:
        for up_id in upstream.get(tid, set()):
            if up_id in task_by_id and task_by_id[up_id].get("status") != "completed":
                blocking_ids.add(up_id)

    result: list[dict[str, Any]] = []
    for t in tasks:
        tid = t["id"]
        due_dt = _parse_iso(t.get("dueDateTime"))
        status = t.get("status", "notStarted")
        overdue = bool(due_dt and due_dt < now and status != "completed")
        at_risk = tid in at_risk_ids
        blocked = tid in blocker_ids
        blocking = tid in blocking_ids
        risk_badges: list[str] = []
        if blocked:
            risk_badges.append("blocked")
        if blocking:
            risk_badges.append("blocking")
        if at_risk:
            risk_badges.append("at_risk")
        if overdue:
            risk_badges.append("overdue")
        result.append({
            **t,
            "risk_badges": risk_badges,
            "upstream_count": len(upstream.get(tid, set())),
            "downstream_count": len(downstream.get(tid, set())),
            "on_critical_path": tid in critical_ids,
        })
    return result


def list_plans() -> list[dict[str, Any]]:
    """
    List plans: from DB plus seed/simulated (uc31-plan, congress-2022, congress-2023, congress-2024).
    """
    from_db = repo_list_plans()
    known_ids = {p["plan_id"] for p in from_db}
    seed_plans = [
        {"plan_id": DEFAULT_PLAN_ID, "name": "UC31 Congress Plan", "congress_date": None, "source_plan_id": None, "created_at": None},
        {"plan_id": "congress-2022", "name": "Congress 2022", "congress_date": "2022-03-15", "source_plan_id": None, "created_at": None},
        {"plan_id": "congress-2023", "name": "Congress 2023", "congress_date": "2023-03-20", "source_plan_id": None, "created_at": None},
        {"plan_id": "congress-2024", "name": "Congress 2024", "congress_date": "2024-03-18", "source_plan_id": None, "created_at": None},
    ]
    for p in seed_plans:
        if p["plan_id"] not in known_ids:
            from_db.append(p)
            known_ids.add(p["plan_id"])
    return from_db


def get_buckets_for_plan(plan_id: str) -> list[dict[str, Any]]:
    """Return buckets (workstreams) for a plan."""
    return get_simulated_buckets(plan_id)


def create_planner_task(plan_id: str, task: dict[str, Any]) -> dict[str, Any]:
    """
    Create a new task. Validates bucketId, ensures plan has DB data (seeds if needed).
    Returns created task with details.
    """
    buckets = get_buckets_for_plan(plan_id)
    bucket_ids = {b["id"] for b in buckets}
    bucket_by_id = {b["id"]: b["name"] for b in buckets}
    bucket_id = task.get("bucketId")
    if not bucket_id:
        raise ValueError("bucketId is required")
    if bucket_id not in bucket_ids:
        raise ValueError(f"Unknown bucketId: {bucket_id}")
    task = dict(task)
    task["bucketName"] = task.get("bucketName") or bucket_by_id.get(bucket_id, "")
    return repo_create_task(plan_id, task)


def update_planner_task(plan_id: str, task_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """
    Partially update a task. Validates bucketId if provided.
    Returns updated task or None if not found.
    """
    if "bucketId" in updates:
        buckets = get_buckets_for_plan(plan_id)
        bucket_ids = {b["id"] for b in buckets}
        bucket_by_id = {b["id"]: b["name"] for b in buckets}
        if updates["bucketId"] not in bucket_ids:
            raise ValueError(f"Unknown bucketId: {updates['bucketId']}")
        updates["bucketName"] = bucket_by_id.get(updates["bucketId"], "")
    return repo_update_task(plan_id, task_id, updates)


def delete_planner_task(plan_id: str, task_id: str) -> bool:
    """Delete a task. Returns True if deleted."""
    return repo_delete_task(plan_id, task_id)


def add_subtask(plan_id: str, task_id: str, item: dict[str, Any]) -> dict[str, Any]:
    """Add or update a checklist item (subtask). Returns the created/updated item."""
    return repo_upsert_checklist_item(plan_id, task_id, item)


def update_subtask(plan_id: str, task_id: str, subtask_id: str, item: dict[str, Any]) -> dict[str, Any]:
    """Update a checklist item. Returns the updated item."""
    item = dict(item)
    item["id"] = subtask_id
    return repo_upsert_checklist_item(plan_id, task_id, item)


def delete_subtask(plan_id: str, task_id: str, subtask_id: str) -> bool:
    """Remove a checklist item. Returns True if removed."""
    return repo_delete_checklist_item(plan_id, task_id, subtask_id)


def get_tasks_for_plan(plan_id: str) -> list[dict[str, Any]]:
    """
    Return tasks for a plan: from DB if we have synced data, else simulated for DEFAULT_PLAN_ID only.
    When using Postgres and default plan has no tasks, auto-seed congress simulated data into DB
    so all reads/writes use Postgres with simulated data.
    """
    from_db = get_planner_tasks_from_db(plan_id)
    if from_db:
        return from_db
    if plan_id == DEFAULT_PLAN_ID:
        if get_settings().is_postgres:
            # Auto-seed simulated data into Postgres so we use DB + simulated content
            seed_congress_plan(plan_id)
            _seed_congress_dependencies(plan_id)
            return get_planner_tasks_from_db(plan_id) or get_congress_seed_tasks(
                plan_id, use_relative_dates_for_attention=True
            )
        return get_congress_seed_tasks(plan_id, use_relative_dates_for_attention=True)
    return []


def sync_planner_tasks(plan_id: str = DEFAULT_PLAN_ID) -> dict[str, Any]:
    """
    Sync tasks from MS Planner (or simulated when Graph not configured).
    When Graph is configured and token is obtained, fetches from Graph API and persists to DB (Postgres or SQLite).
    """
    if is_graph_configured():
        token = get_token()
        if token:
            try:
                # Fetch tasks with details expanded
                tasks = fetch_plan_tasks_from_graph(plan_id, token, include_details=True)
                try:
                    db_upsert_planner_tasks(plan_id, tasks)
                    
                    # Fetch and store task details (checklist, references)
                    for task in tasks:
                        task_id = task.get("id")
                        if task_id:
                            # Details are already in task dict from expanded query, but fetch separately to ensure we have checklist/references
                            details = fetch_task_details_from_graph(task_id, token)
                            if details:
                                upsert_planner_task_details(plan_id, task_id, {
                                    "checklist": details.get("checklist", {}),
                                    "references": details.get("references", {}),
                                    "lastModifiedAt": details.get("lastModifiedDateTime"),
                                })
                    
                    # Fetch and store dependencies
                    dependencies_map = fetch_task_dependencies_from_graph(plan_id, token)
                    for task_id, deps in dependencies_map.items():
                        upsert_planner_task_dependencies(plan_id, task_id, deps)
                        
                except Exception as db_e:
                    return {
                        "plan_id": plan_id,
                        "status": "error",
                        "source": "graph",
                        "tasks_synced": 0,
                        "message": f"Graph sync succeeded but DB write failed: {db_e!s}",
                    }
                set_plan_sync_state(plan_id, datetime.now(timezone.utc), get_plan_sync_state(plan_id)[0])
                return {
                    "plan_id": plan_id,
                    "status": "ok",
                    "source": "graph",
                    "tasks_synced": len(tasks),
                    "message": "Synced from Microsoft Graph and saved to database.",
                }
            except Exception as e:
                return {
                    "plan_id": plan_id,
                    "status": "error",
                    "source": "graph",
                    "tasks_synced": 0,
                    "message": f"Graph sync failed: {e!s}",
                }
        tasks = get_congress_seed_tasks(plan_id, use_relative_dates_for_attention=True)
        try:
            db_upsert_planner_tasks(plan_id, tasks)
        except Exception:
            pass
        set_plan_sync_state(plan_id, datetime.now(timezone.utc), get_plan_sync_state(plan_id)[0])
        return {
            "plan_id": plan_id,
            "status": "ok",
            "source": "congress_seed",
            "tasks_synced": len(tasks),
            "message": "Graph token failed. Seeded congress data to DB.",
        }
    tasks = get_congress_seed_tasks(plan_id, use_relative_dates_for_attention=True)
    try:
        db_upsert_planner_tasks(plan_id, tasks)
    except Exception:
        pass
    set_plan_sync_state(plan_id, datetime.now(timezone.utc), get_plan_sync_state(plan_id)[0])
    return {
        "plan_id": plan_id,
        "status": "ok",
        "source": "congress_seed",
        "tasks_synced": len(tasks),
        "message": "Sync completed (congress seed). Set GRAPH_* for live Planner sync.",
    }


def seed_congress_plan(plan_id: str = DEFAULT_PLAN_ID) -> dict[str, Any]:
    """
    Seed DB with Novartis Congress event scheduling data (same as seed script).
    Ensures tables, upserts congress tasks, sets sync state. For dev / bootstrap.
    """
    from congress_twin.db.planner_repo import (
        ensure_plan_sync_state_table,
        ensure_planner_tasks_table,
    )
    ensure_planner_tasks_table()
    ensure_plan_sync_state_table()
    tasks = get_congress_seed_tasks(plan_id, use_relative_dates_for_attention=True)
    db_upsert_planner_tasks(plan_id, tasks)
    now = datetime.now(timezone.utc)
    set_plan_sync_state(plan_id, now, previous_sync_at=now)
    return {
        "plan_id": plan_id,
        "status": "ok",
        "tasks_seeded": len(tasks),
        "message": "Congress seed data loaded. UI/APIs will use DB for this plan.",
    }


# --- Advanced view (Commander): probability gantt, mitigation feed, veeva ---

def get_probability_gantt(plan_id: str = DEFAULT_PLAN_ID) -> dict[str, Any]:
    """
    Tasks with start/end and variance for Probability Gantt.
    Uses task startDateTime/dueDateTime and variance_days when present (planning data).
    """
    path_res = get_critical_path(plan_id)
    tasks = get_tasks_for_plan(plan_id)
    task_by_id = {t["id"]: t for t in tasks}
    critical_ids = set(path_res["task_ids"])
    now = datetime.now(timezone.utc)

    bars: list[dict[str, Any]] = []
    for i, tid in enumerate(path_res["task_ids"]):
        t = task_by_id.get(tid)
        if not t:
            continue
        start_s = t.get("startDateTime")
        due_s = t.get("dueDateTime")
        start_dt = _parse_iso(start_s)
        due_dt = _parse_iso(due_s)
        if not start_dt and due_dt:
            start_dt = due_dt - timedelta(days=5)
        if not due_dt:
            due_dt = now
        if not start_dt:
            start_dt = due_dt - timedelta(days=5)
        variance_days = t.get("variance_days") or (2 if tid in critical_ids else 1)
        # Confidence from percent complete or default
        pct = t.get("percentComplete", 0)
        confidence = pct if 0 <= pct <= 100 else max(70, 95 - i * 3)
        bars.append({
            "id": tid,
            "title": t["title"],
            "status": t.get("status"),
            "start_date": start_dt.isoformat(),
            "end_date": due_dt.isoformat(),
            "confidence_percent": confidence,
            "variance_days": variance_days,
            "on_critical_path": True,
        })
    for t in tasks:
        if t["id"] in critical_ids:
            continue
        start_s = t.get("startDateTime")
        due_s = t.get("dueDateTime")
        due_dt = _parse_iso(due_s)
        start_dt = _parse_iso(start_s) if start_s else (due_dt - timedelta(days=4) if due_dt else None)
        if due_dt and len(bars) < 12:
            bars.append({
                "id": t["id"],
                "title": t["title"],
                "status": t.get("status"),
                "start_date": (start_dt or due_dt).isoformat(),
                "end_date": due_dt.isoformat(),
                "confidence_percent": t.get("percentComplete", 78),
                "variance_days": t.get("variance_days", 1),
                "on_critical_path": False,
            })
    bars.sort(key=lambda x: (x["start_date"] or ""))
    return {"plan_id": plan_id, "bars": bars}


def get_mitigation_feed(plan_id: str = DEFAULT_PLAN_ID) -> dict[str, Any]:
    """
    Agent mitigation feed: interventions (e.g. task shifted, reason).
    Planning-related simulated list for Commander View.
    """
    interventions = [
        {"id": "int-1", "task_id": "task-003", "task_title": "Backend: Planner sync service", "action": "shifted", "reason": "OptimizationAgent re-ran after blocker cleared; moved 1 day earlier to protect critical path.", "at": "2026-02-06T08:51:00+00:00"},
        {"id": "int-2", "task_id": "task-002", "task_title": "API and data model design", "action": "updated", "reason": "MonitorAgent: 82% confidence of on-time; no change required.", "at": "2026-02-06T08:06:00+00:00"},
        {"id": "int-3", "task_id": "task-005", "task_title": "Integration and API wiring", "action": "flagged", "reason": "VeevaAgent: KOL alignment dip if task-006 slips; consider adding resource.", "at": "2026-02-06T07:06:00+00:00"},
    ]
    return {"plan_id": plan_id, "interventions": interventions}


def get_veeva_insights(plan_id: str = DEFAULT_PLAN_ID) -> dict[str, Any]:
    """
    Veeva-style insights: KOL value vs staff fatigue (simulated for Commander View).
    """
    return {
        "plan_id": plan_id,
        "kol_alignment_score": 87,
        "kol_alignment_trend": "up",
        "staff_fatigue_index": 34,
        "staff_fatigue_trend": "down",
        "summary": "KOL value aligned; staff fatigue within target. One slot at risk if Integration task slips.",
        "insights": [
            {"id": "v1", "title": "KOL coverage", "value": "87%", "detail": "High-value KOLs covered in current schedule."},
            {"id": "v2", "title": "Staff fatigue", "value": "34", "detail": "Below 40 threshold; capacity available for buffer."},
        ],
    }
