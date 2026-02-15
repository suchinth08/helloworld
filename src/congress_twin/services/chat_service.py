"""
Chat service: Hybrid semantic layer (Phase 1).

Intent + entity extraction via LLM (when configured) or regex fallback.
Dispatches to planner_service / impact_analyzer / monte_carlo for each intent.
"""

import logging
from datetime import datetime
from typing import Any

from congress_twin.db.planner_repo import get_planner_task_dependencies
from congress_twin.services.chat_intent import extract_intent
from congress_twin.services.chat_trace_store import save_trace
from congress_twin.services.planner_service import (
    get_attention_dashboard,
    get_critical_path,
    get_dependencies,
    get_milestone_analysis,
    get_tasks_for_plan,
)

logger = logging.getLogger(__name__)


def _format_date_short(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%b %d")
    except (ValueError, TypeError):
        return iso or ""


def _respond(
    plan_id: str,
    message: str,
    intent: str,
    entities: dict,
    resp_type: str,
    data: Any,
    text: str,
) -> dict[str, Any]:
    try:
        save_trace(plan_id, message, intent, entities, text[:500])
    except Exception:
        pass
    return {"type": resp_type, "data": data, "text": text}


def handle_chat_message(plan_id: str, message: str) -> dict[str, Any]:
    """
    Process chat message: extract intent + entities, dispatch to data fabric, return formatted response.
    Returns: { type, data, text }
    """
    parsed = extract_intent(message, plan_id)
    intent = parsed["intent"]
    entities = parsed["entities"]
    plan_id = entities.get("plan_id") or plan_id

    # --- attention ---
    if intent == "attention":
        dashboard = get_attention_dashboard(plan_id)
        blockers = dashboard.get("blockers", {}).get("tasks", [])[:5]
        overdue = dashboard.get("overdue", {}).get("tasks", [])[:5]
        due_next = dashboard.get("due_next_7_days", {}).get("tasks", [])[:5]
        text_parts = []
        if overdue:
            text_parts.append(f"**Overdue ({len(overdue)}):** {', '.join(t['title'] for t in overdue)}")
        if blockers:
            text_parts.append(f"**Blocked ({len(blockers)}):** {', '.join(t['title'] for t in blockers)}")
        if due_next:
            text_parts.append(f"**Due next 7 days ({len(due_next)}):** {', '.join(t['title'] for t in due_next)}")
        return _respond(
            plan_id, message, intent, entities,
            "attention", dashboard,
            "\n".join(text_parts) or "Nothing needs immediate attention.",
        )

    # --- critical_path ---
    if intent == "critical_path":
        cp = get_critical_path(plan_id)
        tasks = cp.get("critical_path", [])
        text = "Critical path: " + " → ".join(t.get("title", t.get("id", "")) for t in tasks[:8])
        return _respond(plan_id, message, intent, entities, "critical_path", cp, text or "No critical path.")

    # --- workload ---
    if intent == "workload":
        tasks = get_tasks_for_plan(plan_id)
        by_assignee: dict[str, list] = {}
        for t in tasks:
            for name in t.get("assigneeNames") or t.get("assignees") or []:
                n = name if isinstance(name, str) else str(name)
                by_assignee.setdefault(n, []).append(t)
        sorted_assignees = sorted(by_assignee.items(), key=lambda x: -len(x[1]))
        text = "Workload: " + "; ".join(f"{n}: {len(t)} tasks" for n, t in sorted_assignees[:5])
        return _respond(plan_id, message, intent, entities, "workload", {"by_assignee": {k: len(v) for k, v in sorted_assignees}}, text)

    # --- impact ---
    if intent == "impact":
        task_id = entities.get("task_id")
        slippage_days = entities.get("slippage_days", 3)
        if not task_id:
            return _respond(
                plan_id, message, intent, entities,
                "impact", {},
                "Which task? Say e.g. 'Impact of delaying task-005 by 3 days'.",
            )
        try:
            from congress_twin.services.impact_analyzer import analyze_slippage_impact
            impact = analyze_slippage_impact(plan_id, task_id, slippage_days)
            affected = impact.get("affected_tasks", [])
            text = f"Delaying {task_id} by {slippage_days} days may affect {len(affected)} downstream task(s)."
            if affected:
                text += " " + ", ".join(t.get("title", t.get("id")) for t in affected[:5])
            return _respond(plan_id, message, intent, entities, "impact", impact, text)
        except Exception:
            return _respond(plan_id, message, intent, entities, "impact", {}, f"Could not compute impact for {task_id}.")

    # --- dependencies ---
    if intent == "dependencies":
        task_id = entities.get("task_id")
        if not task_id:
            return _respond(
                plan_id, message, intent, entities,
                "dependencies", {},
                "Which task? Say e.g. 'Dependencies for task-005' or 'What depends on task-003?'.",
            )
        try:
            deps = get_dependencies(task_id, plan_id)
            up = deps.get("upstream", [])
            down = deps.get("downstream", [])
            stmt = deps.get("impact_statement", "")
            text = stmt
            if up:
                text += "\nUpstream: " + ", ".join(t.get("title", t.get("id")) for t in up[:5])
            if down:
                text += "\nDownstream: " + ", ".join(t.get("title", t.get("id")) for t in down[:5])
            return _respond(plan_id, message, intent, entities, "dependencies", deps, text.strip() or "No dependencies.")
        except Exception:
            return _respond(plan_id, message, intent, entities, "dependencies", {}, f"Could not get dependencies for {task_id}.")

    # --- milestone ---
    if intent == "milestone":
        event_date = None
        if entities.get("event_date"):
            try:
                event_date = datetime.fromisoformat(entities["event_date"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass
        try:
            res = get_milestone_analysis(plan_id, event_date)
            before = res.get("tasks_before_event", [])[:5]
            at_risk = res.get("at_risk_tasks", [])[:5]
            text_parts = []
            if before:
                text_parts.append(f"Before event: {', '.join(t.get('title', t.get('id')) for t in before)}")
            if at_risk:
                text_parts.append(f"At risk: {', '.join(t.get('title', t.get('id')) for t in at_risk)}")
            return _respond(
                plan_id, message, intent, entities,
                "milestone", res,
                "\n".join(text_parts) or "No milestone data for this event date.",
            )
        except Exception:
            return _respond(plan_id, message, intent, entities, "milestone", {}, "Could not run milestone analysis.")

    # --- monte_carlo ---
    if intent == "monte_carlo":
        try:
            from congress_twin.services.monte_carlo_service import run_monte_carlo
            res = run_monte_carlo(plan_id, n_simulations=500, event_date_iso=entities.get("event_date"))
            pct = res.get("probability_on_time_percent")
            text = f"Probability of finishing on time: {pct:.0f}%." if pct is not None else "Monte Carlo completed."
            return _respond(plan_id, message, intent, entities, "monte_carlo", res, text)
        except Exception as e:
            return _respond(plan_id, message, intent, entities, "monte_carlo", {}, f"Monte Carlo failed: {e!s}.")

    # --- task_list ---
    if intent == "task_list":
        tasks = get_tasks_for_plan(plan_id)
        status = entities.get("status")
        if status:
            tasks = [t for t in tasks if (t.get("status") or "").lower() == status.lower()]
        bucket_name = entities.get("bucket_name")
        if bucket_name:
            tasks = [t for t in tasks if (t.get("bucketName") or "").lower() == bucket_name.lower()]
        text = f"Found {len(tasks)} tasks."
        if tasks:
            text += " " + ", ".join(t.get("title", t.get("id")) for t in tasks[:8])
        return _respond(plan_id, message, intent, entities, "task_list", {"tasks": tasks, "count": len(tasks)}, text)

    # --- analytical (Malloy semantic layer) ---
    if intent == "analytical":
        logger.info("chat_service: analytical intent — using Malloy semantic layer (plan_id=%s)", plan_id)
        tasks = get_tasks_for_plan(plan_id)
        deps = get_planner_task_dependencies(plan_id, None)
        msg_lower = (message or "").lower()
        # Choose named query from message keywords
        if "assignee" in msg_lower or "by person" in msg_lower or "who has" in msg_lower:
            named_query = "tasks_by_assignee"
        elif "incomplete" in msg_lower or "open" in msg_lower and "bucket" in msg_lower or "not completed" in msg_lower:
            named_query = "incomplete_by_bucket"
        elif "summary" in msg_lower or "overview" in msg_lower or "total" in msg_lower and "task" in msg_lower:
            named_query = "plan_summary"
        elif "top" in msg_lower and "bucket" in msg_lower or "most task" in msg_lower:
            named_query = "top_buckets_by_count"
        elif "status" in msg_lower and "bucket" not in msg_lower:
            named_query = "tasks_by_status"
        else:
            named_query = "completion_by_bucket"
        logger.info("chat_service: Malloy named_query=%s (tasks=%s, deps=%s)", named_query, len(tasks), len(deps))
        try:
            from congress_twin.services.malloy_runner import run_malloy_query
            rows = run_malloy_query(plan_id, tasks, deps, named_query=named_query)
        except Exception as e:
            logger.warning("chat_service: Malloy run_malloy_query failed: %s", e)
            rows = None
        if rows is not None and len(rows) > 0:
            logger.info("chat_service: Malloy returned %s row(s), formatting response", len(rows))
            if named_query == "completion_by_bucket":
                lines = [f"**{r.get('bucket_name', '')}**: {r.get('task_count', 0)} tasks, {r.get('completion_pct', 0):.0f}% complete" for r in rows]
            elif named_query == "top_buckets_by_count":
                lines = [f"**{r.get('bucket_name', '')}**: {r.get('task_count', 0)} tasks" for r in rows]
            elif named_query == "tasks_by_status":
                lines = [f"**{r.get('status', '')}**: {r.get('task_count', 0)} tasks" for r in rows]
            elif named_query == "tasks_by_assignee":
                lines = [f"**{r.get('assignee_names', '')}**: {r.get('task_count', 0)} tasks" for r in rows]
            elif named_query == "incomplete_by_bucket":
                lines = [f"**{r.get('bucket_name', '')}**: {r.get('task_count', 0)} incomplete" for r in rows]
            elif named_query == "plan_summary" and rows:
                r = rows[0]
                lines = [f"**Plan summary:** {r.get('task_count', 0)} tasks, {r.get('completed_count', 0)} completed ({r.get('completion_pct', 0):.0f}% complete)."]
            else:
                lines = [f"**{list(r.keys())[0]}**: {list(r.values())[0]}" for r in rows[:15]]
            text = "\n".join(lines) if lines else "No data."
            return _respond(plan_id, message, intent, entities, "analytical", {"rows": rows}, text)
        # Query was attempted but failed or returned no data — do not suggest installing deps
        logger.info("chat_service: Malloy query failed or returned no data")
        return _respond(
            plan_id,
            message,
            intent,
            entities,
            "analytical",
            {},
            "Analytics query didn’t return results. Please try again or rephrase (e.g. \"Completion by bucket\", \"Count by status\").",
        )

    # --- summary (default) ---
    tasks = get_tasks_for_plan(plan_id)
    completed = sum(1 for t in tasks if t.get("status") == "completed")
    total = len(tasks)
    text = f"You have {total} tasks. {completed} completed."
    text += " Try: 'What needs attention?', 'Critical path', 'Impact of delaying task-X'. Analytics: 'Completion by bucket', 'Count by status', 'Tasks by assignee', 'Incomplete by bucket', 'Plan summary', 'Top buckets'."
    return _respond(plan_id, message, intent, entities, "summary", {"total": total, "completed": completed}, text)
