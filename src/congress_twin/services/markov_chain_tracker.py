"""
Markov Chain State Tracking: State-based task modeling per ACP_03 PDF.

States: NotStarted, Planning, InProgress, Blocked, UnderReview, Completed, Cancelled
Transition probabilities calibrated from historical data.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from congress_twin.db.planner_repo import get_planner_tasks

logger = logging.getLogger(__name__)


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """Parse ISO datetime string."""
    if not dt_str:
        return None
    try:
        dt_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def _get_task_state(task: dict[str, Any]) -> str:
    """Map task to Markov chain state."""
    percent_complete = task.get("percentComplete", 0)
    status = task.get("status", "notStarted")
    
    if percent_complete >= 100:
        return "Completed"
    elif status == "cancelled" or "cancel" in (task.get("description") or "").lower():
        return "Cancelled"
    elif percent_complete == 50:
        # Check if blocked (stuck at 50% for too long)
        completed = _parse_datetime(task.get("completedDateTime"))
        due = _parse_datetime(task.get("dueDateTime"))
        if due and not completed:
            # If past due and still at 50%, likely blocked
            if datetime.now() > due + timedelta(days=7):
                return "Blocked"
        return "InProgress"
    elif percent_complete > 0:
        return "InProgress"
    else:
        # Check if assigned (Planning) or not (NotStarted)
        assignees = task.get("assignees") or []
        if assignees:
            return "Planning"
        return "NotStarted"


def build_transition_matrix(plan_ids: list[str]) -> dict[str, dict[str, float]]:
    """
    Build transition probability matrix from historical data.
    Returns: {from_state: {to_state: probability}}
    """
    all_tasks = []
    for plan_id in plan_ids:
        tasks = get_planner_tasks(plan_id)
        all_tasks.extend(tasks)
    
    # Track state transitions (simplified: infer from current state distribution)
    # In real implementation, would track state changes over time via audit log
    state_counts: dict[str, int] = defaultdict(int)
    transitions: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    for task in all_tasks:
        state = _get_task_state(task)
        state_counts[state] += 1
        
        # Infer transitions based on task lifecycle
        created = _parse_datetime(task.get("createdDateTime"))
        completed = _parse_datetime(task.get("completedDateTime"))
        
        if completed:
            # Completed path
            transitions["NotStarted"]["Planning"] += 1
            transitions["Planning"]["InProgress"] += 1
            transitions["InProgress"]["Completed"] += 1
        elif state == "Blocked":
            transitions["InProgress"]["Blocked"] += 1
            transitions["Blocked"]["InProgress"] += 1  # Recovery
        elif state == "InProgress":
            transitions["Planning"]["InProgress"] += 1
    
    # Normalize to probabilities
    transition_matrix: dict[str, dict[str, float]] = {}
    states = ["NotStarted", "Planning", "InProgress", "Blocked", "UnderReview", "Completed", "Cancelled"]
    
    for from_state in states:
        transition_matrix[from_state] = {}
        total = sum(transitions[from_state].values())
        
        if total == 0:
            # Default transitions
            if from_state == "NotStarted":
                transition_matrix[from_state] = {"Planning": 0.7, "NotStarted": 0.3}
            elif from_state == "Planning":
                transition_matrix[from_state] = {"InProgress": 0.8, "Planning": 0.2}
            elif from_state == "InProgress":
                transition_matrix[from_state] = {"UnderReview": 0.4, "Blocked": 0.15, "InProgress": 0.45}
            elif from_state == "Blocked":
                transition_matrix[from_state] = {"InProgress": 0.6, "Blocked": 0.4}
            elif from_state == "UnderReview":
                transition_matrix[from_state] = {"Completed": 0.7, "InProgress": 0.3}
            elif from_state in ["Completed", "Cancelled"]:
                transition_matrix[from_state] = {from_state: 1.0}  # Absorbing
        else:
            for to_state in states:
                count = transitions[from_state].get(to_state, 0)
                transition_matrix[from_state][to_state] = count / total if total > 0 else 0.0
    
    return transition_matrix


def compute_expected_completion_time(
    current_state: str,
    transition_matrix: dict[str, dict[str, float]],
    base_duration_days: float = 10.0,
) -> dict[str, Any]:
    """
    Compute expected completion time using fundamental matrix (simplified).
    Returns expected time and variance.
    """
    # Simplified: use state-based duration multipliers
    state_durations = {
        "NotStarted": 0,
        "Planning": base_duration_days * 0.2,
        "InProgress": base_duration_days * 0.6,
        "Blocked": base_duration_days * 0.3,  # Additional delay
        "UnderReview": base_duration_days * 0.2,
        "Completed": 0,
        "Cancelled": 0,
    }
    
    # Expected time from current state to completion
    expected_time = 0.0
    current = current_state
    visited = set()
    max_iterations = 100
    
    for _ in range(max_iterations):
        if current == "Completed" or current == "Cancelled":
            break
        if current in visited:
            break
        visited.add(current)
        
        expected_time += state_durations.get(current, 0)
        
        # Sample next state
        transitions = transition_matrix.get(current, {})
        if not transitions:
            break
        
        # Weighted random choice
        import random
        rand = random.random()
        cumsum = 0.0
        for next_state, prob in transitions.items():
            cumsum += prob
            if rand <= cumsum:
                current = next_state
                break
    
    return {
        "expected_completion_days": expected_time,
        "current_state": current_state,
        "variance": expected_time * 0.3,  # Simplified variance
    }


def get_markov_analysis(plan_id: str, task_id: str | None = None) -> dict[str, Any]:
    """
    Get Markov chain analysis for plan or specific task.
    """
    historical_plan_ids = ["congress-2022", "congress-2023", "congress-2024"]
    transition_matrix = build_transition_matrix(historical_plan_ids)
    
    # Use get_tasks_for_plan so simulated tasks are included
    tasks = get_tasks_for_plan(plan_id)
    
    if task_id:
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return {"error": "Task not found"}
        
        current_state = _get_task_state(task)
        start = _parse_datetime(task.get("startDateTime"))
        due = _parse_datetime(task.get("dueDateTime"))
        base_duration = (due - start).total_seconds() / 86400 if (start and due) else 10.0
        
        expected = compute_expected_completion_time(current_state, transition_matrix, base_duration)
        
        return {
            "task_id": task_id,
            "current_state": current_state,
            "transition_matrix": transition_matrix,
            "expected_completion": expected,
        }
    else:
        # Analyze all tasks
        task_analyses = []
        for task in tasks:
            current_state = _get_task_state(task)
            start = _parse_datetime(task.get("startDateTime"))
            due = _parse_datetime(task.get("dueDateTime"))
            base_duration = (due - start).total_seconds() / 86400 if (start and due) else 10.0
            
            expected = compute_expected_completion_time(current_state, transition_matrix, base_duration)
            task_analyses.append({
                "task_id": task.get("id"),
                "title": task.get("title"),
                "current_state": current_state,
                "expected_completion_days": expected["expected_completion_days"],
            })
        
        return {
            "plan_id": plan_id,
            "transition_matrix": transition_matrix,
            "task_analyses": task_analyses,
        }
