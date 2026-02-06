"""
Tests for Planner API v1.

NVS-GenAI: API routes 100% test coverage.
"""

import pytest
from fastapi.testclient import TestClient

from congress_twin.main import app
from congress_twin.services.planner_simulated_data import DEFAULT_PLAN_ID


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestGetTasks:
    def test_returns_200_and_tasks(self, client: TestClient) -> None:
        r = client.get(f"/api/v1/planner/tasks/{DEFAULT_PLAN_ID}")
        assert r.status_code == 200
        data = r.json()
        assert "tasks" in data
        assert "plan_id" in data
        assert "count" in data
        assert data["plan_id"] == DEFAULT_PLAN_ID
        assert isinstance(data["tasks"], list)
        assert data["count"] == len(data["tasks"])
        # Tasks endpoint must NOT return attention-dashboard shape
        assert "blockers" not in data
        assert "overdue" not in data

    def test_unknown_plan_returns_404(self, client: TestClient) -> None:
        r = client.get("/api/v1/planner/tasks/unknown-plan")
        assert r.status_code == 404


class TestGetAttentionDashboard:
    def test_returns_200_and_structure(self, client: TestClient) -> None:
        r = client.get(f"/api/v1/planner/attention-dashboard/{DEFAULT_PLAN_ID}")
        assert r.status_code == 200
        data = r.json()
        assert "blockers" in data
        assert "overdue" in data
        assert "due_next_7_days" in data
        assert "recently_changed" in data
        assert "count" in data["blockers"]
        assert "tasks" in data["blockers"]
        assert isinstance(data["blockers"]["tasks"], list)
        assert isinstance(data["overdue"]["tasks"], list)

    def test_unknown_plan_returns_404(self, client: TestClient) -> None:
        r = client.get("/api/v1/planner/attention-dashboard/unknown-plan")
        assert r.status_code == 404


class TestGetTaskDependencies:
    def test_returns_200_and_upstream_downstream(self, client: TestClient) -> None:
        r = client.get(f"/api/v1/planner/tasks/{DEFAULT_PLAN_ID}/dependencies/task-006")
        assert r.status_code == 200
        data = r.json()
        assert data["task_id"] == "task-006"
        assert "upstream" in data
        assert "downstream" in data
        assert "impact_statement" in data
        assert isinstance(data["upstream"], list)
        assert isinstance(data["downstream"], list)
        # task-006 depends on task-004 and task-005
        assert len(data["upstream"]) == 2
        # task-007 depends on task-006
        assert len(data["downstream"]) == 1

    def test_unknown_task_returns_404(self, client: TestClient) -> None:
        r = client.get(f"/api/v1/planner/tasks/{DEFAULT_PLAN_ID}/dependencies/task-999")
        assert r.status_code == 404

    def test_unknown_plan_returns_404(self, client: TestClient) -> None:
        r = client.get("/api/v1/planner/tasks/unknown-plan/dependencies/task-001")
        assert r.status_code == 404


class TestGetCriticalPath:
    def test_returns_200_and_path(self, client: TestClient) -> None:
        r = client.get(f"/api/v1/planner/critical-path/{DEFAULT_PLAN_ID}")
        assert r.status_code == 200
        data = r.json()
        assert "critical_path" in data
        assert "task_ids" in data
        assert data["plan_id"] == DEFAULT_PLAN_ID
        assert len(data["task_ids"]) >= 1
        assert len(data["critical_path"]) == len(data["task_ids"])

    def test_unknown_plan_returns_404(self, client: TestClient) -> None:
        r = client.get("/api/v1/planner/critical-path/unknown-plan")
        assert r.status_code == 404


class TestPostSync:
    def test_returns_200_and_sync_result(self, client: TestClient) -> None:
        r = client.post(f"/api/v1/planner/sync/{DEFAULT_PLAN_ID}")
        assert r.status_code == 200
        data = r.json()
        assert data["plan_id"] == DEFAULT_PLAN_ID
        assert data["status"] == "ok"
        assert data["source"] == "simulated"
        assert data["tasks_synced"] >= 1
        assert "message" in data

    def test_unknown_plan_returns_200_simulated(self, client: TestClient) -> None:
        # Sync accepts any plan_id; without Graph it returns simulated result for that plan_id
        r = client.post("/api/v1/planner/sync/unknown-plan")
        assert r.status_code == 200
        data = r.json()
        assert data["plan_id"] == "unknown-plan"
        assert data["status"] in ("ok", "error")


class TestGetMilestoneAnalysis:
    def test_returns_200_and_structure(self, client: TestClient) -> None:
        r = client.get(f"/api/v1/planner/milestone-analysis/{DEFAULT_PLAN_ID}")
        assert r.status_code == 200
        data = r.json()
        assert data["plan_id"] == DEFAULT_PLAN_ID
        assert "event_date" in data
        assert "tasks_before_event" in data
        assert "at_risk_tasks" in data
        assert "at_risk_count" in data
        assert isinstance(data["tasks_before_event"], list)
        assert isinstance(data["at_risk_tasks"], list)
        assert data["at_risk_count"] == len(data["at_risk_tasks"])

    def test_accepts_event_date_query(self, client: TestClient) -> None:
        r = client.get(
            f"/api/v1/planner/milestone-analysis/{DEFAULT_PLAN_ID}",
            params={"event_date": "2025-03-15T00:00:00+00:00"},
        )
        assert r.status_code == 200
        assert "2025-03-15" in r.json()["event_date"]

    def test_unknown_plan_returns_404(self, client: TestClient) -> None:
        r = client.get("/api/v1/planner/milestone-analysis/unknown-plan")
        assert r.status_code == 404


class TestHealth:
    def test_health_returns_200(self, client: TestClient) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"
