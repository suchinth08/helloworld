"""
Seed the app DB with Novartis Congress event scheduling data (MS Planner–shaped).

Usage (from repo root, with venv/uv):
  PYTHONPATH=src uv run python -m congress_twin.scripts.seed_congress_db

Or via API (after starting backend):
  curl -X POST "http://localhost:8010/api/v1/planner/seed?plan_id=uc31-plan"

Ensures planner_tasks and plan_sync_state tables in SQLite, upserts congress tasks for the default plan,
and sets sync state so "changes since sync" has a baseline. Uses relative dates so the attention
dashboard shows "Due next 7 days", "Critical path due next", and "Recently changed".

After seeding, the UI and APIs serve from DB for the default plan (uc31-plan).
"""

import logging
import sys
from datetime import datetime, timezone

from congress_twin.db.planner_repo import (
    ensure_plan_sync_state_table,
    ensure_planner_tasks_table,
    set_plan_sync_state,
    upsert_planner_tasks,
)
from congress_twin.services.congress_seed_data import DEFAULT_PLAN_ID, get_congress_seed_tasks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> int:
    plan_id = DEFAULT_PLAN_ID
    logger.info("Seeding Congress data for plan_id=%s", plan_id)

    ensure_planner_tasks_table()
    ensure_plan_sync_state_table()

    tasks = get_congress_seed_tasks(plan_id, use_relative_dates_for_attention=True)
    upsert_planner_tasks(plan_id, tasks)
    logger.info("Upserted %d tasks", len(tasks))

    now = datetime.now(timezone.utc)
    set_plan_sync_state(plan_id, now, previous_sync_at=now)
    logger.info("Set plan_sync_state last_sync_at=%s", now.isoformat())

    logger.info("Seed complete. UI/APIs will use DB for plan %s.", plan_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
