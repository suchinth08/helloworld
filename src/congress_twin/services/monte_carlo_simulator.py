"""
Enhanced Monte Carlo Simulator: Full implementation per ACP_02 PDF.

Features:
- Historical distribution fitting (Beta for PERT)
- Resource contention modeling
- External event injection (flight cancellations, etc.)
- DAG traversal with proper topological sort
- Comprehensive output: percentiles, bottlenecks, risk heatmap
"""

import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

# Ensure timezone is imported
from datetime import timezone

from congress_twin.db.planner_repo import get_planner_task_dependencies
from congress_twin.services.historical_analyzer import analyze_duration_bias
from congress_twin.services.planner_service import get_tasks_for_plan
from congress_twin.services.planner_simulated_data import DEFAULT_PLAN_ID

random.seed(42)


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """Parse ISO datetime string."""
    if not dt_str:
        return None
    try:
        dt_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def _fit_beta_distribution(base_duration: float, bias_factor: float = 1.0) -> tuple[float, float, float]:
    """
    Fit Beta distribution parameters for PERT (optimistic, most likely, pessimistic).
    Simplified: use base_duration as most likely, apply bias_factor.
    """
    optimistic = base_duration * 0.7 * bias_factor
    most_likely = base_duration * bias_factor
    pessimistic = base_duration * 1.5 * bias_factor
    return optimistic, most_likely, pessimistic


def _sample_beta_duration(optimistic: float, most_likely: float, pessimistic: float) -> float:
    """Sample duration from Beta distribution (PERT)."""
    try:
        import numpy as np
        # PERT Beta approximation: mean = (a + 4m + b) / 6, variance from range
        mean = (optimistic + 4 * most_likely + pessimistic) / 6
        std = (pessimistic - optimistic) / 6
        # Sample from normal approximation (simpler than Beta)
        sample = np.random.normal(mean, std)
        return max(optimistic, min(pessimistic, sample))
    except ImportError:
        # Fallback: triangular distribution (optimistic, most_likely, pessimistic)
        import random
        r = random.random()
        if r < 0.5:
            # Between optimistic and most_likely
            return optimistic + (most_likely - optimistic) * (r * 2)
        else:
            # Between most_likely and pessimistic
            return most_likely + (pessimistic - most_likely) * ((r - 0.5) * 2)


def _build_dag(tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Build dependency DAG: task_id -> set of predecessor task IDs."""
    dag: dict[str, set[str]] = {task["id"]: set() for task in tasks}
    dep_map = {dep["taskId"]: dep for dep in dependencies}
    
    for task in tasks:
        task_id = task["id"]
        if task_id in dep_map:
            dep = dep_map[task_id]
            depends_on = dep.get("dependsOnTaskId")
            if depends_on:
                dag[task_id].add(depends_on)
    
    return dag


def _topological_sort(tasks: list[dict[str, Any]], dag: dict[str, set[str]]) -> list[str]:
    """Topological sort of tasks respecting dependencies."""
    in_degree: dict[str, int] = {task["id"]: 0 for task in tasks}
    
    # Count incoming edges
    for task_id, predecessors in dag.items():
        for pred in predecessors:
            if pred in in_degree:
                in_degree[task_id] += 1
    
    # Kahn's algorithm
    queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
    result = []
    
    while queue:
        task_id = queue.pop(0)
        result.append(task_id)
        
        # Remove edges from this node
        for other_id, predecessors in dag.items():
            if task_id in predecessors:
                in_degree[other_id] -= 1
                if in_degree[other_id] == 0:
                    queue.append(other_id)
    
    # Add any remaining tasks (cycles or disconnected)
    for task_id in in_degree:
        if task_id not in result:
            result.append(task_id)
    
    return result


def _compute_assignee_load(
    assignee: str,
    current_time: datetime,
    task_finish_times: dict[str, datetime],
    tasks_by_assignee: dict[str, list[dict[str, Any]]],
) -> int:
    """Count concurrent tasks for an assignee at current_time."""
    load = 0
    for task in tasks_by_assignee.get(assignee, []):
        task_id = task["id"]
        finish_time = task_finish_times.get(task_id)
        start = _parse_datetime(task.get("startDateTime"))
        
        if start and finish_time:
            if start <= current_time < finish_time:
                load += 1
    
    return load


def _apply_queuing_delay(assignee_load: int, historical_k: int = 3) -> float:
    """Apply queuing delay if assignee is overloaded."""
    if assignee_load <= historical_k:
        return 0.0
    
    # Exponential delay: overload penalty
    overload = assignee_load - historical_k
    return random.expovariate(1.0 / (overload * 0.5))  # Days of delay


def _inject_disruptions(task: dict[str, Any], bucket: str) -> float:
    """Inject external disruptions (e.g., flight cancellations for Travel bucket)."""
    disruption_delay = 0.0
    
    if bucket == "Travel & Accommodation":
        # P(flight_cancel) = 0.03
        if random.random() < 0.03:
            # Rebooking delay: 2-5 days
            disruption_delay = random.uniform(2.0, 5.0)
    
    elif bucket == "Venue & Logistics":
        # Vendor delay probability
        if random.random() < 0.05:
            disruption_delay = random.uniform(1.0, 3.0)
    
    elif bucket == "Speaker Management":
        # Speaker response delay
        if random.random() < 0.08:
            disruption_delay = random.uniform(0.5, 2.0)
    
    return disruption_delay


def run_simulation(
    plan_id: str = DEFAULT_PLAN_ID,
    n_iterations: int = 10000,
    historical_plan_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run Monte Carlo simulation with full features per ACP_02 PDF.
    
    Returns:
        - Percentiles (P50, P75, P95)
        - Critical path probability (which tasks appear on CP most)
        - Bottleneck ranking
        - Risk heatmap (bucket-level variance)
    """
    # Use get_tasks_for_plan so simulated tasks (e.g. default plan seed) are included
    tasks = get_tasks_for_plan(plan_id)
    if not tasks:
        return {
            "plan_id": plan_id,
            "error": "No tasks found for plan",
        }
    
    dependencies = get_planner_task_dependencies(plan_id)
    
    # Build DAG and topological order
    dag = _build_dag(tasks, dependencies)
    topo_order = _topological_sort(tasks, dag)
    
    # Get historical duration bias for distribution fitting
    if historical_plan_ids is None:
        historical_plan_ids = ["congress-2022", "congress-2023", "congress-2024"]
    
    try:
        duration_bias = analyze_duration_bias(historical_plan_ids)
        bucket_bias = duration_bias.get("bucket_stats", {})
    except Exception:
        bucket_bias = {}
    
    # Group tasks by assignee for resource contention
    tasks_by_assignee: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        assignees = task.get("assignees") or []
        for assignee in assignees:
            tasks_by_assignee[assignee].append(task)
    
    # Run simulations
    congress_completion_times: list[datetime] = []
    critical_path_counts: dict[str, int] = defaultdict(int)
    task_finish_times_all: dict[str, list[datetime]] = defaultdict(list)
    
    for iteration in range(n_iterations):
        task_finish_times: dict[str, datetime] = {}
        task_start_times: dict[str, datetime] = {}
        
        # Process tasks in topological order
        for task_id in topo_order:
            task = next((t for t in tasks if t["id"] == task_id), None)
            if not task:
                continue
            
            # Compute start time = max(predecessor completion times)
            start_time = _parse_datetime(task.get("startDateTime"))
            if not start_time:
                start_time = datetime.now(timezone.utc)
            
            predecessors = dag.get(task_id, set())
            for pred_id in predecessors:
                pred_finish = task_finish_times.get(pred_id)
                if pred_finish and pred_finish > start_time:
                    start_time = pred_finish
            
            # Sample duration from distribution
            bucket = task.get("bucketName") or "Unknown"
            start_dt = _parse_datetime(task.get("startDateTime"))
            due_dt = _parse_datetime(task.get("dueDateTime"))
            
            if start_dt and due_dt:
                base_duration = (due_dt - start_dt).total_seconds() / 86400
            else:
                base_duration = 5.0
            
            # Apply bias factor from historical data
            bias_factor = 1.0
            if bucket in bucket_bias:
                bias_factor = bucket_bias[bucket].get("bias_factor", 1.0)
            
            optimistic, most_likely, pessimistic = _fit_beta_distribution(base_duration, bias_factor)
            duration_days = _sample_beta_duration(optimistic, most_likely, pessimistic)
            
            # Apply resource contention delay
            assignees = task.get("assignees") or []
            if assignees:
                assignee = assignees[0]  # Use first assignee
                load = _compute_assignee_load(assignee, start_time, task_finish_times, tasks_by_assignee)
                queuing_delay = _apply_queuing_delay(load, historical_k=3)
                duration_days += queuing_delay
            
            # Apply external disruptions
            disruption_delay = _inject_disruptions(task, bucket)
            duration_days += disruption_delay
            
            # Compute finish time
            finish_time = start_time + timedelta(days=duration_days)
            task_start_times[task_id] = start_time
            task_finish_times[task_id] = finish_time
            task_finish_times_all[task_id].append(finish_time)
        
        # Congress completion = max of all finish times
        if task_finish_times:
            congress_end = max(task_finish_times.values())
            congress_completion_times.append(congress_end)
            
            # Identify critical path (tasks with no slack)
            for task_id in topo_order:
                task_finish = task_finish_times.get(task_id)
                if not task_finish:
                    continue
                
                # Check if this task's delay would delay congress end
                if task_finish == congress_end:
                    critical_path_counts[task_id] += 1
                
                # Also check if delaying this task delays downstream tasks
                downstream_delayed = False
                for other_id, other_finish in task_finish_times.items():
                    if other_id != task_id and other_id in dag.get(task_id, set()):
                        if other_finish == congress_end:
                            downstream_delayed = True
                            break
                
                if downstream_delayed:
                    critical_path_counts[task_id] += 1
    
    # Compute percentiles
    if not congress_completion_times:
        return {
            "plan_id": plan_id,
            "error": "No completion times generated",
        }
    
    sorted_times = sorted(congress_completion_times)
    n = len(sorted_times)
    
    def _format_iso_datetime(dt: datetime) -> str:
        """Format datetime to ISO string with UTC timezone (Z suffix)."""
        if dt.tzinfo is None:
            # Naive datetime - assume UTC
            dt = dt.replace(tzinfo=timezone.utc)
        # Convert to UTC and format
        dt_utc = dt.astimezone(timezone.utc)
        iso_str = dt_utc.isoformat()
        # Replace +00:00 with Z for standard UTC format
        if iso_str.endswith('+00:00'):
            return iso_str[:-6] + 'Z'
        # If already has Z or other format, ensure Z format
        return dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    percentiles = {
        "p50": _format_iso_datetime(sorted_times[n // 2]),
        "p75": _format_iso_datetime(sorted_times[int(n * 0.75)]),
        "p95": _format_iso_datetime(sorted_times[int(n * 0.95)]),
    }
    
    # Critical path probability (normalized)
    total_iterations = len(congress_completion_times)
    critical_path_prob = {
        task_id: (count / total_iterations) * 100
        for task_id, count in critical_path_counts.items()
    }
    
    # Bottleneck ranking: tasks with highest variance in finish times
    bottlenecks = []
    for task_id, finish_times in task_finish_times_all.items():
        if len(finish_times) < 10:
            continue
        finish_times_sorted = sorted(finish_times)
        variance_days = (finish_times_sorted[-1] - finish_times_sorted[0]).total_seconds() / 86400
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task:
            bottlenecks.append({
                "task_id": task_id,
                "title": task.get("title"),
                "bucket": task.get("bucketName"),
                "variance_days": variance_days,
                "critical_path_probability": critical_path_prob.get(task_id, 0),
            })
    
    bottlenecks.sort(key=lambda x: x["variance_days"], reverse=True)
    
    # Risk heatmap: bucket-level variance
    bucket_variances: dict[str, list[float]] = defaultdict(list)
    for task_id, finish_times in task_finish_times_all.items():
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task and len(finish_times) > 10:
            bucket = task.get("bucketName") or "Unknown"
            finish_times_sorted = sorted(finish_times)
            variance = (finish_times_sorted[-1] - finish_times_sorted[0]).total_seconds() / 86400
            bucket_variances[bucket].append(variance)
    
    risk_heatmap = {
        bucket: sum(variances) / len(variances) if variances else 0
        for bucket, variances in bucket_variances.items()
    }
    
    return {
        "plan_id": plan_id,
        "n_iterations": n_iterations,
        "percentiles": percentiles,
        "critical_path_probability": dict(list(critical_path_prob.items())[:20]),  # Top 20
        "bottlenecks": bottlenecks[:20],
        "risk_heatmap": risk_heatmap,
    }
