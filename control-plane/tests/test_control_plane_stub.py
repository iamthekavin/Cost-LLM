"""Pytest stub verifying Control Plane endpoints."""

from control_plane.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_control_plane_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "control-plane"


def test_control_plane_log_ingest_and_query():
    log_payload = {
        "request_id": "test-req-003",
        "subtask_id": "subtask_0",
        "user_id": "user_42",
        "prompt_text": "Calculate 2 + 2",
        "routing_decision": {
            "request_id": "test-req-003",
            "subtask_id": "subtask_0",
            "subtask_text": "Calculate 2 + 2",
            "complexity_score": 0.05,
            "reasoning_depth": "trivial",
            "chosen_model": "llama3.1:8b",
            "chosen_tier": "local",
            "routing_reason": "Simple math",
            "overridden_by_user": False,
        },
        "override_details": {"is_overridden": False},
    }

    # Ingest log
    ingest_res = client.post("/v1/logs", json=log_payload)
    assert ingest_res.status_code == 200

    # Retrieve log
    query_res = client.get("/v1/logs/test-req-003")
    assert query_res.status_code == 200
    logs = query_res.json()
    assert len(logs) == 1
    assert logs[0]["request_id"] == "test-req-003"
    assert logs[0]["routing_decision"]["chosen_model"] == "llama3.1:8b"


def test_control_plane_dashboard():
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Cost-LLM Control Plane" in response.text
