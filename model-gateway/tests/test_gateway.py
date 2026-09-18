"""Integration tests for Model Gateway API endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from model_gateway.main import app

from shared.schemas.contracts import ModelCallResult

client = TestClient(app)


def test_health_endpoint_ollama_offline():
    with patch("model_gateway.providers.local_ollama.LocalOllamaProvider.check_health", new_callable=AsyncMock) as mock_health:
        mock_health.return_value = {"reachable": False, "error": "Connection refused"}
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "model-gateway"
        assert data["status"] == "degraded"
        assert data["ollama_reachable"] is False


def test_health_endpoint_ollama_online():
    with patch("model_gateway.providers.local_ollama.LocalOllamaProvider.check_health", new_callable=AsyncMock) as mock_health:
        mock_health.return_value = {"reachable": True, "models": ["llama3.1:8b"], "has_target_model": True}
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "model-gateway"
        assert data["status"] == "ok"
        assert data["ollama_reachable"] is True


def test_call_endpoint_success():
    with patch("model_gateway.main.execute_call", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = ModelCallResult(
            subtask_id="sub-101",
            model_used="llama3.1:8b",
            tokens_in=15,
            tokens_out=30,
            latency_ms=120.0,
            cost_usd=0.0,
            raw_output="42",
        )
        payload = {
            "subtask_id": "sub-101",
            "subtask_text": "What is 6 * 7?",
            "chosen_model": "llama3.1:8b",
        }
        res = client.post("/call", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["subtask_id"] == "sub-101"
        assert data["raw_output"] == "42"
        assert data["cost_usd"] == 0.0


def test_v1_execute_endpoint_routing_decision():
    with patch("model_gateway.main.execute_call", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = ModelCallResult(
            subtask_id="sub-202",
            model_used="gpt-4o-mini",
            tokens_in=50,
            tokens_out=25,
            latency_ms=250.0,
            cost_usd=0.000023,
            raw_output="Paris",
        )
        decision = {
            "request_id": "req-999",
            "subtask_id": "sub-202",
            "subtask_text": "Capital of France?",
            "complexity_score": 0.2,
            "reasoning_depth": "trivial",
            "chosen_model": "gpt-4o-mini",
            "chosen_tier": "cheap",
            "routing_reason": "Fact lookup",
            "fallback_model": "gpt-4o",
        }
        res = client.post("/v1/execute", json=decision)
        assert res.status_code == 200
        data = res.json()
        assert data["subtask_id"] == "sub-202"
        assert data["model_used"] == "gpt-4o-mini"
