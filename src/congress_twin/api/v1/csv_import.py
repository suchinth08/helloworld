"""
Import API v1 — CSV import for MS Planner tasks.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from congress_twin.services.csv_importer import import_csv_to_planner_tasks
from congress_twin.services.planner_simulated_data import DEFAULT_PLAN_ID

router = APIRouter()


class ImportResponse(BaseModel):
    tasks_created: int
    tasks_updated: int
    errors: list[str]
    bucket_mapping: dict[str, str]


@router.post("/csv", response_model=ImportResponse)
async def import_csv(
    plan_id: str = DEFAULT_PLAN_ID,
    file: UploadFile = File(...),
) -> ImportResponse:
    """
    Import CSV file with MS Planner tasks.
    
    Expected CSV format:
    ID, Bucket, Label, Task, Start Date, Due Date, Priority, Assignments, Dependencies, Notes
    
    Returns import summary with tasks created/updated, errors, and bucket mapping.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    try:
        content = await file.read()
        result = import_csv_to_planner_tasks(plan_id, content)
        return ImportResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
