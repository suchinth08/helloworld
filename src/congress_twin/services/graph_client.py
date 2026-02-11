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


def _normalize_datetime(dt: Any) -> Optional[str]:
    """Normalize datetime string to ISO format with Z suffix."""
    if not dt:
        return None
    dt_str = str(dt)
    if not dt_str.endswith("Z") and "+" not in dt_str:
        return f"{dt_str}Z"
    return dt_str


def _extract_identity_set(identity: dict[str, Any] | None) -> Optional[str]:
    """Extract user ID from identitySet (createdBy, completedBy)."""
    if not identity:
        return None
    if isinstance(identity, dict):
        # identitySet can have user, application, etc.
        user = identity.get("user") or identity.get("application")
        if user:
            return user.get("id") or user.get("displayName")
    return None


def _map_applied_categories(categories: dict[str, Any] | None) -> list[str]:
    """Map appliedCategories (category1-25) to label names."""
    if not categories:
        return []
    labels = []
    # MS Planner uses category1, category2, ..., category25
    # Map to meaningful labels if available, otherwise use category name
    category_labels = {
        "category1": "External Dependency",
        "category2": "High Risk",
        "category3": "VIP Speaker",
        "category4": "Urgent",
        "category5": "Blocked",
        # Add more mappings as needed
    }
    for cat_key, cat_value in categories.items():
        if cat_value:  # True if category is applied
            label = category_labels.get(cat_key, cat_key)
            labels.append(label)
    return labels


def _normalize_task(graph_task: dict[str, Any], bucket_name_by_id: dict[str, str], task_details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Map Graph plannerTask to our task shape with all MS Planner fields (per ACP_05 PDF reference)."""
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
    # Extract assignee names if available
    assignee_names = []
    for user_id, assignment in assignments.items():
        if isinstance(assignment, dict):
            assignee_names.append(user_id)  # Use ID as name if no display name
    
    due = _normalize_datetime(graph_task.get("dueDateTime"))
    start = _normalize_datetime(graph_task.get("startDateTime"))
    completed = _normalize_datetime(graph_task.get("completedDateTime"))
    created = _normalize_datetime(graph_task.get("createdDateTime"))
    last_mod = completed or created or _normalize_datetime(graph_task.get("dueDateTime"))
    
    bucket_id = graph_task.get("bucketId") or ""
    
    # Extract appliedCategories
    applied_categories = _map_applied_categories(graph_task.get("appliedCategories"))
    
    task = {
        "id": tid,
        "title": graph_task.get("title") or "",
        "bucketId": bucket_id,
        "bucketName": bucket_name_by_id.get(bucket_id, ""),
        "percentComplete": percent,
        "status": status,
        "dueDateTime": due,
        "startDateTime": start,
        "completedDateTime": completed,
        "createdDateTime": created,
        "assignees": assignee_ids,
        "assigneeNames": assignee_names,
        "lastModifiedAt": last_mod,
        "priority": graph_task.get("priority"),
        "orderHint": graph_task.get("orderHint"),
        "assigneePriority": graph_task.get("assigneePriority"),
        "appliedCategories": applied_categories,
        "conversationThreadId": graph_task.get("conversationThreadId"),
        "createdBy": _extract_identity_set(graph_task.get("createdBy")),
        "completedBy": _extract_identity_set(graph_task.get("completedBy")),
    }
    
    # Add task details if provided
    if task_details:
        task["description"] = task_details.get("description")
        task["previewType"] = task_details.get("previewType")
        # Checklist and references are handled separately
    
    return task


def fetch_task_details_from_graph(task_id: str, token: str) -> dict[str, Any]:
    """
    Fetch task details (description, checklist, references, previewType) from Microsoft Graph.
    Returns details dict or empty dict if not found.
    """
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    details_url = f"{GRAPH_BASE}/planner/tasks/{task_id}/details"
    try:
        resp = requests.get(details_url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return {}
        raise


def fetch_task_dependencies_from_graph(plan_id: str, token: str) -> dict[str, list[dict[str, str]]]:
    """
    Extract task dependencies from references field.
    Returns dict mapping task_id -> list of {dependsOnTaskId, dependencyType}.
    """
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    tasks_url = f"{GRAPH_BASE}/planner/plans/{plan_id}/tasks?$expand=details"
    dependencies_map: dict[str, list[dict[str, str]]] = {}
    
    try:
        resp = requests.get(tasks_url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        for task in data.get("value", []):
            task_id = task.get("id")
            if not task_id:
                continue
            
            details = task.get("details")
            if not details:
                # Fetch details separately if not expanded
                details = fetch_task_details_from_graph(task_id, token)
            
            references = details.get("references") or {}
            deps = []
            for ref_alias, ref_data in references.items():
                if isinstance(ref_data, dict):
                    ref_type = ref_data.get("type", "")
                    # Check if reference is to another Planner task
                    if ref_type == "plannerTask" or "planner" in ref_type.lower():
                        # Extract task ID from reference (may be in alias or href)
                        ref_href = ref_data.get("href", "")
                        # Try to extract task ID from href or alias
                        # Format: https://graph.microsoft.com/v1.0/planner/tasks/{taskId}
                        if "/planner/tasks/" in ref_href:
                            dep_task_id = ref_href.split("/planner/tasks/")[-1].split("/")[0]
                            deps.append({"dependsOnTaskId": dep_task_id, "dependencyType": "FS"})
            
            if deps:
                dependencies_map[task_id] = deps
    except requests.HTTPError as e:
        logger.warning("Failed to fetch dependencies: %s", e)
    
    return dependencies_map


def fetch_plan_tasks_from_graph(plan_id: str, token: str, include_details: bool = True) -> list[dict[str, Any]]:
    """
    Fetch tasks and buckets for a plan from Microsoft Graph with all fields (per ACP_05 PDF).
    Returns list of tasks in our normalized shape with all MS Planner fields.
    Raises requests.HTTPError on non-2xx response.
    
    Args:
        plan_id: Planner plan ID
        token: OAuth2 access token
        include_details: If True, fetch task details (description, checklist, references)
    """
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    buckets_url = f"{GRAPH_BASE}/planner/plans/{plan_id}/buckets"
    tasks_url = f"{GRAPH_BASE}/planner/plans/{plan_id}/tasks"
    
    if include_details:
        tasks_url += "?$expand=details"
    
    bucket_name_by_id: dict[str, str] = {}
    resp = requests.get(buckets_url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    for b in data.get("value", []):
        bucket_name_by_id[b.get("id", "")] = b.get("name", "")
    
    resp = requests.get(tasks_url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    
    tasks = []
    for t in data.get("value", []):
        task_details = None
        if include_details:
            task_details = t.get("details")
        tasks.append(_normalize_task(t, bucket_name_by_id, task_details))
    
    return tasks
