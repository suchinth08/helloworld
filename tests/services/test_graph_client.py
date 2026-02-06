"""
Tests for Graph API client (Phase 1).
"""

import pytest

from congress_twin.services.graph_client import (
    _normalize_task,
    is_graph_configured,
)


class TestIsGraphConfigured:
    def test_returns_false_without_env(self) -> None:
        assert is_graph_configured() is False


class TestNormalizeTask:
    def test_maps_graph_task_to_normalized_shape(self) -> None:
        graph_task = {
            "id": "task-abc",
            "title": "Design API",
            "bucketId": "bucket-1",
            "percentComplete": 60,
            "dueDateTime": "2025-03-01T12:00:00Z",
            "assignments": {"user-1": {"@odata.type": "microsoft.graph.plannerAssignment"}},
            "createdDateTime": "2025-01-01T00:00:00Z",
        }
        out = _normalize_task(graph_task, {"bucket-1": "Build"})
        assert out["id"] == "task-abc"
        assert out["title"] == "Design API"
        assert out["bucketName"] == "Build"
        assert out["status"] == "inProgress"
        assert out["percentComplete"] == 60
        assert out["assignees"] == ["user-1"]
        assert out["assigneeNames"] == ["user-1"]

    def test_percent_100_is_completed(self) -> None:
        out = _normalize_task(
            {"id": "x", "title": "Done", "percentComplete": 100},
            {},
        )
        assert out["status"] == "completed"

    def test_percent_0_is_not_started(self) -> None:
        out = _normalize_task(
            {"id": "x", "title": "Todo", "percentComplete": 0},
            {},
        )
        assert out["status"] == "notStarted"
