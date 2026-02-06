"""
External events ingestion and agent re-adjustments (human-in-the-loop).

Ingest events (flight cancellation, participant meeting cancelled); create dashboard alerts;
agent proposes re-adjustments; human approves/rejects; apply approved actions to tasks.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from congress_twin.db.events_repo import (
    delete_external_event as repo_delete_external_event,
    delete_proposed_action as repo_delete_proposed_action,
    get_external_events,
    get_proposed_action_by_id,
    get_proposed_actions,
    insert_external_event,
    insert_proposed_action,
    update_proposed_action_status,
)
from congress_twin.db.planner_repo import get_planner_tasks, upsert_planner_tasks
from congress_twin.services.planner_simulated_data import DEFAULT_PLAN_ID
from congress_twin.services.planner_service import get_tasks_for_plan


def ingest_external_event(
    plan_id: str = DEFAULT_PLAN_ID,
    event_type: str = "external",
    title: str = "",
    description: Optional[str] = None,
    severity: str = "medium",
    affected_task_ids: Optional[list[str]] = None,
    payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Ingest an external event (e.g. flight_cancellation, participant_meeting_cancelled).
    Stores the event (alert in dashboard) and triggers agent to propose re-adjustments (HITL).
    """
    payload = payload or {}
    if not title and event_type == "flight_cancellation":
        title = "Flight cancellation impacting travel"
    if not title and event_type == "participant_meeting_cancelled":
        title = "Participant meeting cancelled – scheduling impact"
    if not title:
        title = f"External event: {event_type}"

    event = insert_external_event(
        plan_id=plan_id,
        event_type=event_type,
        title=title,
        description=description,
        severity=severity,
        affected_task_ids=affected_task_ids or [],
        payload=payload,
    )

    # Agent: propose re-adjustments based on event type and affected tasks
    proposed = _agent_propose_readjustments(plan_id, event_type, event["id"], affected_task_ids, payload)
    return {"event": event, "proposed_actions": proposed}


def _agent_propose_readjustments(
    plan_id: str,
    event_type: str,
    external_event_id: int,
    affected_task_ids: Optional[list[str]],
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """Agent proposes re-adjustments (shift dates, reassign) for human approval."""
    tasks = get_tasks_for_plan(plan_id)
    task_by_id = {t["id"]: t for t in tasks}
    affected = affected_task_ids or []
    # If no affected tasks given, pick from critical path or first in-progress
    if not affected:
        in_progress = [t["id"] for t in tasks if t.get("status") == "inProgress"]
        affected = in_progress[:2] if in_progress else [t["id"] for t in tasks[:2]]

    proposed: list[dict[str, Any]] = []
    shift_days = payload.get("shift_days", 2)

    if event_type == "flight_cancellation":
        # Propose shifting affected tasks by N days
        for tid in affected[:3]:
            t = task_by_id.get(tid)
            if not t or t.get("status") == "completed":
                continue
            proposed.append(insert_proposed_action(
                plan_id=plan_id,
                external_event_id=external_event_id,
                task_id=tid,
                action_type="shift_due_date",
                title=f"Shift due date: {t.get('title', tid)}",
                description=f"Flight cancellation may delay travel. Agent suggests shifting due date by +{shift_days} days. Approve to apply.",
                payload={"task_id": tid, "shift_days": shift_days, "reason": "flight_cancellation"},
            ))

    if event_type == "participant_meeting_cancelled":
        # Propose reassignment or date shift for affected tasks
        for tid in affected[:3]:
            t = task_by_id.get(tid)
            if not t or t.get("status") == "completed":
                continue
            proposed.append(insert_proposed_action(
                plan_id=plan_id,
                external_event_id=external_event_id,
                task_id=tid,
                action_type="shift_due_date",
                title=f"Re-adjust schedule: {t.get('title', tid)}",
                description=f"Participant meeting cancelled. Propose shifting by +{shift_days} days to allow rescheduling. Approve to apply.",
                payload={"task_id": tid, "shift_days": shift_days, "reason": "participant_meeting_cancelled"},
            ))

    # Generic: at least one proposal
    if not proposed and affected:
        tid = affected[0]
        t = task_by_id.get(tid)
        if t:
            proposed.append(insert_proposed_action(
                plan_id=plan_id,
                external_event_id=external_event_id,
                task_id=tid,
                action_type="shift_due_date",
                title=f"Re-adjust: {t.get('title', tid)}",
                description="Agent suggests shifting due date to absorb external impact. Approve to apply.",
                payload={"task_id": tid, "shift_days": shift_days},
            ))

    return proposed


def get_alerts(plan_id: str = DEFAULT_PLAN_ID, limit: int = 30) -> dict[str, Any]:
    """Dashboard alerts: recent external events + pending proposed actions."""
    events = get_external_events(plan_id, limit=limit)
    pending = get_proposed_actions(plan_id, status="pending", limit=20)
    return {
        "plan_id": plan_id,
        "external_events": events,
        "pending_actions_count": len(pending),
        "pending_actions": pending,
    }


def approve_proposed_action(
    action_id: int,
    plan_id: str = DEFAULT_PLAN_ID,
    decided_by: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Human approves; then apply the action (e.g. update task due date in DB)."""
    updated = update_proposed_action_status(action_id, plan_id, "approved", decided_by=decided_by)
    if updated:
        _apply_proposed_action(plan_id, updated)
    return updated


def reject_proposed_action(
    action_id: int,
    plan_id: str = DEFAULT_PLAN_ID,
    decided_by: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    return update_proposed_action_status(action_id, plan_id, "rejected", decided_by=decided_by)


def _apply_proposed_action(plan_id: str, action: dict[str, Any]) -> None:
    """Apply an approved action to the plan (e.g. shift task due date in DB)."""
    if action.get("status") != "approved":
        return
    action_type = action.get("action_type")
    payload = action.get("payload") or {}
    task_id = action.get("task_id") or payload.get("task_id")
    if not task_id:
        return

    tasks = get_planner_tasks(plan_id)
    if not tasks:
        return
    task_list = list(tasks)
    for t in task_list:
        if t.get("id") != task_id:
            continue
        shift_days = payload.get("shift_days", 0)
        due_s = t.get("dueDateTime")
        start_s = t.get("startDateTime")
        if not due_s and not start_s:
            return
        def _parse(s: str | None):
            if not s:
                return None
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return None
        due_dt = _parse(due_s)
        start_dt = _parse(start_s)
        if due_dt:
            due_dt = due_dt + timedelta(days=shift_days)
            t["dueDateTime"] = due_dt.isoformat().replace("+00:00", "Z")
        if start_dt:
            start_dt = start_dt + timedelta(days=shift_days)
            t["startDateTime"] = start_dt.isoformat().replace("+00:00", "Z")
        break

    upsert_planner_tasks(plan_id, task_list)


def delete_event_and_actions(event_id: int, plan_id: str = DEFAULT_PLAN_ID) -> dict[str, Any]:
    """Delete an external event and all its proposed actions. For testing / cleanup."""
    deleted = repo_delete_external_event(event_id, plan_id)
    return {"plan_id": plan_id, "event_id": event_id, "deleted": deleted}


def delete_proposed_action_only(action_id: int, plan_id: str = DEFAULT_PLAN_ID) -> dict[str, Any]:
    """Delete a single proposed action (any status). For testing / cleanup."""
    deleted = repo_delete_proposed_action(action_id, plan_id)
    return {"plan_id": plan_id, "action_id": action_id, "deleted": deleted}
