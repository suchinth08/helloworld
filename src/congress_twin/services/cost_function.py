"""
Cost Function Calculation: Multi-objective optimization per ACP_03 PDF.

C_total = w1*C_schedule + w2*C_resource + w3*C_risk + w4*C_quality + w5*C_disruption
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from congress_twin.db.planner_repo import get_planner_tasks, get_planner_task_dependencies
from congress_twin.services.planner_simulated_data import DEFAULT_PLAN_ID


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """Parse ISO datetime string."""
    if not dt_str:
        return None
    try:
        dt_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def compute_schedule_cost(tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]], alpha: float = 1.0, beta: float = 0.5, gamma: float = 3.0) -> float:
    """
    Schedule cost: Quadratic tardiness + linear earliness + critical path multiplier.
    """
    # Build dependency graph to identify critical path tasks
    dep_map = {dep["taskId"]: dep for dep in dependencies}
    downstream_count: dict[str, int] = defaultdict(int)
    
    for dep in dependencies:
        downstream_count[dep.get("dependsOnTaskId", "")] += 1
    
    # Find tasks with high downstream count (critical path candidates)
    max_downstream = max(downstream_count.values()) if downstream_count else 0
    critical_path_threshold = max_downstream * 0.7
    
    cost = 0.0
    
    for task in tasks:
        due = _parse_datetime(task.get("dueDateTime"))
        completed = _parse_datetime(task.get("completedDateTime"))
        start = _parse_datetime(task.get("startDateTime"))
        
        if not (due and start):
            continue
        
        if completed:
            actual_end = completed
        else:
            # Estimate from current state
            if task.get("percentComplete", 0) >= 100:
                actual_end = due
            else:
                # Estimate remaining time
                planned_duration = (due - start).total_seconds() / 86400
                remaining = planned_duration * (1 - task.get("percentComplete", 0) / 100)
                actual_end = datetime.now() + timedelta(days=remaining)
        
        tardiness_days = max(0, (actual_end - due).total_seconds() / 86400)
        earliness_days = max(0, (due - actual_end).total_seconds() / 86400)
        
        # Quadratic tardiness penalty
        cost += alpha * (tardiness_days ** 2)
        
        # Linear earliness bonus (diminishing)
        cost -= beta * earliness_days
        
        # Critical path multiplier
        task_id = task.get("id", "")
        is_critical = downstream_count.get(task_id, 0) >= critical_path_threshold
        if is_critical and tardiness_days > 0:
            cost += gamma * tardiness_days
    
    return cost


def compute_resource_cost(tasks: list[dict[str, Any]], delta: float = 1.0, epsilon: float = 0.5, zeta: float = 0.2) -> float:
    """
    Resource cost: Over-allocation + under-utilization + context switch penalties.
    """
    # Compute utilization per assignee
    assignee_tasks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        assignees = task.get("assignees") or []
        for assignee in assignees:
            assignee_tasks[assignee].append(task)
    
    cost = 0.0
    U_max = 5.0  # Max concurrent tasks
    U_min = 1.0  # Min desired concurrent tasks
    
    for assignee, task_list in assignee_tasks.items():
        # Count concurrent tasks (simplified: count all assigned)
        utilization = len(task_list)
        
        # Over-allocation penalty (quadratic)
        if utilization > U_max:
            cost += delta * ((utilization - U_max) ** 2)
        
        # Under-utilization waste
        if utilization < U_min:
            cost += epsilon * (U_min - utilization)
        
        # Context switch penalty (each additional task adds overhead)
        if utilization > 1:
            cost += zeta * (utilization - 1)
    
    return cost


def compute_risk_cost(tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]], eta: float = 2.0, delay_threshold_days: float = 7.0) -> float:
    """
    Risk cost: P(delay > threshold) * impact_magnitude.
    """
    # Build downstream count for impact
    downstream_count: dict[str, int] = defaultdict(int)
    for dep in dependencies:
        downstream_count[dep.get("dependsOnTaskId", "")] += 1
    
    cost = 0.0
    
    for task in tasks:
        priority = task.get("priority", 5)
        due = _parse_datetime(task.get("dueDateTime"))
        completed = _parse_datetime(task.get("completedDateTime"))
        start = _parse_datetime(task.get("startDateTime"))
        
        if not (due and start):
            continue
        
        # Estimate delay probability (simplified: based on current state)
        delay_prob = 0.0
        if not completed:
            planned_duration = (due - start).total_seconds() / 86400
            elapsed = (datetime.now() - start).total_seconds() / 86400 if start < datetime.now() else 0
            progress = task.get("percentComplete", 0) / 100
            
            if progress > 0:
                # If behind schedule
                expected_elapsed = planned_duration * progress
                if elapsed > expected_elapsed:
                    delay_prob = min(1.0, (elapsed - expected_elapsed) / planned_duration)
            else:
                # Not started yet: base probability
                delay_prob = 0.3
        
        # Impact magnitude = priority weight + downstream dependencies
        impact = (11 - priority) / 10.0  # Higher priority = lower number = higher impact
        impact += downstream_count.get(task.get("id", ""), 0) * 0.1
        
        if delay_prob > 0:
            cost += eta * delay_prob * impact
    
    return cost


def compute_quality_cost(tasks: list[dict[str, Any]]) -> float:
    """
    Quality cost: Topic mismatch, preference violations, audience overlap (for speaker assignments).
    Simplified implementation.
    """
    # For now, return 0 (would need speaker/topic matching data)
    return 0.0


def compute_disruption_cost(plan_id: str, lambda_weight: float = 1.0, mu: float = 0.5, nu: float = 0.3) -> float:
    """
    Disruption cost: Cascade depth, human approval latency, plan delta.
    Simplified: return base cost.
    """
    # Would need to track replan events and cascade depth
    return 0.0


def compute_total_cost(
    plan_id: str = DEFAULT_PLAN_ID,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Compute total multi-objective cost.
    
    Args:
        plan_id: Plan ID
        weights: Optional weights dict with keys: w1, w2, w3, w4, w5
    """
    if weights is None:
        weights = {"w1": 1.0, "w2": 0.8, "w3": 1.2, "w4": 0.5, "w5": 0.3}
    
    tasks = get_planner_tasks(plan_id)
    dependencies = get_planner_task_dependencies(plan_id)
    
    c_schedule = compute_schedule_cost(tasks, dependencies)
    c_resource = compute_resource_cost(tasks)
    c_risk = compute_risk_cost(tasks, dependencies)
    c_quality = compute_quality_cost(tasks)
    c_disruption = compute_disruption_cost(plan_id)
    
    c_total = (
        weights["w1"] * c_schedule +
        weights["w2"] * c_resource +
        weights["w3"] * c_risk +
        weights["w4"] * c_quality +
        weights["w5"] * c_disruption
    )
    
    return {
        "plan_id": plan_id,
        "total_cost": c_total,
        "cost_breakdown": {
            "schedule": c_schedule,
            "resource": c_resource,
            "risk": c_risk,
            "quality": c_quality,
            "disruption": c_disruption,
        },
        "weights": weights,
    }
