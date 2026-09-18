"""Pytest stub verifying Model Gateway health check and execution stub."""

from fastapi.testclient import TestClient
from model_gateway.main import app

client = TestClient(app)


def test_gateway_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "model-gateway"


def test_gateway_execute_stub():
    decision_payload = {
        "request_id": "test-req-002",
        "subtask_id": "sub-1",
        "subtask_text": "Summarize this sentence.",
        "complexity_score": 0.2,
        "reasoning_depth": "trivial",
        "chosen_model": "llama3.1:8b",
        "chosen_tier": "local",
        "routing_reason": "Low complexity",
    }
    response = client.post("/v1/execute", json=decision_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["subtask_id"] == "sub-1"
    assert data["model_used"] == "llama3.1:8b"
    assert data["cost_usd"] == 0.0
    assert "raw_output" in data
