"""
CSV Import service: Parse CSV files and map fields to MS Planner standard (per ACP_05 PDF reference).

CSV Format:
ID, Bucket, Label, Task, Start Date, Due Date, Priority, Assignments, Dependencies, Notes

Field Mapping:
- CSV ID → planner_task_id
- CSV Bucket → bucket_name (lookup/create bucketId)
- CSV Label → applied_categories (parse comma-separated labels)
- CSV Task → title
- CSV Start Date → start_date_time (parse date format)
- CSV Due Date → due_date_time
- CSV Priority → priority (map "Medium" → 5, "High" → 3, "Low" → 9)
- CSV Assignments → assignees (parse comma-separated user IDs/names)
- CSV Dependencies → planner_task_dependencies (parse task IDs)
- CSV Notes → description
"""

import csv
import json
import logging
from datetime import datetime
from io import StringIO
from typing import Any

from congress_twin.db.planner_repo import (
    ensure_planner_tasks_table,
    upsert_planner_tasks,
    upsert_planner_task_details,
    upsert_planner_task_dependencies,
)

logger = logging.getLogger(__name__)


def _parse_date(date_str: str | None) -> str | None:
    """Parse date string in various formats to ISO format."""
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()
    # Try common formats: MM-DD-YYYY, YYYY-MM-DD, DD/MM/YYYY, etc.
    formats = [
        "%m-%d-%Y",
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m-%d-%y",
        "%m/%d/%y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.isoformat() + "Z"
        except ValueError:
            continue
    logger.warning("Could not parse date: %s", date_str)
    return None


def _parse_priority(priority_str: str | None) -> int | None:
    """Map priority string to integer (0-10)."""
    if not priority_str:
        return None
    priority_str = priority_str.strip().lower()
    mapping = {
        "urgent": 1,
        "high": 3,
        "important": 3,
        "medium": 5,
        "normal": 5,
        "low": 9,
    }
    if priority_str in mapping:
        return mapping[priority_str]
    # Try to parse as integer
    try:
        p = int(priority_str)
        if 0 <= p <= 10:
            return p
    except ValueError:
        pass
    return 5  # Default to medium


def _parse_list(value: str | None, separator: str = ",") -> list[str]:
    """Parse comma-separated string into list, trimming whitespace."""
    if not value or not value.strip():
        return []
    return [item.strip() for item in value.split(separator) if item.strip()]


def _parse_dependencies(deps_str: str | None) -> list[dict[str, str]]:
    """Parse dependencies string into list of dependency objects."""
    if not deps_str or not deps_str.strip():
        return []
    # Dependencies can be: "1,2,3" or "1:FS,2:SS" (with types)
    deps = []
    for dep_str in _parse_list(deps_str):
        if ":" in dep_str:
            task_id, dep_type = dep_str.split(":", 1)
            deps.append({"dependsOnTaskId": task_id.strip(), "dependencyType": dep_type.strip().upper()})
        else:
            deps.append({"dependsOnTaskId": dep_str.strip(), "dependencyType": "FS"})
    return deps


def import_csv_to_planner_tasks(plan_id: str, csv_content: str | bytes, bucket_name_to_id: dict[str, str] | None = None) -> dict[str, Any]:
    """
    Import CSV content into planner_tasks.
    
    Args:
        plan_id: Plan ID to import tasks into
        csv_content: CSV file content as string or bytes
        bucket_name_to_id: Optional mapping of bucket names to bucket IDs (if None, will generate IDs)
    
    Returns:
        dict with keys: tasks_created, tasks_updated, errors, bucket_mapping
    """
    ensure_planner_tasks_table()
    
    if isinstance(csv_content, bytes):
        csv_content = csv_content.decode("utf-8")
    
    if bucket_name_to_id is None:
        bucket_name_to_id = {}
    
    reader = csv.DictReader(StringIO(csv_content))
    
    # Expected columns (case-insensitive)
    expected_cols = {
        "id": None,
        "bucket": None,
        "label": None,
        "task": None,
        "start date": None,
        "due date": None,
        "priority": None,
        "assignments": None,
        "dependencies": None,
        "notes": None,
    }
    
    # Find actual column names (case-insensitive)
    actual_cols = {}
    for col in reader.fieldnames or []:
        col_lower = col.lower().strip()
        for expected in expected_cols:
            if expected in col_lower or col_lower in expected:
                actual_cols[expected] = col
                break
    
    # Validate required columns
    required = ["id", "task", "due date"]
    missing = [r for r in required if r not in actual_cols]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    tasks = []
    task_details_map: dict[str, dict[str, Any]] = {}
    task_dependencies_map: dict[str, list[dict[str, str]]] = {}
    errors: list[str] = []
    
    for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        try:
            task_id = row.get(actual_cols.get("id", "")) or row.get("ID", "")
            if not task_id:
                errors.append(f"Row {row_num}: Missing ID")
                continue
            
            bucket_name = row.get(actual_cols.get("bucket", "")) or row.get("Bucket", "")
            if bucket_name:
                if bucket_name not in bucket_name_to_id:
                    # Generate bucket ID from name
                    bucket_id = f"{plan_id}-bucket-{bucket_name.lower().replace(' ', '-').replace('&', 'and')}"
                    bucket_name_to_id[bucket_name] = bucket_id
                bucket_id = bucket_name_to_id[bucket_name]
            else:
                bucket_id = None
            
            # Parse labels (applied categories)
            label_str = row.get(actual_cols.get("label", "")) or row.get("Label", "")
            applied_categories = _parse_list(label_str)
            
            title = row.get(actual_cols.get("task", "")) or row.get("Task", "")
            if not title:
                errors.append(f"Row {row_num}: Missing Task title")
                continue
            
            start_date = _parse_date(row.get(actual_cols.get("start date", "")) or row.get("Start Date", ""))
            due_date = _parse_date(row.get(actual_cols.get("due date", "")) or row.get("Due Date", ""))
            if not due_date:
                errors.append(f"Row {row_num}: Missing or invalid Due Date")
                continue
            
            priority = _parse_priority(row.get(actual_cols.get("priority", "")) or row.get("Priority", ""))
            
            assignments_str = row.get(actual_cols.get("assignments", "")) or row.get("Assignments", "")
            assignees = _parse_list(assignments_str)
            assignee_names = assignees  # Use same list for names if no separate mapping
            
            dependencies_str = row.get(actual_cols.get("dependencies", "")) or row.get("Dependencies", "")
            dependencies = _parse_dependencies(dependencies_str)
            if dependencies:
                task_dependencies_map[task_id] = dependencies
            
            notes = row.get(actual_cols.get("notes", "")) or row.get("Notes", "")
            if notes:
                task_details_map[task_id] = {"description": notes}
            
            task = {
                "id": task_id,
                "title": title,
                "bucketId": bucket_id,
                "bucketName": bucket_name,
                "status": "notStarted",
                "percentComplete": 0,
                "startDateTime": start_date,
                "dueDateTime": due_date,
                "priority": priority,
                "assignees": assignees,
                "assigneeNames": assignee_names,
                "appliedCategories": applied_categories,
                "description": notes,
            }
            tasks.append(task)
            
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            logger.warning("Error parsing CSV row %d: %s", row_num, e)
    
    # Upsert tasks
    tasks_created = 0
    tasks_updated = 0
    try:
        count = upsert_planner_tasks(plan_id, tasks)
        # Assume all are updates if count > 0 (we can't distinguish without checking existence)
        tasks_updated = count
    except Exception as e:
        errors.append(f"Failed to upsert tasks: {str(e)}")
        logger.error("Failed to upsert tasks: %s", e)
    
    # Upsert task details
    for task_id, details in task_details_map.items():
        try:
            upsert_planner_task_details(plan_id, task_id, details)
        except Exception as e:
            errors.append(f"Failed to upsert details for task {task_id}: {str(e)}")
    
    # Upsert dependencies
    for task_id, deps in task_dependencies_map.items():
        try:
            upsert_planner_task_dependencies(plan_id, task_id, deps)
        except Exception as e:
            errors.append(f"Failed to upsert dependencies for task {task_id}: {str(e)}")
    
    return {
        "tasks_created": 0,  # Can't distinguish without pre-check
        "tasks_updated": tasks_updated,
        "errors": errors,
        "bucket_mapping": bucket_name_to_id,
    }
