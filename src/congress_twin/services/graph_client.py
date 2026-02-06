"""
MS Graph API client for Planner (Phase 1).

When GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, GRAPH_TENANT_ID are set,
get_token() obtains an access token for Microsoft Graph and
fetch_plan_tasks_from_graph() returns tasks from the Planner plan.
"""

import logging
from typing import Any, Optional

import requests

from congress_twin.config import get_settings

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def is_graph_configured() -> bool:
    """True if Graph API credentials are set."""
    s = get_settings()
    return bool(s.graph_client_id and s.graph_client_secret and s.graph_tenant_id)


def get_token() -> Optional[str]:
    """
    Get OAuth2 access token for Microsoft Graph (client credentials flow).
    Returns None if Graph is not configured or token request fails.
    """
    if not is_graph_configured():
        return None
    try:
        import msal
    except ImportError:
        logger.warning("msal not installed; run pip install msal")
        return None
    s = get_settings()
    authority = f"https://login.microsoftonline.com/{s.graph_tenant_id}"
    app = msal.ConfidentialClientApplication(
        s.graph_client_id,
        authority=authority,
        client_credential=s.graph_client_secret,
    )
    result = app.acquire_token_for_client(scopes=[s.graph_scope])
    if result.get("error"):
        logger.warning("Graph token error: %s", result.get("error_description", result.get("error")))
        return None
    return result.get("access_token")


def _normalize_task(graph_task: dict[str, Any], bucket_name_by_id: dict[str, str]) -> dict[str, Any]:
    """Map Graph plannerTask to our task shape (bucketName, assigneeNames, status, lastModifiedAt)."""
    tid = graph_task.get("id", "")
    percent = graph_task.get("percentComplete", 0)
    if percent >= 100:
        status = "completed"
    elif percent > 0:
        status = "inProgress"
    else:
        status = "notStarted"
    assignments = graph_task.get("assignments") or {}
    assignee_ids = [k for k in assignments if isinstance(assignments.get(k), dict)]
    due = graph_task.get("dueDateTime")
    if due and not due.endswith("Z") and "+" not in due:
        due = f"{due}Z"
    last_mod = graph_task.get("completedDateTime") or graph_task.get("createdDateTime") or due
    if last_mod and not last_mod.endswith("Z") and "+" not in last_mod:
        last_mod = f"{last_mod}Z"
    bucket_id = graph_task.get("bucketId") or ""
    return {
        "id": tid,
        "title": graph_task.get("title") or "",
        "bucketId": bucket_id,
        "bucketName": bucket_name_by_id.get(bucket_id, ""),
        "percentComplete": percent,
        "status": status,
        "dueDateTime": due,
        "assignees": assignee_ids,
        "assigneeNames": assignee_ids,
        "lastModifiedAt": last_mod,
    }


def fetch_plan_tasks_from_graph(plan_id: str, token: str) -> list[dict[str, Any]]:
    """
    Fetch tasks and buckets for a plan from Microsoft Graph.
    Returns list of tasks in our normalized shape (bucketName, status, assignees, etc.).
    Raises requests.HTTPError on non-2xx response.
    """
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    buckets_url = f"{GRAPH_BASE}/planner/plans/{plan_id}/buckets"
    tasks_url = f"{GRAPH_BASE}/planner/plans/{plan_id}/tasks"
    bucket_name_by_id: dict[str, str] = {}
    resp = requests.get(buckets_url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    for b in data.get("value", []):
        bucket_name_by_id[b.get("id", "")] = b.get("name", "")
    resp = requests.get(tasks_url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return [_normalize_task(t, bucket_name_by_id) for t in data.get("value", [])]
