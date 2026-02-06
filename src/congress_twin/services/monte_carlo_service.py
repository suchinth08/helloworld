"""
Monte Carlo simulation for Congress schedule: on-time probability and agent suggestions.

Runs N simulations of task durations (using variance), computes critical path end date
per run, then P(on-time) and risk drivers. Agent suggests enhancements and modifications.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from congress_twin.services.planner_simulated_data import DEFAULT_PLAN_ID, get_simulated_dependencies
from congress_twin.services.planner_service import get_tasks_for_plan


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def run_monte_carlo(
    plan_id: str = DEFAULT_PLAN_ID,
    n_simulations: int = 500,
    event_date_iso: str | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """
    Run Monte Carlo simulation: sample task durations from (base + variance), compute
    critical path end for each run. Returns P(on-time), percentile end dates, risk tasks,
    and agent suggestions (enhancements/modifications).
    """
    if seed is not None:
        random.seed(seed)
    tasks = get_tasks_for_plan(plan_id)
    deps = get_simulated_dependencies(plan_id)
    task_by_id = {t["id"]: t for t in tasks}

    # Build upstream map and topological order for critical path
    upstream: dict[str, set[str]] = {t["id"]: set() for t in tasks}
    for task_id, depends_on in deps:
        upstream[task_id].add(depends_on)

    # Topological order (simplified: use critical path order from longest chain)
    from congress_twin.services.planner_service import get_critical_path
    path_res = get_critical_path(plan_id)
    critical_ids = path_res["task_ids"]
    # All task IDs in dependency order for simulation
    all_ids = list(task_by_id.keys())

    # Event date: plan end or provided
    event_date = _parse_iso(event_date_iso) if event_date_iso else None
    if not event_date and critical_ids:
        last_id = critical_ids[-1]
        t = task_by_id.get(last_id)
        if t:
            due = _parse_iso(t.get("dueDateTime"))
            if due:
                event_date = due + timedelta(days=3)
    if not event_date:
        event_date = datetime.now(timezone.utc) + timedelta(days=30)

    # Base duration (days) and variance per task
    def get_duration_days(t: dict[str, Any]) -> tuple[float, float]:
        start = _parse_iso(t.get("startDateTime"))
        due = _parse_iso(t.get("dueDateTime"))
        if start and due:
            base = max(0.5, (due - start).total_seconds() / 86400)
        else:
            base = 5.0
        var = t.get("variance_days", 2)
        return base, float(var)

    # Run simulations: for each task sample duration = base + N(0, variance^2) truncated
    end_dates: list[datetime] = []
    task_finish_samples: dict[str, list[datetime]] = {tid: [] for tid in all_ids}

    for _ in range(n_simulations):
        finish: dict[str, datetime] = {}
        # Process in dependency order (simplified: multiple passes until no change)
        for _ in range(len(all_ids) + 1):
            for tid in all_ids:
                if tid in finish:
                    continue
                deps_tid = upstream.get(tid, set())
                if any(d not in finish for d in deps_tid):
                    continue
                t = task_by_id.get(tid)
                if not t:
                    continue
                base, var = get_duration_days(t)
                # Sample duration (days)
                delta_days = base + random.gauss(0, var if var > 0 else 1)
                delta_days = max(0.5, delta_days)
                start_dt = None
                for dep in deps_tid:
                    fd = finish.get(dep)
                    if fd and (start_dt is None or fd > start_dt):
                        start_dt = fd
                if start_dt is None:
                    start_dt = _parse_iso(t.get("startDateTime")) or datetime.now(timezone.utc)
                end_dt = start_dt + timedelta(days=delta_days)
                finish[tid] = end_dt
                task_finish_samples[tid].append(end_dt)

        # Plan end = max of all finish times
        if finish:
            plan_end = max(finish.values())
            end_dates.append(plan_end)

    on_time_count = sum(1 for d in end_dates if d <= event_date)
    p_on_time = (on_time_count / len(end_dates)) * 100.0 if end_dates else 0.0
    end_dates_sorted = sorted(end_dates)
    n = len(end_dates_sorted)
    p50 = end_dates_sorted[n // 2].isoformat() if n else None
    p90 = end_dates_sorted[int(n * 0.9)].isoformat() if n else None
    p10 = end_dates_sorted[int(n * 0.1)].isoformat() if n else None

    # Risk drivers: tasks whose variance most shifts the plan end (simplified: by variance and on critical path)
    risk_tasks: list[dict[str, Any]] = []
    for tid in critical_ids:
        t = task_by_id.get(tid)
        if not t:
            continue
        samples = task_finish_samples.get(tid, [])
        if not samples:
            continue
        samples_sorted = sorted(samples)
        nn = len(samples_sorted)
        p90_finish = samples_sorted[int(nn * 0.9)].isoformat() if nn else None
        risk_tasks.append({
            "task_id": tid,
            "title": t.get("title", ""),
            "variance_days": t.get("variance_days", 2),
            "p90_finish": p90_finish,
            "on_critical_path": True,
        })
    risk_tasks.sort(key=lambda x: -x.get("variance_days", 0))

    # Agent suggestions: enhancements and modifications
    suggestions = _agent_suggestions(
        plan_id=plan_id,
        p_on_time=p_on_time,
        risk_tasks=risk_tasks,
        event_date=event_date,
        task_by_id=task_by_id,
        critical_ids=critical_ids,
    )

    return {
        "plan_id": plan_id,
        "n_simulations": n_simulations,
        "event_date": event_date.isoformat(),
        "probability_on_time_percent": round(p_on_time, 1),
        "percentile_end_dates": {
            "p10": p10,
            "p50": p50,
            "p90": p90,
        },
        "risk_tasks": risk_tasks[:10],
        "agent_suggestions": suggestions,
    }


def _agent_suggestions(
    plan_id: str,
    p_on_time: float,
    risk_tasks: list[dict[str, Any]],
    event_date: datetime,
    task_by_id: dict[str, Any],
    critical_ids: list[str],
) -> list[dict[str, Any]]:
    """Agent: suggest enhancements and modifications from Monte Carlo results."""
    suggestions: list[dict[str, Any]] = []

    if p_on_time < 70 and risk_tasks:
        top = risk_tasks[0]
        suggestions.append({
            "id": "s1",
            "type": "enhancement",
            "priority": "high",
            "title": "Add buffer to highest-variance critical task",
            "detail": f"Task '{top.get('title', '')}' (id: {top.get('task_id')}) has high variance. Add 1–2 day buffer or parallel prep to protect event date.",
            "task_id": top.get("task_id"),
            "action_hint": "Consider shifting predecessor or adding backup owner.",
        })

    if p_on_time < 85:
        suggestions.append({
            "id": "s2",
            "type": "modification",
            "priority": "medium",
            "title": "Tighten due dates on downstream tasks",
            "detail": f"On-time probability is {p_on_time:.0f}%. Bring forward due dates for non-critical tasks to create slack on critical path.",
            "task_id": None,
            "action_hint": "Review Day-of logistics & runbook and Post-congress handover dates.",
        })

    if len(critical_ids) >= 4:
        suggestions.append({
            "id": "s3",
            "type": "enhancement",
            "priority": "medium",
            "title": "Parallelize where possible",
            "detail": "Critical path has multiple tasks. Registration platform and Catering (or similar) could run in parallel to reduce end-to-end duration.",
            "task_id": None,
            "action_hint": "Check dependency graph for tasks that can start earlier.",
        })

    suggestions.append({
        "id": "s4",
        "type": "modification",
        "priority": "low",
        "title": "Sync with MS Planner and re-run simulation",
        "detail": "After re-sync, run Monte Carlo again to see updated P(on-time) with latest % complete and due dates.",
        "task_id": None,
        "action_hint": "Use Sync button and then refresh this view.",
    })

    return suggestions
