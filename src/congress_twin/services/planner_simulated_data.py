"""
Simulated MS Planner data for Congress Twin (no Graph API).

Planning-related data: fixed date ranges, % complete, variance (2d/1d), critical path.
"""

from datetime import datetime, timezone
from typing import Any

DEFAULT_PLAN_ID = "uc31-plan"

ASSIGNEE_NAMES: dict[str, str] = {
    "user-1": "Alex",
    "user-2": "Jordan",
    "user-3": "Sam",
    "user-4": "Casey",
}


def get_simulated_buckets(plan_id: str = DEFAULT_PLAN_ID) -> list[dict[str, Any]]:
    """Simulated buckets (columns) for the plan."""
    return [
        {"id": f"{plan_id}-bucket-discovery", "name": "Discovery", "order_hint": " !"},
        {"id": f"{plan_id}-bucket-design", "name": "Design", "order_hint": "  !"},
        {"id": f"{plan_id}-bucket-build", "name": "Build", "order_hint": "   !"},
        {"id": f"{plan_id}-bucket-test", "name": "Test", "order_hint": "    !"},
        {"id": f"{plan_id}-bucket-deploy", "name": "Deploy", "order_hint": "     !"},
    ]


def get_simulated_tasks(plan_id: str = DEFAULT_PLAN_ID) -> list[dict[str, Any]]:
    """
    Planning-related tasks: fixed start/end dates (Feb 2026), % complete, variance.
    All on critical path for this plan.
    """
    buckets = get_simulated_buckets(plan_id)
    bucket_by_id = {b["id"]: b["name"] for b in buckets}
    b_discovery, b_design, b_build, b_test, b_deploy = (b["id"] for b in buckets)

    # Fixed dates 2026; startDateTime → dueDateTime; percentComplete; variance_days for Gantt
    tasks = [
        {"id": "task-001", "title": "Requirements document", "bucketId": b_discovery, "percentComplete": 92, "status": "inProgress", "startDateTime": "2026-01-30T00:00:00+00:00", "dueDateTime": "2026-02-04T00:00:00+00:00", "assignees": ["user-1"], "lastModifiedAt": "2026-02-04T12:00:00+00:00", "variance_days": 2},
        {"id": "task-002", "title": "API and data model design", "bucketId": b_design, "percentComplete": 89, "status": "inProgress", "startDateTime": "2026-02-04T00:00:00+00:00", "dueDateTime": "2026-02-09T00:00:00+00:00", "assignees": ["user-2"], "lastModifiedAt": "2026-02-06T08:06:00+00:00", "variance_days": 2},
        {"id": "task-003", "title": "Backend: Planner sync service", "bucketId": b_build, "percentComplete": 86, "status": "inProgress", "startDateTime": "2026-02-06T00:00:00+00:00", "dueDateTime": "2026-02-11T00:00:00+00:00", "assignees": ["user-3"], "lastModifiedAt": "2026-02-06T08:51:00+00:00", "variance_days": 2},
        {"id": "task-004", "title": "Frontend: Dependency Lens UI", "bucketId": b_build, "percentComplete": 78, "status": "inProgress", "startDateTime": "2026-02-08T00:00:00+00:00", "dueDateTime": "2026-02-12T00:00:00+00:00", "assignees": ["user-4"], "lastModifiedAt": "2026-02-08T14:00:00+00:00", "variance_days": 1},
        {"id": "task-005", "title": "Integration and API wiring", "bucketId": b_build, "percentComplete": 83, "status": "inProgress", "startDateTime": "2026-02-11T00:00:00+00:00", "dueDateTime": "2026-02-16T00:00:00+00:00", "assignees": ["user-3"], "lastModifiedAt": "2026-02-06T07:06:00+00:00", "variance_days": 2},
        {"id": "task-006", "title": "UAT and bug fixes", "bucketId": b_test, "percentComplete": 80, "status": "inProgress", "startDateTime": "2026-02-15T00:00:00+00:00", "dueDateTime": "2026-02-20T00:00:00+00:00", "assignees": ["user-4"], "lastModifiedAt": "2026-02-15T10:00:00+00:00", "variance_days": 2},
        {"id": "task-007", "title": "Go-live and handover", "bucketId": b_deploy, "percentComplete": 77, "status": "inProgress", "startDateTime": "2026-02-22T00:00:00+00:00", "dueDateTime": "2026-02-27T00:00:00+00:00", "assignees": ["user-1"], "lastModifiedAt": "2026-02-22T09:00:00+00:00", "variance_days": 2},
    ]

    for t in tasks:
        t["bucketName"] = bucket_by_id.get(t["bucketId"], "")
        t["assigneeNames"] = [ASSIGNEE_NAMES.get(a, a) for a in t.get("assignees", [])]
    return tasks


def get_simulated_dependencies(plan_id: str = DEFAULT_PLAN_ID) -> list[tuple[str, str]]:
    """(task_id, depends_on_task_id). Congress critical path + supporting/related task dependencies."""
    return [
        # Core congress path
        ("task-002", "task-001"),
        ("task-003", "task-002"),
        ("task-004", "task-003"),
        ("task-005", "task-003"),
        ("task-005", "task-004"),
        ("task-006", "task-005"),
        ("task-007", "task-006"),
        # Related components
        ("task-008", "task-002"),   # KOL invitations after speaker confirmations
        ("task-009", "task-001"),   # Budget after agenda outline
        ("task-010", "task-004"),   # AV & tech after registration platform
        ("task-011", "task-003"),   # Legal sign-off after venue contracts
        ("task-012", "task-003"),   # Catering after venue
        ("task-013", "task-007"),   # Post-event survey after handover
        ("task-014", "task-001"),   # Stakeholder alignment after agenda
        ("task-015", "task-002"),   # Marketing collateral after speaker confirmations
    ]
