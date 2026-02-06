"""
Pytest fixtures for Congress Twin.

NVS-GenAI: Tests mirror src/congress_twin structure.
"""

import pytest
from fastapi.testclient import TestClient

from congress_twin.main import app


@pytest.fixture(scope="session")
def default_plan_id() -> str:
    return "uc31-plan"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
