"""
Historical Data Generator: Generate 3+ years of simulated congress plans with realistic distributions.

Generates:
- Plan IDs: congress-2022, congress-2023, congress-2024
- Each plan: 50-100 tasks across 5-7 buckets
- Realistic duration distributions, completion patterns, state transitions, dependencies
"""

import json
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from congress_twin.db.planner_repo import (
    ensure_planner_tasks_table,
    upsert_planner_tasks,
    upsert_planner_task_details,
    upsert_planner_task_dependencies,
)

# Set seed for reproducibility
random.seed(42)

# Realistic bucket names for congress planning
CONGRESS_BUCKETS = [
    "Venue & Logistics",
    "Speaker Management",
    "Content & Agenda",
    "Travel & Accommodation",
    "Registration",
    "Marketing & Communications",
    "Exhibitor Management",
]

# Simulated assignees with varying throughput
ASSIGNEES = [
    {"id": "user-alex", "name": "Alex", "throughput": 0.8, "specialization": ["Venue & Logistics", "Travel & Accommodation"]},
    {"id": "user-jordan", "name": "Jordan", "throughput": 1.0, "specialization": ["Speaker Management", "Content & Agenda"]},
    {"id": "user-sam", "name": "Sam", "throughput": 0.9, "specialization": ["Registration", "Marketing & Communications"]},
    {"id": "user-casey", "name": "Casey", "throughput": 0.7, "specialization": ["Exhibitor Management"]},
    {"id": "user-taylor", "name": "Taylor", "throughput": 1.1, "specialization": ["Content & Agenda", "Marketing & Communications"]},
    {"id": "user-morgan", "name": "Morgan", "throughput": 0.85, "specialization": ["Speaker Management"]},
    {"id": "user-river", "name": "River", "throughput": 0.95, "specialization": ["Venue & Logistics"]},
]

# Task templates by bucket (with base duration in days)
TASK_TEMPLATES = {
    "Venue & Logistics": [
        {"title": "Book main venue", "base_duration": 14, "priority": 3, "categories": ["External Dependency", "High Risk"]},
        {"title": "Secure AV equipment", "base_duration": 10, "priority": 5, "categories": ["External Dependency"]},
        {"title": "Arrange catering", "base_duration": 7, "priority": 5, "categories": []},
        {"title": "Set up registration area", "base_duration": 3, "priority": 5, "categories": []},
        {"title": "Coordinate with venue security", "base_duration": 5, "priority": 3, "categories": ["External Dependency"]},
    ],
    "Speaker Management": [
        {"title": "Invite keynote speaker", "base_duration": 21, "priority": 1, "categories": ["VIP Speaker", "High Risk"]},
        {"title": "Confirm speaker availability", "base_duration": 14, "priority": 3, "categories": ["External Dependency"]},
        {"title": "Collect speaker bios", "base_duration": 7, "priority": 5, "categories": []},
        {"title": "Prepare speaker materials", "base_duration": 10, "priority": 3, "categories": []},
        {"title": "Coordinate speaker travel", "base_duration": 12, "priority": 3, "categories": ["External Dependency", "High Risk"]},
    ],
    "Content & Agenda": [
        {"title": "Draft conference agenda", "base_duration": 14, "priority": 3, "categories": []},
        {"title": "Design session tracks", "base_duration": 10, "priority": 5, "categories": []},
        {"title": "Create presentation templates", "base_duration": 5, "priority": 5, "categories": []},
        {"title": "Review and approve content", "base_duration": 7, "priority": 3, "categories": []},
    ],
    "Travel & Accommodation": [
        {"title": "Book hotel blocks", "base_duration": 21, "priority": 3, "categories": ["External Dependency"]},
        {"title": "Arrange airport transfers", "base_duration": 10, "priority": 5, "categories": ["External Dependency"]},
        {"title": "Process visa applications", "base_duration": 30, "priority": 1, "categories": ["High Risk", "External Dependency"]},
        {"title": "Coordinate group flights", "base_duration": 14, "priority": 3, "categories": ["External Dependency", "High Risk"]},
    ],
    "Registration": [
        {"title": "Set up registration system", "base_duration": 14, "priority": 3, "categories": []},
        {"title": "Create registration forms", "base_duration": 7, "priority": 5, "categories": []},
        {"title": "Process early registrations", "base_duration": 5, "priority": 5, "categories": []},
        {"title": "Send confirmation emails", "base_duration": 3, "priority": 5, "categories": []},
    ],
    "Marketing & Communications": [
        {"title": "Design marketing materials", "base_duration": 14, "priority": 5, "categories": []},
        {"title": "Launch social media campaign", "base_duration": 7, "priority": 5, "categories": []},
        {"title": "Send save-the-date emails", "base_duration": 3, "priority": 5, "categories": []},
    ],
    "Exhibitor Management": [
        {"title": "Recruit exhibitors", "base_duration": 21, "priority": 5, "categories": ["External Dependency"]},
        {"title": "Assign booth spaces", "base_duration": 7, "priority": 5, "categories": []},
        {"title": "Coordinate exhibitor logistics", "base_duration": 10, "priority": 5, "categories": ["External Dependency"]},
    ],
}


def _sample_beta_duration(base_duration: int, alpha: float = 2.0, beta: float = 2.0) -> float:
    """Sample duration from Beta distribution (PERT-like)."""
    import numpy as np
    try:
        # Beta distribution scaled to realistic range
        sample = np.random.beta(alpha, beta)
        # Scale to base_duration ± 50%
        min_dur = base_duration * 0.5
        max_dur = base_duration * 1.5
        return min_dur + sample * (max_dur - min_dur)
    except ImportError:
        # Fallback to uniform if numpy not available
        return base_duration * random.uniform(0.7, 1.3)


def _sample_log_normal_delay() -> float:
    """Sample delay from log-normal distribution (for delayed tasks)."""
    try:
        import numpy as np
        return max(0, np.random.lognormal(mean=2.0, sigma=1.0))
    except ImportError:
        # Fallback: exponential delay
        return max(0, random.expovariate(0.1))


def _generate_checklist_items(task_title: str, num_items: int = None) -> list[dict[str, Any]]:
    """Generate realistic checklist items for a task."""
    if num_items is None:
        num_items = random.randint(3, 8)
    
    checklist_templates = {
        "Book": ["Research options", "Compare prices", "Negotiate contract", "Sign agreement", "Confirm booking"],
        "Invite": ["Draft invitation", "Send invitation", "Follow up", "Receive confirmation", "Add to agenda"],
        "Design": ["Create draft", "Review internally", "Get approval", "Finalize", "Distribute"],
        "Coordinate": ["Contact stakeholders", "Schedule meeting", "Agree on plan", "Execute", "Confirm completion"],
    }
    
    items = []
    base_templates = []
    for key, templates in checklist_templates.items():
        if key.lower() in task_title.lower():
            base_templates = templates
            break
    
    if not base_templates:
        base_templates = ["Research", "Plan", "Execute", "Review", "Complete"]
    
    for i in range(num_items):
        if i < len(base_templates):
            title = base_templates[i]
        else:
            title = f"Step {i+1}"
        items.append({
            "id": f"checklist-{i}",
            "title": title,
            "isChecked": random.random() > 0.3,  # 70% checked on average
            "orderHint": f" !{' ' * i}",
        })
    
    return items


def generate_historical_plan(plan_id: str, congress_date: datetime, year: int) -> dict[str, Any]:
    """
    Generate a complete historical congress plan.
    
    Args:
        plan_id: Plan ID (e.g., "congress-2022")
        congress_date: Target congress date
        year: Year for reference
    
    Returns:
        dict with tasks_created, details_created, dependencies_created
    """
    ensure_planner_tasks_table()
    
    # Planning starts 6 months before congress
    planning_start = congress_date - timedelta(days=180)
    
    # Select 5-7 buckets for this plan
    num_buckets = random.randint(5, 7)
    selected_buckets = random.sample(CONGRESS_BUCKETS, num_buckets)
    
    # Generate bucket IDs
    bucket_name_to_id = {}
    for bucket_name in selected_buckets:
        bucket_id = f"{plan_id}-bucket-{bucket_name.lower().replace(' ', '-').replace('&', 'and')}"
        bucket_name_to_id[bucket_name] = bucket_id
    
    tasks = []
    task_details_map: dict[str, dict[str, Any]] = {}
    task_dependencies_map: dict[str, list[dict[str, str]]] = {}
    task_id_counter = 1
    
    # Generate tasks for each bucket
    for bucket_name in selected_buckets:
        templates = TASK_TEMPLATES.get(bucket_name, [])
        if not templates:
            continue
        
        # Generate 5-15 tasks per bucket
        num_tasks = random.randint(5, 15)
        selected_templates = random.choices(templates, k=num_tasks)
        
        for template in selected_templates:
            task_id = f"{plan_id}-task-{task_id_counter:03d}"
            task_id_counter += 1
            
            # Base duration with variance
            base_duration = template["base_duration"]
            planned_duration = _sample_beta_duration(base_duration)
            
            # 20% of tasks get delayed
            is_delayed = random.random() < 0.2
            if is_delayed:
                delay = _sample_log_normal_delay()
                actual_duration = planned_duration + delay
            else:
                actual_duration = planned_duration * random.uniform(0.9, 1.1)
            
            # Generate dates
            # Start date: random within planning window (earlier tasks start sooner)
            days_from_start = random.randint(0, 120)
            start_date = planning_start + timedelta(days=days_from_start)
            due_date = start_date + timedelta(days=int(planned_duration))
            completed_date = start_date + timedelta(days=int(actual_duration))
            created_date = start_date - timedelta(days=random.randint(1, 7))
            
            # Assign to random assignee (prefer specialized ones)
            assignee = random.choice(ASSIGNEES)
            if bucket_name in assignee["specialization"]:
                # Higher chance for specialized assignee
                if random.random() < 0.7:
                    assignee = assignee
                else:
                    assignee = random.choice(ASSIGNEES)
            
            # Generate state transitions
            # Not Started -> Planning -> In Progress -> Completed
            # Some tasks get blocked (stuck at 50%)
            is_blocked = random.random() < 0.15
            if is_blocked:
                percent_complete = 50
                status = "inProgress"
            elif completed_date <= congress_date:
                percent_complete = 100
                status = "completed"
            elif start_date <= congress_date:
                percent_complete = 50
                status = "inProgress"
            else:
                percent_complete = 0
                status = "notStarted"
            
            # Generate checklist
            checklist_items = _generate_checklist_items(template["title"])
            if checklist_items:
                task_details_map[task_id] = {
                    "checklist": checklist_items,
                    "references": [],
                    "lastModifiedAt": completed_date.isoformat() + "Z" if completed_date else None,
                }
            
            task = {
                "id": task_id,
                "title": template["title"],
                "bucketId": bucket_name_to_id[bucket_name],
                "bucketName": bucket_name,
                "status": status,
                "percentComplete": percent_complete,
                "startDateTime": start_date.isoformat() + "Z",
                "dueDateTime": due_date.isoformat() + "Z",
                "completedDateTime": completed_date.isoformat() + "Z" if completed_date <= congress_date else None,
                "createdDateTime": created_date.isoformat() + "Z",
                "priority": template["priority"],
                "assignees": [assignee["id"]],
                "assigneeNames": [assignee["name"]],
                "appliedCategories": template["categories"],
                "description": f"Historical task from {year} congress planning",
                "createdBy": assignee["id"],
                "completedBy": assignee["id"] if status == "completed" else None,
                "lastModifiedAt": completed_date.isoformat() + "Z" if completed_date <= congress_date else start_date.isoformat() + "Z",
            }
            tasks.append(task)
    
    # Generate dependencies (30% of tasks have dependencies)
    task_ids = [t["id"] for t in tasks]
    num_dependencies = int(len(tasks) * 0.3)
    for _ in range(num_dependencies):
        task_id = random.choice(task_ids)
        # Find a task that starts before this one
        task_start = next((t["startDateTime"] for t in tasks if t["id"] == task_id), None)
        if task_start:
            potential_deps = [
                t["id"] for t in tasks
                if t["id"] != task_id and t["dueDateTime"] and t["dueDateTime"] < task_start
            ]
            if potential_deps:
                dep_task_id = random.choice(potential_deps)
                if task_id not in task_dependencies_map:
                    task_dependencies_map[task_id] = []
                task_dependencies_map[task_id].append({
                    "dependsOnTaskId": dep_task_id,
                    "dependencyType": "FS",
                })
    
    # Upsert to database
    tasks_created = upsert_planner_tasks(plan_id, tasks)
    
    details_created = 0
    for task_id, details in task_details_map.items():
        upsert_planner_task_details(plan_id, task_id, details)
        details_created += 1
    
    dependencies_created = 0
    for task_id, deps in task_dependencies_map.items():
        upsert_planner_task_dependencies(plan_id, task_id, deps)
        dependencies_created += len(deps)
    
    return {
        "plan_id": plan_id,
        "tasks_created": tasks_created,
        "details_created": details_created,
        "dependencies_created": dependencies_created,
        "bucket_mapping": bucket_name_to_id,
    }


def generate_all_historical_plans() -> dict[str, Any]:
    """Generate historical plans for 2022, 2023, 2024."""
    results = {}
    
    # Generate plans for past 3 years
    current_year = datetime.now(timezone.utc).year
    for year_offset in range(3, 0, -1):  # 2022, 2023, 2024
        year = current_year - year_offset
        plan_id = f"congress-{year}"
        # Assume congress happens in Q2 (April-June)
        congress_date = datetime(year, random.randint(4, 6), random.randint(15, 25), tzinfo=timezone.utc)
        results[plan_id] = generate_historical_plan(plan_id, congress_date, year)
    
    return results
