"""Pytest stub verifying Benchmark health check and evaluation stub."""

from benchmark_engine.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_benchmark_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "benchmark"


def test_benchmark_evaluate():
    log_payload = {
        "request_id": "test-req-004",
        "subtask_id": "subtask_0",
        "user_id": "user_100",
        "prompt_text": "Extract summary",
        "routing_decision": {
            "request_id": "test-req-004",
            "subtask_id": "subtask_0",
            "subtask_text": "Extract summary",
            "complexity_score": 0.1,
            "reasoning_depth": "trivial",
            "chosen_model": "llama3.1:8b",
            "chosen_tier": "local",
            "routing_reason": "Simple summarization",
        },
        "model_call_result": {
            "subtask_id": "subtask_0",
            "model_used": "llama3.1:8b",
            "tokens_in": 100,
            "tokens_out": 50,
            "latency_ms": 150.0,
            "cost_usd": 0.0,
            "raw_output": "Summary text",
        },
    }

    eval_res = client.post("/v1/benchmark/evaluate", json=log_payload)
    assert eval_res.status_code == 200
    data = eval_res.json()
    assert data["request_id"] == "test-req-004"
    assert data["cost_savings_pct"] == 100.0
    assert data["baseline_cost_usd"] > 0
