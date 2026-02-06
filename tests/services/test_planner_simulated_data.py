"""
Tests for simulated Planner data.

NVS-GenAI: Tests mirror src/congress_twin/services.
"""

import pytest

from congress_twin.services.planner_simulated_data import (
    DEFAULT_PLAN_ID,
    get_simulated_buckets,
    get_simulated_tasks,
    get_simulated_dependencies,
)


class TestSimulatedBuckets:
    def test_returns_list(self) -> None:
        buckets = get_simulated_buckets()
        assert isinstance(buckets, list)

    def test_bucket_has_id_name(self) -> None:
        buckets = get_simulated_buckets()
        assert len(buckets) >= 1
        for b in buckets:
            assert "id" in b
            assert "name" in b
            assert b["id"]
            assert b["name"]

    def test_plan_id_in_bucket_id(self) -> None:
        buckets = get_simulated_buckets(DEFAULT_PLAN_ID)
        for b in buckets:
            assert DEFAULT_PLAN_ID in b["id"]


class TestSimulatedTasks:
    def test_returns_list(self) -> None:
        tasks = get_simulated_tasks()
        assert isinstance(tasks, list)

    def test_task_has_required_fields(self) -> None:
        tasks = get_simulated_tasks()
        assert len(tasks) >= 1
        for t in tasks:
            assert "id" in t
            assert "title" in t
            assert "bucketId" in t
            assert "percentComplete" in t
            assert "status" in t

    def test_status_values_valid(self) -> None:
        tasks = get_simulated_tasks()
        allowed = {"notStarted", "inProgress", "completed"}
        for t in tasks:
            assert t["status"] in allowed


class TestSimulatedDependencies:
    def test_returns_list_of_tuples(self) -> None:
        deps = get_simulated_dependencies()
        assert isinstance(deps, list)
        for d in deps:
            assert isinstance(d, tuple)
            assert len(d) == 2
            assert isinstance(d[0], str)
            assert isinstance(d[1], str)

    def test_deps_refer_to_task_ids(self) -> None:
        tasks = get_simulated_tasks()
        task_ids = {t["id"] for t in tasks}
        deps = get_simulated_dependencies()
        for task_id, depends_on in deps:
            assert task_id in task_ids
            assert depends_on in task_ids
