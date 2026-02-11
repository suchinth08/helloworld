"""
Historical Data Analysis Engine: Extract patterns from historical congress data.

Analyzes:
- Duration Intelligence: Estimation bias, PERT parameters
- Dependency Patterns: Implicit dependencies, bottlenecks
- Resource Profiling: Throughput, response latency, capacity
- Risk Patterns: Cancellations, blocks, scope creep
- Timeline Intelligence: Phase durations, milestone rates
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from congress_twin.db.planner_repo import get_planner_tasks, get_planner_task_dependencies, get_planner_task_details

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


def analyze_duration_bias(plan_ids: list[str]) -> dict[str, Any]:
    """
    Analyze duration estimation bias: Compare planned vs actual durations per task type/bucket.
    Returns PERT parameters (optimistic, most likely, pessimistic) per bucket/task type.
    """
    all_tasks = []
    for plan_id in plan_ids:
        tasks = get_planner_tasks(plan_id)
        all_tasks.extend(tasks)
    
    bucket_stats: dict[str, list[float]] = defaultdict(list)
    task_type_stats: dict[str, list[float]] = defaultdict(list)
    
    for task in all_tasks:
        start = _parse_datetime(task.get("startDateTime"))
        due = _parse_datetime(task.get("dueDateTime"))
        completed = _parse_datetime(task.get("completedDateTime"))
        
        if not (start and due):
            continue
        
        planned_duration = (due - start).total_seconds() / 86400  # days
        
        if completed:
            actual_duration = (completed - start).total_seconds() / 86400
            bias = actual_duration / planned_duration if planned_duration > 0 else 1.0
            
            bucket = task.get("bucketName") or "Unknown"
            bucket_stats[bucket].append(bias)
            
            task_type = task.get("title", "").split()[0] if task.get("title") else "Unknown"
            task_type_stats[task_type].append(bias)
    
    # Compute PERT parameters (simplified: use percentiles)
    def compute_pert_params(values: list[float]) -> dict[str, float]:
        if not values:
            return {"optimistic": 0, "most_likely": 0, "pessimistic": 0, "mean": 0, "bias_factor": 1.0}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "optimistic": sorted_vals[int(n * 0.1)] if n > 0 else 0,  # P10
            "most_likely": sorted_vals[int(n * 0.5)] if n > 0 else 0,  # P50 (median)
            "pessimistic": sorted_vals[int(n * 0.9)] if n > 0 else 0,  # P90
            "mean": sum(values) / len(values),
            "bias_factor": sum(values) / len(values),  # Average bias
        }
    
    return {
        "bucket_stats": {bucket: compute_pert_params(vals) for bucket, vals in bucket_stats.items()},
        "task_type_stats": {task_type: compute_pert_params(vals) for task_type, vals in task_type_stats.items()},
    }


def extract_implicit_dependencies(plan_ids: list[str]) -> list[dict[str, Any]]:
    """
    Find implicit dependencies: Tasks where B consistently starts after A completes.
    """
    all_tasks = []
    for plan_id in plan_ids:
        tasks = get_planner_tasks(plan_id)
        all_tasks.extend([(plan_id, t) for t in tasks])
    
    # Group by task title pattern
    task_patterns: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for plan_id, task in all_tasks:
        title = task.get("title", "")
        # Use first few words as pattern
        pattern = " ".join(title.split()[:3]) if title else "Unknown"
        task_patterns[pattern].append((plan_id, task))
    
    implicit_deps = []
    for pattern_a, tasks_a in task_patterns.items():
        for pattern_b, tasks_b in task_patterns.items():
            if pattern_a == pattern_b:
                continue
            
            # Check if tasks_b consistently start after tasks_a complete
            matches = 0
            total = 0
            for plan_id_a, task_a in tasks_a:
                completed_a = _parse_datetime(task_a.get("completedDateTime"))
                if not completed_a:
                    continue
                
                for plan_id_b, task_b in tasks_b:
                    if plan_id_a != plan_id_b:
                        continue
                    start_b = _parse_datetime(task_b.get("startDateTime"))
                    if start_b and start_b >= completed_a:
                        matches += 1
                    total += 1
            
            if total > 0 and matches / total > 0.7:  # 70% consistency threshold
                implicit_deps.append({
                    "from_pattern": pattern_a,
                    "to_pattern": pattern_b,
                    "confidence": matches / total,
                    "occurrences": total,
                })
    
    return implicit_deps


def identify_bottlenecks(plan_ids: list[str]) -> list[dict[str, Any]]:
    """
    Identify bottleneck tasks: Tasks that, when delayed, cause the most downstream delays.
    """
    # Build dependency graph
    all_deps = []
    for plan_id in plan_ids:
        deps = get_planner_task_dependencies(plan_id)
        all_deps.extend([(plan_id, d) for d in deps])
    
    # Count downstream tasks per task
    downstream_count: dict[tuple[str, str], int] = defaultdict(int)  # (plan_id, task_id) -> count
    
    def count_downstream(plan_id: str, task_id: str, visited: set) -> int:
        if (plan_id, task_id) in visited:
            return 0
        visited.add((plan_id, task_id))
        count = 1
        for p_id, dep in all_deps:
            if p_id == plan_id and dep["taskId"] == task_id:
                count += count_downstream(p_id, dep["dependsOnTaskId"], visited)
        return count
    
    bottlenecks = []
    for plan_id in plan_ids:
        tasks = get_planner_tasks(plan_id)
        for task in tasks:
            task_id = task.get("id")
            if not task_id:
                continue
            downstream = count_downstream(plan_id, task_id, set()) - 1  # Exclude self
            if downstream > 0:
                bottlenecks.append({
                    "plan_id": plan_id,
                    "task_id": task_id,
                    "title": task.get("title"),
                    "bucket": task.get("bucketName"),
                    "downstream_count": downstream,
                })
    
    return sorted(bottlenecks, key=lambda x: x["downstream_count"], reverse=True)


def compute_resource_throughput(plan_ids: list[str]) -> dict[str, Any]:
    """
    Compute per-person throughput: Tasks completed per week per assignee.
    """
    all_tasks = []
    for plan_id in plan_ids:
        tasks = get_planner_tasks(plan_id)
        all_tasks.extend(tasks)
    
    assignee_stats: dict[str, list[float]] = defaultdict(list)  # assignee -> list of completion times
    
    for task in all_tasks:
        assignees = task.get("assignees") or []
        completed = _parse_datetime(task.get("completedDateTime"))
        created = _parse_datetime(task.get("createdDateTime"))
        
        if not (completed and created and assignees):
            continue
        
        duration_days = (completed - created).total_seconds() / 86400
        
        for assignee in assignees:
            assignee_stats[assignee].append(duration_days)
    
    throughput = {}
    for assignee, durations in assignee_stats.items():
        if durations:
            avg_duration = sum(durations) / len(durations)
            tasks_per_week = 7.0 / avg_duration if avg_duration > 0 else 0
            throughput[assignee] = {
                "tasks_completed": len(durations),
                "avg_duration_days": avg_duration,
                "tasks_per_week": tasks_per_week,
            }
    
    return throughput


def compute_response_latency(plan_ids: list[str]) -> dict[str, Any]:
    """
    Compute response latency: Time from task creation to assignment (assignedDateTime - createdDateTime).
    Note: We don't have assignedDateTime in current schema, so we'll use startDateTime as proxy.
    """
    all_tasks = []
    for plan_id in plan_ids:
        tasks = get_planner_tasks(plan_id)
        all_tasks.extend(tasks)
    
    assignee_latency: dict[str, list[float]] = defaultdict(list)
    
    for task in all_tasks:
        assignees = task.get("assignees") or []
        created = _parse_datetime(task.get("createdDateTime"))
        start = _parse_datetime(task.get("startDateTime"))
        
        if not (created and start and assignees):
            continue
        
        latency_days = (start - created).total_seconds() / 86400
        
        for assignee in assignees:
            assignee_latency[assignee].append(latency_days)
    
    latency_stats = {}
    for assignee, latencies in assignee_latency.items():
        if latencies:
            latency_stats[assignee] = {
                "avg_latency_days": sum(latencies) / len(latencies),
                "median_latency_days": sorted(latencies)[len(latencies) // 2],
                "samples": len(latencies),
            }
    
    return latency_stats


def analyze_block_frequency(plan_ids: list[str]) -> dict[str, Any]:
    """
    Analyze blocked task frequency: Tasks stuck at 50% for > threshold.
    """
    all_tasks = []
    for plan_id in plan_ids:
        tasks = get_planner_tasks(plan_id)
        all_tasks.extend(tasks)
    
    blocked_tasks = []
    bucket_block_counts: dict[str, int] = defaultdict(int)
    bucket_total_counts: dict[str, int] = defaultdict(int)
    
    for task in all_tasks:
        bucket = task.get("bucketName") or "Unknown"
        bucket_total_counts[bucket] += 1
        
        percent_complete = task.get("percentComplete", 0)
        if percent_complete == 50:
            # Check if task is actually blocked (completed date far in future or None)
            completed = _parse_datetime(task.get("completedDateTime"))
            due = _parse_datetime(task.get("dueDateTime"))
            
            if not completed or (due and completed > due + timedelta(days=7)):
                blocked_tasks.append({
                    "task_id": task.get("id"),
                    "title": task.get("title"),
                    "bucket": bucket,
                })
                bucket_block_counts[bucket] += 1
    
    block_rates = {
        bucket: bucket_block_counts[bucket] / bucket_total_counts[bucket]
        if bucket_total_counts[bucket] > 0 else 0
        for bucket in bucket_total_counts
    }
    
    return {
        "total_blocked": len(blocked_tasks),
        "block_rate_by_bucket": block_rates,
        "blocked_tasks": blocked_tasks[:20],  # Top 20
    }


def analyze_phase_durations(plan_ids: list[str]) -> dict[str, Any]:
    """
    Analyze phase durations: Per bucket, compute actual vs planned durations.
    """
    all_tasks = []
    for plan_id in plan_ids:
        tasks = get_planner_tasks(plan_id)
        all_tasks.extend([(plan_id, t) for t in tasks])
    
    bucket_durations: dict[str, list[tuple[float, float]]] = defaultdict(list)  # bucket -> [(planned, actual), ...]
    
    for plan_id, task in all_tasks:
        bucket = task.get("bucketName") or "Unknown"
        start = _parse_datetime(task.get("startDateTime"))
        due = _parse_datetime(task.get("dueDateTime"))
        completed = _parse_datetime(task.get("completedDateTime"))
        
        if not (start and due):
            continue
        
        planned = (due - start).total_seconds() / 86400
        
        if completed:
            actual = (completed - start).total_seconds() / 86400
            bucket_durations[bucket].append((planned, actual))
    
    phase_stats = {}
    for bucket, durations in bucket_durations.items():
        if durations:
            planned_vals = [p for p, a in durations]
            actual_vals = [a for p, a in durations]
            phase_stats[bucket] = {
                "avg_planned_days": sum(planned_vals) / len(planned_vals),
                "avg_actual_days": sum(actual_vals) / len(actual_vals),
                "bias_factor": sum(actual_vals) / sum(planned_vals) if sum(planned_vals) > 0 else 1.0,
                "sample_count": len(durations),
            }
    
    return phase_stats


def get_historical_insights(current_plan_id: str, historical_plan_ids: list[str] | None = None) -> dict[str, Any]:
    """
    Get comprehensive historical insights for current plan.
    """
    if historical_plan_ids is None:
        # Default to congress-2022, congress-2023, congress-2024
        historical_plan_ids = ["congress-2022", "congress-2023", "congress-2024"]
    
    return {
        "duration_bias": analyze_duration_bias(historical_plan_ids),
        "implicit_dependencies": extract_implicit_dependencies(historical_plan_ids),
        "bottlenecks": identify_bottlenecks(historical_plan_ids)[:10],  # Top 10
        "resource_throughput": compute_resource_throughput(historical_plan_ids),
        "response_latency": compute_response_latency(historical_plan_ids),
        "block_frequency": analyze_block_frequency(historical_plan_ids),
        "phase_durations": analyze_phase_durations(historical_plan_ids),
    }
