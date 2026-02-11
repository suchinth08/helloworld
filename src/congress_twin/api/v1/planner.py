"""
Planner API v1 — tasks, dependencies, critical path, attention dashboard, advanced (Commander).

NVS-GenAI: Resource-centric URIs; version in path.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from congress_twin.config import get_settings
from congress_twin.services.external_events_service import (
    approve_proposed_action,
    delete_event_and_actions,
    delete_proposed_action_only,
    get_alerts,
    ingest_external_event,
    reject_proposed_action,
)
from congress_twin.services.monte_carlo_service import run_monte_carlo
from congress_twin.db.planner_repo import get_planner_task_with_details
from congress_twin.services.planner_service import (
    get_attention_dashboard,
    get_changes_since_sync,
    get_critical_path,
    get_dependencies,
    get_execution_tasks,
    get_milestone_analysis,
    get_mitigation_feed,
    get_probability_gantt,
    get_tasks_for_plan,
    get_veeva_insights,
    seed_congress_plan,
    sync_planner_tasks,
)
from congress_twin.services.task_intelligence import get_task_intelligence
from congress_twin.services.planner_simulated_data import DEFAULT_PLAN_ID

router = APIRouter()


class ExternalEventIngestBody(BaseModel):
    event_type: str = Field(default="external", description="e.g. flight_cancellation, participant_meeting_cancelled")
    title: Optional[str] = None
    description: Optional[str] = None
    severity: str = Field(default="medium", description="low, medium, high")
    affected_task_ids: Optional[list[str]] = Field(default=None, description="Task IDs impacted")
    payload: Optional[dict[str, Any]] = Field(default=None, description="e.g. shift_days")


def _validate_plan(plan_id: str) -> None:
    if plan_id != DEFAULT_PLAN_ID:
        raise HTTPException(status_code=404, detail="Plan not found")


@router.get("/tasks/{plan_id}")
async def get_tasks(plan_id: str) -> dict:
    """
    Get task list for a plan (from DB if synced, else simulated for default plan).
    """
    tasks = get_tasks_for_plan(plan_id)
    if not tasks and plan_id != DEFAULT_PLAN_ID:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"plan_id": plan_id, "tasks": tasks, "count": len(tasks)}


@router.get("/tasks/{plan_id}/{task_id}")
async def get_task_details(plan_id: str, task_id: str) -> dict:
    """
    Get a single task with all details (checklist, references, dependencies).
    """
    task = get_planner_task_with_details(plan_id, task_id)
    if not task:
        # Fallback to simulated data if not in DB
        tasks = get_tasks_for_plan(plan_id)
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
    return {"plan_id": plan_id, "task": task}


@router.get("/tasks/{plan_id}/{task_id}/intelligence")
async def get_task_intelligence_endpoint(plan_id: str, task_id: str, include_simulations: bool = Query(default=True)) -> dict:
    """
    Get AI-driven intelligence and optimization suggestions for a task.
    Includes Monte Carlo predictions, Markov Chain analysis, dependency risks, reassignment recommendations.
    """
    _validate_plan(plan_id)
    intelligence = get_task_intelligence(plan_id, task_id, include_simulations=include_simulations)
    if "error" in intelligence:
        raise HTTPException(status_code=404, detail=intelligence["error"])
    return intelligence


@router.get("/attention-dashboard/{plan_id}")
async def get_attention_dashboard_endpoint(plan_id: str) -> dict:
    """
    What needs attention: blockers, overdue, due next 7d, critical path due next, recently changed.
    """
    _validate_plan(plan_id)
    return get_attention_dashboard(plan_id)


@router.get("/changes-since-sync/{plan_id}")
async def get_changes_since_sync_endpoint(plan_id: str) -> dict:
    """Tasks modified since previous sync (for 'Changes since publish' panel)."""
    _validate_plan(plan_id)
    return get_changes_since_sync(plan_id)


@router.get("/execution-tasks/{plan_id}")
async def get_execution_tasks_endpoint(plan_id: str) -> dict:
    """Tasks with risk badges (blocked, blocking, at_risk, overdue) and upstream/downstream counts for Dependency Lens."""
    _validate_plan(plan_id)
    tasks = get_execution_tasks(plan_id)
    return {"plan_id": plan_id, "tasks": tasks, "count": len(tasks)}


@router.get("/plan-link")
async def get_plan_link(plan_id: str = Query(DEFAULT_PLAN_ID, description="Plan ID")) -> dict:
    """Optional direct link to open the plan in MS Planner. Returns empty url if not configured."""
    _validate_plan(plan_id)
    url = get_settings().planner_plan_url or ""
    return {"plan_id": plan_id, "url": url}


@router.get("/tasks/{plan_id}/dependencies/{task_id}")
async def get_task_dependencies(plan_id: str, task_id: str) -> dict:
    """
    Upstream (must finish before this), downstream (impacted if this slips), impact statement.
    """
    _validate_plan(plan_id)
    tasks = get_tasks_for_plan(plan_id)
    if not any(t["id"] == task_id for t in tasks):
        raise HTTPException(status_code=404, detail="Task not found")
    return get_dependencies(task_id, plan_id)


@router.get("/critical-path/{plan_id}")
async def get_critical_path_endpoint(plan_id: str) -> dict:
    """Longest dependency chain (critical path)."""
    _validate_plan(plan_id)
    return get_critical_path(plan_id)


@router.get("/milestone-analysis/{plan_id}")
async def get_milestone_analysis_endpoint(
    plan_id: str,
    event_date: str | None = Query(None, description="ISO date for milestone (e.g. 2025-03-01)"),
) -> dict:
    """
    Milestone / Event Date lane: tasks before event date, at-risk tasks (due after event).
    """
    _validate_plan(plan_id)
    event_dt = None
    if event_date:
        try:
            event_dt = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="event_date must be ISO format")
    return get_milestone_analysis(plan_id, event_dt)


@router.post("/sync/{plan_id}")
async def sync_plan(plan_id: str) -> dict:
    """
    Trigger sync from MS Planner (any plan_id). Persists to DB when Graph is configured.
    When Graph is not configured, upserts Congress seed data to DB.
    """
    return sync_planner_tasks(plan_id)


@router.post("/seed")
async def seed_plan(
    plan_id: str = Query(DEFAULT_PLAN_ID, description="Plan to seed with Congress data"),
) -> dict:
    """
    Seed DB with Novartis Congress event scheduling data (dev/bootstrap).
    Ensures tables, upserts tasks, sets sync state. After seeding, UI uses DB for this plan.
    """
    _validate_plan(plan_id)
    return seed_congress_plan(plan_id)


# --- Advanced view (Commander): probability gantt, mitigation feed, veeva, SSE ---

@router.get("/probability-gantt/{plan_id}")
async def get_probability_gantt_endpoint(plan_id: str) -> dict:
    """Tasks with start/end, confidence %, variance for Probability Gantt."""
    _validate_plan(plan_id)
    return get_probability_gantt(plan_id)


@router.get("/mitigation-feed/{plan_id}")
async def get_mitigation_feed_endpoint(plan_id: str) -> dict:
    """Agent interventions / mitigation feed for Commander View."""
    _validate_plan(plan_id)
    return get_mitigation_feed(plan_id)


@router.get("/veeva-insights/{plan_id}")
async def get_veeva_insights_endpoint(plan_id: str) -> dict:
    """KOL alignment and staff fatigue insights (simulated)."""
    _validate_plan(plan_id)
    return get_veeva_insights(plan_id)


# --- Monte Carlo, external events, alerts, human-in-the-loop ---

@router.get("/monte-carlo/{plan_id}")
async def get_monte_carlo(
    plan_id: str,
    n_simulations: int = Query(500, ge=100, le=2000),
    event_date: str | None = Query(None, description="ISO date for event/milestone"),
    seed: int | None = Query(None, description="Random seed for reproducibility"),
) -> dict:
    """
    Run Monte Carlo simulation: P(on-time), percentile end dates, risk tasks.
    Agent suggestions (enhancements and modifications) included.
    """
    _validate_plan(plan_id)
    return run_monte_carlo(plan_id, n_simulations=n_simulations, event_date_iso=event_date, seed=seed)


@router.post("/external-events/{plan_id}")
async def post_external_event(plan_id: str, body: ExternalEventIngestBody) -> dict:
    """
    Ingest external event (external REST API). Call from webhooks or external systems.
    E.g. flight_cancellation, participant_meeting_cancelled. Creates alert and agent proposals (HITL).
    """
    _validate_plan(plan_id)
    return ingest_external_event(
        plan_id=plan_id,
        event_type=body.event_type,
        title=body.title,
        description=body.description,
        severity=body.severity,
        affected_task_ids=body.affected_task_ids,
        payload=body.payload,
    )


@router.delete("/external-events/{plan_id}/{event_id}")
async def delete_external_event(plan_id: str, event_id: int) -> dict:
    """Delete an external event and all its proposed actions. For testing / cleanup."""
    _validate_plan(plan_id)
    result = delete_event_and_actions(event_id, plan_id)
    if not result["deleted"]:
        raise HTTPException(status_code=404, detail="Event not found or already deleted")
    return result


@router.delete("/proposed-actions/{plan_id}/{action_id}")
async def delete_proposed_action(plan_id: str, action_id: int) -> dict:
    """Delete a single proposed action (any status). For testing / cleanup."""
    _validate_plan(plan_id)
    result = delete_proposed_action_only(action_id, plan_id)
    if not result["deleted"]:
        raise HTTPException(status_code=404, detail="Action not found or already deleted")
    return result


@router.get("/alerts/{plan_id}")
async def get_alerts_endpoint(plan_id: str) -> dict:
    """Dashboard alerts: external events + pending agent proposed actions (HITL)."""
    _validate_plan(plan_id)
    return get_alerts(plan_id)


@router.get("/proposed-actions/{plan_id}")
async def get_proposed_actions_endpoint(
    plan_id: str,
    status: str | None = Query(None, description="pending, approved, rejected"),
) -> dict:
    """List agent proposed actions (re-adjustments) for human approval."""
    _validate_plan(plan_id)
    from congress_twin.db.events_repo import get_proposed_actions
    actions = get_proposed_actions(plan_id, status=status)
    return {"plan_id": plan_id, "actions": actions, "count": len(actions)}


@router.post("/proposed-actions/{plan_id}/{action_id}/approve")
async def approve_action(
    plan_id: str,
    action_id: int,
    decided_by: str | None = Query(None),
) -> dict:
    """Human approves proposed action; agent applies re-adjustment (e.g. shift task due date)."""
    _validate_plan(plan_id)
    result = approve_proposed_action(action_id, plan_id, decided_by=decided_by)
    if not result:
        raise HTTPException(status_code=404, detail="Action not found or not pending")
    return {"plan_id": plan_id, "action_id": action_id, "status": "approved", "action": result}


@router.post("/proposed-actions/{plan_id}/{action_id}/reject")
async def reject_action(
    plan_id: str,
    action_id: int,
    decided_by: str | None = Query(None),
) -> dict:
    """Human rejects proposed action."""
    _validate_plan(plan_id)
    result = reject_proposed_action(action_id, plan_id, decided_by=decided_by)
    if not result:
        raise HTTPException(status_code=404, detail="Action not found or not pending")
    return {"plan_id": plan_id, "action_id": action_id, "status": "rejected", "action": result}


@router.get("/stream")
async def stream_plan_vs_reality(plan_id: str = Query(DEFAULT_PLAN_ID, description="Plan ID")) -> StreamingResponse:
    """
    SSE stream: Plan vs Reality and agent updates (simulated).
    Client connects with EventSource; events are JSON.
    """
    async def event_stream():
        # Send initial snapshot
        tasks = get_tasks_for_plan(plan_id)
        yield f"data: {json.dumps({'type': 'snapshot', 'plan_id': plan_id, 'tasks_count': len(tasks), 'message': 'Plan vs Reality snapshot'})}\n\n"
        await asyncio.sleep(0.5)
        # Send a couple of simulated updates
        yield f"data: {json.dumps({'type': 'update', 'message': 'OptimizationAgent: schedule stable.', 'at': datetime.utcnow().isoformat() + 'Z'})}\n\n"
        await asyncio.sleep(1.0)
        yield f"data: {json.dumps({'type': 'heartbeat', 'plan_id': plan_id})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
