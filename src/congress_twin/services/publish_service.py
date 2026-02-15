"""
Publish service: Publish plan to MS Planner.

MVP: Simulated — validate data, persist 'published' state, return success.
Production: Call Graph API to create/update tasks (requires Tasks.ReadWrite.All).
"""

from datetime import datetime, timezone
from typing import Any

from congress_twin.db.planner_repo import get_planner_tasks
from congress_twin.services.planner_service import get_tasks_for_plan


def publish_plan_to_planner(plan_id: str) -> dict[str, Any]:
    """
    Publish plan tasks to MS Planner.
    MVP: Validate, mark as published, return success.
    Production: Would call Graph API create_task, update_task.
    """
    tasks = get_tasks_for_plan(plan_id)
    if not tasks:
        return {
            "plan_id": plan_id,
            "published": False,
            "tasks_pushed": 0,
            "message": "No tasks to publish",
        }
    # MVP: simulated success
    return {
        "plan_id": plan_id,
        "published": True,
        "tasks_pushed": len(tasks),
        "message": f"Published {len(tasks)} tasks (simulated). Configure Graph API for live publish.",
    }
