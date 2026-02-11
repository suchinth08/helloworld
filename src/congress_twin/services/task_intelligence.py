"""
Task Intelligence Service: Generate AI-driven suggestions for task optimization.

Combines:
- Monte Carlo simulation for risk and timeline predictions
- Markov Chain analysis for state transition probabilities
- Historical analysis for pattern recognition
- Resource optimization for reassignment
- Dependency optimization for critical path
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any


def _utc_now() -> datetime:
    """Return current time in UTC (timezone-aware) for comparison with parsed datetimes."""
    return datetime.now(timezone.utc)


def _to_utc(dt: datetime | None) -> datetime | None:
    """Normalize datetime to UTC for comparison. Naive datetimes are assumed UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

from congress_twin.db.planner_repo import (
    get_planner_task_dependencies,
    get_planner_task_details,
)
from congress_twin.services.planner_service import get_tasks_for_plan
from congress_twin.services.historical_analyzer import (
    analyze_duration_bias,
    compute_resource_throughput,
    identify_bottlenecks,
)
from congress_twin.services.markov_chain_tracker import get_markov_analysis
from congress_twin.services.monte_carlo_simulator import run_simulation
from congress_twin.services.planner_service import get_critical_path
from congress_twin.services.planner_simulated_data import DEFAULT_PLAN_ID

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


def _compute_assignee_workload(plan_id: str, assignee: str, exclude_task_id: str | None = None) -> dict[str, Any]:
    """Compute current workload for an assignee."""
    tasks = get_tasks_for_plan(plan_id)
    assignee_tasks = [
        t for t in tasks
        if assignee in (t.get("assignees") or []) and t.get("id") != exclude_task_id
    ]
    
    active_tasks = [t for t in assignee_tasks if t.get("status") != "completed"]
    overdue_tasks = [
        t for t in active_tasks
        if _to_utc(_parse_datetime(t.get("dueDateTime"))) and _to_utc(_parse_datetime(t.get("dueDateTime"))) < _utc_now()
    ]
    
    return {
        "total_tasks": len(assignee_tasks),
        "active_tasks": len(active_tasks),
        "overdue_tasks": len(overdue_tasks),
        "utilization_score": len(active_tasks) / 5.0 if len(active_tasks) > 0 else 0.0,  # Normalize to 0-1
    }


def _find_optimal_assignees(
    plan_id: str,
    task: dict[str, Any],
    current_assignees: list[str],
    historical_plan_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Find optimal assignees based on workload, historical performance, and task type."""
    if historical_plan_ids is None:
        historical_plan_ids = ["congress-2022", "congress-2023", "congress-2024"]
    
    # Get all assignees from current plan
    tasks = get_tasks_for_plan(plan_id)
    all_assignees = set()
    for t in tasks:
        all_assignees.update(t.get("assignees") or [])
    
    # Get historical throughput
    try:
        throughput = compute_resource_throughput(historical_plan_ids)
        assignee_throughput = throughput.get("assignee_stats", {})
    except Exception:
        assignee_throughput = {}
    
    # Score each assignee
    recommendations = []
    bucket = task.get("bucketName") or task.get("bucketId", "")
    
    for assignee in all_assignees:
        workload = _compute_assignee_workload(plan_id, assignee, task.get("id"))
        
        # Historical performance for this bucket/task type
        hist_perf = assignee_throughput.get(assignee, {})
        bucket_perf = hist_perf.get("by_bucket", {}).get(bucket, {})
        avg_completion_rate = bucket_perf.get("avg_completion_rate", 0.5)
        
        # Score: lower workload + higher historical performance = better
        score = (1.0 - workload["utilization_score"]) * 0.4 + avg_completion_rate * 0.6
        
        recommendations.append({
            "assignee": assignee,
            "score": score,
            "workload": workload,
            "historical_completion_rate": avg_completion_rate,
            "reason": f"{assignee}: {workload['active_tasks']} active tasks, {avg_completion_rate:.0%} historical completion rate",
        })
    
    # Sort by score (highest first)
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    
    return recommendations[:5]  # Top 5 recommendations


def _analyze_dependency_risks(
    plan_id: str,
    task_id: str,
    monte_carlo_results: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Analyze dependency risks and suggest optimizations."""
    dependencies = get_planner_task_dependencies(plan_id, task_id)
    tasks = get_tasks_for_plan(plan_id)
    task_map = {t["id"]: t for t in tasks}
    
    risks = []
    
    for dep in dependencies:
        depends_on_id = dep.get("dependsOnTaskId")
        if not depends_on_id:
            continue
        
        depends_on_task = task_map.get(depends_on_id)
        if not depends_on_task:
            continue
        
        # Check if dependency is on critical path
        is_critical = False
        if monte_carlo_results:
            critical_path_tasks = monte_carlo_results.get("critical_path_probability", {})
            is_critical = critical_path_tasks.get(depends_on_id, 0) > 0.5
        
        # Check if dependency is delayed
        due_date = _parse_datetime(depends_on_task.get("dueDateTime"))
        completed = _parse_datetime(depends_on_task.get("completedDateTime"))
        is_delayed = False
        delay_days = 0
        
        if due_date and not completed:
            due_utc = _to_utc(due_date)
            now = _utc_now()
            if due_utc and now > due_utc:
                is_delayed = True
                delay_days = (now - due_utc).days
        elif due_date and completed:
            if completed > due_date:
                is_delayed = True
                delay_days = (completed - due_date).days
        
        # Check dependency status
        dep_status = depends_on_task.get("status", "notStarted")
        is_blocked = dep_status != "completed" and is_delayed
        
        risk_level = "low"
        if is_blocked:
            risk_level = "high"
        elif is_delayed or dep_status != "completed":
            risk_level = "medium"
        
        risks.append({
            "dependency_task_id": depends_on_id,
            "dependency_task_title": depends_on_task.get("title", ""),
            "dependency_type": dep.get("dependencyType", "FS"),
            "risk_level": risk_level,
            "is_critical": is_critical,
            "is_delayed": is_delayed,
            "delay_days": delay_days,
            "dependency_status": dep_status,
            "suggestion": _generate_dependency_suggestion(depends_on_task, is_blocked, is_delayed, delay_days),
        })
    
    return risks


def _generate_dependency_suggestion(
    depends_on_task: dict[str, Any],
    is_blocked: bool,
    is_delayed: bool,
    delay_days: int,
) -> str:
    """Generate human-readable suggestion for dependency issue."""
    if is_blocked:
        return f"⚠️ Dependency '{depends_on_task.get('title', '')}' is blocked and delayed by {delay_days} days. Consider parallel work or expediting."
    elif is_delayed:
        return f"⚠️ Dependency '{depends_on_task.get('title', '')}' is delayed by {delay_days} days. Monitor closely."
    elif depends_on_task.get("status") != "completed":
        return f"ℹ️ Waiting on dependency '{depends_on_task.get('title', '')}'. Ensure it stays on track."
    return "✓ Dependency is on track."


def _generate_timeline_suggestions(
    task: dict[str, Any],
    monte_carlo_results: dict[str, Any] | None = None,
    markov_analysis: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Generate timeline optimization suggestions."""
    suggestions = []
    
    start_date = _parse_datetime(task.get("startDateTime"))
    due_date = _parse_datetime(task.get("dueDateTime"))
    completed_date = _parse_datetime(task.get("completedDateTime"))
    percent_complete = task.get("percentComplete", 0)
    
    if not start_date or not due_date:
        return suggestions
    
    planned_duration = (due_date - start_date).total_seconds() / 86400  # days
    
    # Monte Carlo predictions
    if monte_carlo_results:
        task_id = task.get("id")
        percentiles = monte_carlo_results.get("percentiles", {})
        p50_str = percentiles.get("p50")
        p95_str = percentiles.get("p95")
        
        if p50_str:
            try:
                p50 = _parse_datetime(p50_str)
                if p50 and p50 > due_date:
                    delay_days = (p50 - due_date).days
                    suggestions.append({
                        "type": "timeline_risk",
                        "severity": "high" if delay_days > 7 else "medium",
                        "title": f"Predicted delay: {delay_days} days",
                        "description": f"Monte Carlo simulation predicts 50% chance of finishing {delay_days} days late.",
                        "action": f"Consider extending deadline by {delay_days} days or adding resources.",
                    })
            except Exception:
                pass
    
    # Markov Chain expected completion
    if markov_analysis:
        expected_completion = markov_analysis.get("expected_completion_days")
        if expected_completion and expected_completion > planned_duration:
            delay = expected_completion - planned_duration
            suggestions.append({
                "type": "markov_prediction",
                "severity": "medium",
                "title": f"State-based prediction: {delay:.1f} days over",
                "description": f"Markov Chain analysis suggests completion in {expected_completion:.1f} days vs planned {planned_duration:.1f} days.",
                "action": "Review task breakdown or add buffer time.",
            })
    
    # Current progress analysis
    if not completed_date and percent_complete > 0:
        now = _utc_now()
        start_utc = _to_utc(start_date)
        elapsed = (now - start_utc).total_seconds() / 86400 if start_utc else 0
        expected_elapsed = planned_duration * (percent_complete / 100)
        
        if elapsed > expected_elapsed * 1.2:  # More than 20% behind
            behind_days = elapsed - expected_elapsed
            suggestions.append({
                "type": "progress_tracking",
                "severity": "high",
                "title": f"Behind schedule: {behind_days:.1f} days",
                "description": f"Task is {behind_days:.1f} days behind expected progress.",
                "action": "Accelerate work or adjust timeline expectations.",
            })
    
    return suggestions


def _generate_resource_suggestions(
    plan_id: str,
    task: dict[str, Any],
    historical_plan_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Generate resource optimization suggestions."""
    suggestions = []
    current_assignees = task.get("assignees") or []
    
    # Check current assignee workload
    for assignee in current_assignees:
        workload = _compute_assignee_workload(plan_id, assignee, task.get("id"))
        
        if workload["utilization_score"] > 0.8:  # Over 80% utilization
            suggestions.append({
                "type": "resource_overload",
                "severity": "high",
                "title": f"{assignee} is overloaded",
                "description": f"{assignee} has {workload['active_tasks']} active tasks ({workload['overdue_tasks']} overdue).",
                "action": "Consider reassigning some tasks to balance workload.",
            })
    
    # Get optimal assignee recommendations
    optimal_assignees = _find_optimal_assignees(plan_id, task, current_assignees, historical_plan_ids)
    
    if optimal_assignees:
        top_recommendation = optimal_assignees[0]
        if top_recommendation["assignee"] not in current_assignees:
            suggestions.append({
                "type": "reassignment",
                "severity": "low",
                "title": "Consider reassignment",
                "description": f"'{top_recommendation['assignee']}' has lower workload and better historical performance.",
                "action": f"Reassign to {top_recommendation['assignee']} for better balance.",
                "recommended_assignee": top_recommendation["assignee"],
                "recommendation_score": top_recommendation["score"],
            })
    
    return suggestions


def _generate_critical_path_suggestions(
    plan_id: str,
    task_id: str,
    monte_carlo_results: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Generate critical path optimization suggestions."""
    suggestions = []
    
    # Check if task is on critical path
    try:
        critical_path = get_critical_path(plan_id)
        critical_tasks = critical_path.get("critical_path_tasks", [])
        is_critical = any(t.get("id") == task_id for t in critical_tasks)
    except Exception:
        is_critical = False
    
    if monte_carlo_results:
        critical_path_prob = monte_carlo_results.get("critical_path_probability", {})
        task_prob = critical_path_prob.get(task_id, 0)
        is_critical = is_critical or task_prob > 0.5
    
    if is_critical:
        suggestions.append({
            "type": "critical_path",
            "severity": "high",
            "title": "On critical path",
            "description": "This task is on the critical path. Delays will impact overall timeline.",
            "action": "Prioritize this task and ensure adequate resources.",
        })
    
    return suggestions


def get_task_intelligence(
    plan_id: str,
    task_id: str,
    include_simulations: bool = True,
) -> dict[str, Any]:
    """
    Generate comprehensive intelligence and suggestions for a task.
    
    Returns:
        - Dependency risks and optimizations
        - Reassignment recommendations
        - Timeline suggestions (Monte Carlo, Markov Chain)
        - Resource optimization
        - Critical path alerts
        - Overall risk score
    """
    # Use get_tasks_for_plan so simulated tasks (e.g. default plan seed) are included
    tasks = get_tasks_for_plan(plan_id)
    task = next((t for t in tasks if t.get("id") == task_id), None)
    
    if not task:
        return {"error": "Task not found"}
    
    # Run simulations in background (cached if already run)
    monte_carlo_results = None
    markov_analysis = None
    
    if include_simulations:
        try:
            # Run Monte Carlo (use smaller iterations for performance)
            monte_carlo_results = run_simulation(plan_id, n_iterations=1000)
        except Exception as e:
            logger.warning(f"Monte Carlo simulation failed: {e}")
        
        try:
            # Get Markov Chain analysis
            markov_analysis = get_markov_analysis(plan_id, task_id=task_id)
        except Exception as e:
            logger.warning(f"Markov Chain analysis failed: {e}")
    
    # Generate all suggestions
    dependency_risks = _analyze_dependency_risks(plan_id, task_id, monte_carlo_results)
    timeline_suggestions = _generate_timeline_suggestions(task, monte_carlo_results, markov_analysis)
    resource_suggestions = _generate_resource_suggestions(plan_id, task)
    critical_path_suggestions = _generate_critical_path_suggestions(plan_id, task_id, monte_carlo_results)
    
    # Get optimal assignees
    optimal_assignees = _find_optimal_assignees(plan_id, task, task.get("assignees") or [])
    
    # Compute overall risk score (0-100)
    risk_score = 0
    risk_factors = []
    
    if dependency_risks:
        high_risks = sum(1 for r in dependency_risks if r["risk_level"] == "high")
        if high_risks > 0:
            risk_score += 30
            risk_factors.append(f"{high_risks} high-risk dependencies")
    
    if timeline_suggestions:
        high_severity = sum(1 for s in timeline_suggestions if s["severity"] == "high")
        if high_severity > 0:
            risk_score += 25
            risk_factors.append(f"{high_severity} timeline risks")
    
    if resource_suggestions:
        overloaded = sum(1 for s in resource_suggestions if s["type"] == "resource_overload")
        if overloaded > 0:
            risk_score += 20
            risk_factors.append(f"{overloaded} overloaded assignees")
    
    if critical_path_suggestions:
        risk_score += 15
        risk_factors.append("On critical path")
    
    # Check if task is overdue
    due_date = _parse_datetime(task.get("dueDateTime"))
    due_utc = _to_utc(due_date)
    if due_utc and _utc_now() > due_utc and task.get("status") != "completed":
        risk_score += 10
        risk_factors.append("Overdue")
    
    return {
        "task_id": task_id,
        "plan_id": plan_id,
        "risk_score": min(100, risk_score),
        "risk_factors": risk_factors,
        "dependency_risks": dependency_risks,
        "timeline_suggestions": timeline_suggestions,
        "resource_suggestions": resource_suggestions,
        "critical_path_suggestions": critical_path_suggestions,
        "optimal_assignees": optimal_assignees,
        "monte_carlo_summary": {
            "p50_completion": monte_carlo_results.get("percentiles", {}).get("p50") if monte_carlo_results else None,
            "p95_completion": monte_carlo_results.get("percentiles", {}).get("p95") if monte_carlo_results else None,
            "critical_path_probability": monte_carlo_results.get("critical_path_probability", {}).get(task_id, 0) if monte_carlo_results else 0,
        } if monte_carlo_results else None,
        "markov_summary": {
            "current_state": markov_analysis.get("current_state") if markov_analysis else None,
            "expected_completion_days": markov_analysis.get("expected_completion", {}).get("expected_completion_days") if markov_analysis and isinstance(markov_analysis.get("expected_completion"), dict) else None,
            "transition_probabilities": markov_analysis.get("transition_matrix", {}) if markov_analysis else {},
        } if markov_analysis else None,
    }
