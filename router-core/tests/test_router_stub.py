"""Pytest stub verifying Router Core health check and contract ingestion."""

from fastapi.testclient import TestClient
from router_core.main import app

client = TestClient(app)


def test_router_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "router-core"


def test_router_scaffold_route():
    payload = {
        "request_id": "test-req-001",
        "user_id": "user-test",
        "prompt": "Hello router core",
    }
    response = client.post("/v1/route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == "test-req-001"
    assert "final_answer" in data
    assert len(data["subtask_breakdown"]) >= 1
