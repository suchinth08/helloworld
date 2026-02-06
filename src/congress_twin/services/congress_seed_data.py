"""
Novartis Congress event scheduling data for DB seed and simulated fallback.

Task IDs task-001 … task-015; dependencies in get_simulated_dependencies().
Mix of Not Started, In Progress, and Completed plus related components.
Dates are for a previous-year congress event (2025). Optional relative dates
so "Due next 7 days", "Critical path due next", and "Recently changed" have data.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from congress_twin.services.planner_simulated_data import (
    ASSIGNEE_NAMES,
    DEFAULT_PLAN_ID,
    get_simulated_buckets,
)


def get_congress_seed_tasks(
    plan_id: str = DEFAULT_PLAN_ID,
    use_relative_dates_for_attention: bool = False,
) -> list[dict[str, Any]]:
    """
    Novartis congress event scheduling tasks: core path + related components.
    Mix of notStarted, inProgress, completed for realistic dashboard and Dependency Lens.
    """
    buckets = get_simulated_buckets(plan_id)
    bucket_by_id = {b["id"]: b["name"] for b in buckets}
    b_discovery, b_design, b_build, b_test, b_deploy = (b["id"] for b in buckets)

    tasks = [
        # --- Completed ---
        {
            "id": "task-001",
            "title": "Agenda & content outline",
            "bucketId": b_discovery,
            "percentComplete": 100,
            "status": "completed",
            "startDateTime": "2025-01-30T00:00:00+00:00",
            "dueDateTime": "2025-02-04T00:00:00+00:00",
            "assignees": ["user-1"],
            "lastModifiedAt": "2025-02-04T14:00:00+00:00",
        },
        {
            "id": "task-002",
            "title": "Speaker confirmations & abstract deadlines",
            "bucketId": b_design,
            "percentComplete": 100,
            "status": "completed",
            "startDateTime": "2025-02-04T00:00:00+00:00",
            "dueDateTime": "2025-02-09T00:00:00+00:00",
            "assignees": ["user-2"],
            "lastModifiedAt": "2025-02-09T10:00:00+00:00",
        },
        {
            "id": "task-009",
            "title": "Budget approval",
            "bucketId": b_discovery,
            "percentComplete": 100,
            "status": "completed",
            "startDateTime": "2025-01-28T00:00:00+00:00",
            "dueDateTime": "2025-02-02T00:00:00+00:00",
            "assignees": ["user-1"],
            "lastModifiedAt": "2025-02-01T16:00:00+00:00",
        },
        {
            "id": "task-011",
            "title": "Legal & compliance sign-off",
            "bucketId": b_build,
            "percentComplete": 100,
            "status": "completed",
            "startDateTime": "2025-02-10T00:00:00+00:00",
            "dueDateTime": "2025-02-14T00:00:00+00:00",
            "assignees": ["user-3"],
            "lastModifiedAt": "2025-02-14T11:00:00+00:00",
        },
        {
            "id": "task-014",
            "title": "Stakeholder alignment meeting",
            "bucketId": b_discovery,
            "percentComplete": 100,
            "status": "completed",
            "startDateTime": "2025-01-25T00:00:00+00:00",
            "dueDateTime": "2025-01-30T00:00:00+00:00",
            "assignees": ["user-1", "user-2"],
            "lastModifiedAt": "2025-01-30T17:00:00+00:00",
        },
        # --- In progress ---
        {
            "id": "task-003",
            "title": "Venue & vendor contracts",
            "bucketId": b_build,
            "percentComplete": 86,
            "status": "inProgress",
            "startDateTime": "2025-02-06T00:00:00+00:00",
            "dueDateTime": "2025-02-11T00:00:00+00:00",
            "assignees": ["user-3"],
            "lastModifiedAt": "2025-02-06T08:51:00+00:00",
        },
        {
            "id": "task-004",
            "title": "Registration platform setup",
            "bucketId": b_build,
            "percentComplete": 78,
            "status": "inProgress",
            "startDateTime": "2025-02-08T00:00:00+00:00",
            "dueDateTime": "2025-02-12T00:00:00+00:00",
            "assignees": ["user-4"],
            "lastModifiedAt": "2025-02-08T14:00:00+00:00",
        },
        {
            "id": "task-005",
            "title": "Abstract submission & review workflow",
            "bucketId": b_build,
            "percentComplete": 83,
            "status": "inProgress",
            "startDateTime": "2025-02-11T00:00:00+00:00",
            "dueDateTime": "2025-02-16T00:00:00+00:00",
            "assignees": ["user-3"],
            "lastModifiedAt": "2025-02-06T07:06:00+00:00",
        },
        {
            "id": "task-006",
            "title": "Day-of logistics & runbook",
            "bucketId": b_test,
            "percentComplete": 80,
            "status": "inProgress",
            "startDateTime": "2025-02-15T00:00:00+00:00",
            "dueDateTime": "2025-02-20T00:00:00+00:00",
            "assignees": ["user-4"],
            "lastModifiedAt": "2025-02-15T10:00:00+00:00",
        },
        {
            "id": "task-007",
            "title": "Post-congress reporting & handover",
            "bucketId": b_deploy,
            "percentComplete": 77,
            "status": "inProgress",
            "startDateTime": "2025-02-22T00:00:00+00:00",
            "dueDateTime": "2025-02-27T00:00:00+00:00",
            "assignees": ["user-1"],
            "lastModifiedAt": "2025-02-22T09:00:00+00:00",
        },
        {
            "id": "task-012",
            "title": "Catering & F&B",
            "bucketId": b_build,
            "percentComplete": 60,
            "status": "inProgress",
            "startDateTime": "2025-02-12T00:00:00+00:00",
            "dueDateTime": "2025-02-18T00:00:00+00:00",
            "assignees": ["user-4"],
            "lastModifiedAt": "2025-02-14T09:00:00+00:00",
        },
        {
            "id": "task-015",
            "title": "Marketing collateral",
            "bucketId": b_design,
            "percentComplete": 45,
            "status": "inProgress",
            "startDateTime": "2025-02-10T00:00:00+00:00",
            "dueDateTime": "2025-02-18T00:00:00+00:00",
            "assignees": ["user-2"],
            "lastModifiedAt": "2025-02-12T14:00:00+00:00",
        },
        # --- Not started ---
        {
            "id": "task-008",
            "title": "KOL invitations & tracking",
            "bucketId": b_design,
            "percentComplete": 0,
            "status": "notStarted",
            "startDateTime": "2025-02-10T00:00:00+00:00",
            "dueDateTime": "2025-02-16T00:00:00+00:00",
            "assignees": ["user-2"],
            "lastModifiedAt": "2025-02-01T00:00:00+00:00",
        },
        {
            "id": "task-010",
            "title": "AV & tech checklist",
            "bucketId": b_build,
            "percentComplete": 0,
            "status": "notStarted",
            "startDateTime": "2025-02-14T00:00:00+00:00",
            "dueDateTime": "2025-02-20T00:00:00+00:00",
            "assignees": ["user-3"],
            "lastModifiedAt": "2025-02-01T00:00:00+00:00",
        },
        {
            "id": "task-013",
            "title": "Post-event survey design",
            "bucketId": b_deploy,
            "percentComplete": 0,
            "status": "notStarted",
            "startDateTime": "2025-02-28T00:00:00+00:00",
            "dueDateTime": "2025-03-05T00:00:00+00:00",
            "assignees": ["user-1"],
            "lastModifiedAt": "2025-02-01T00:00:00+00:00",
        },
    ]

    for t in tasks:
        t["bucketName"] = bucket_by_id.get(t["bucketId"], "")
        t["assigneeNames"] = [ASSIGNEE_NAMES.get(a, a) for a in t.get("assignees", [])]

    if use_relative_dates_for_attention:
        _apply_relative_dates_for_attention(tasks)
    return tasks


def _apply_relative_dates_for_attention(tasks: list[dict[str, Any]]) -> None:
    """
    Override due/start/lastModified for a subset of tasks so the attention dashboard shows:
    - Due next 7 days (task-004, 005, 006, 007)
    - Critical path due next (task-006, 007)
    - Recently changed (task-004, 005, 006, 007)
    """
    now = datetime.now(timezone.utc)

    def iso(dt: datetime) -> str:
        s = dt.isoformat()
        return s if "+" in s or s.endswith("Z") else f"{s}Z"

    # Map task_id -> (due_offset_days, start_offset_days, last_mod_offset_hours)
    overrides: dict[str, tuple[int, int, float]] = {
        "task-004": (2, -2, 1),   # due in 2d, recently changed
        "task-005": (4, 0, 2),
        "task-006": (5, 2, 1),    # critical path, due in 5d
        "task-007": (6, 4, 0.5),  # critical path, due in 6d
    }
    for t in tasks:
        tid = t.get("id")
        if tid not in overrides:
            continue
        due_d, start_d, mod_h = overrides[tid]
        t["dueDateTime"] = iso(now + timedelta(days=due_d))
        t["startDateTime"] = iso(now + timedelta(days=start_d))
        t["lastModifiedAt"] = iso(now - timedelta(hours=mod_h))
