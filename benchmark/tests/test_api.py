"""API Integration Tests for Benchmark Engine (Member D)."""
from datetime import datetime, timezone

from starlette.testclient import TestClient

from benchmark.benchmark_engine.main import app
from shared.schemas.contracts import (
    BenchmarkRecord,
    DecisionLogEntry,
    ModelCallResult,
    ModelTier,
    ReasoningDepth,
    RoutingDecision,
)

client = TestClient(app)


def test_health_check():
    """Verify health endpoint."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "benchmark"
    assert data["status"] == "ok"


def test_evaluate_log_entry():
    """Verify evaluation of DecisionLogEntry into BenchmarkRecord."""
    log_entry = DecisionLogEntry(
        request_id="req_test_01",
        subtask_id="sub_0",
        prompt_text="Extract key info",
        routing_decision=RoutingDecision(
            request_id="req_test_01",
            subtask_id="sub_0",
            subtask_text="Extract key info",
            complexity_score=0.1,
            reasoning_depth=ReasoningDepth.TRIVIAL,
            chosen_model="llama3.1:8b",
            chosen_tier=ModelTier.LOCAL,
            routing_reason="Trivial extraction",
        ),
        model_call_result=ModelCallResult(
            subtask_id="sub_0",
            model_used="llama3.1:8b",
            tokens_in=20,
            tokens_out=10,
            latency_ms=150.0,
            cost_usd=0.0,
            raw_output="Extracted info",
        ),
    )

    resp = client.post("/v1/benchmark/evaluate", json=log_entry.model_dump(mode="json"))
    assert resp.status_code == 200
    record = resp.json()
    assert record["request_id"] == "req_test_01"
    assert record["router_cost_usd"] == 0.0
    assert record["cost_savings_pct"] == 100.0


def test_list_and_ingest_records():
    """Verify ingesting and listing BenchmarkRecord entries."""
    new_record = BenchmarkRecord(
        request_id="req_ingest_01",
        task_category="coding",
        router_cost_usd=0.001,
        baseline_cost_usd=0.005,
        cost_savings_pct=80.0,
        router_quality_score=0.95,
        baseline_quality_score=0.98,
        quality_delta=-0.03,
        timestamp=datetime.now(timezone.utc),
    )

    resp_post = client.post(
        "/v1/benchmark/records", json=new_record.model_dump(mode="json")
    )
    assert resp_post.status_code == 200

    resp_get = client.get("/v1/benchmark/records")
    assert resp_get.status_code == 200
    records = resp_get.json()
    assert len(records) >= 1
    assert any(r["request_id"] == "req_ingest_01" for r in records)


def test_benchmark_summary():
    """Verify summary endpoint returns aggregated statistics."""
    resp = client.get("/v1/benchmark/summary")
    assert resp.status_code == 200
    summary = resp.json()
    assert "cumulative_savings_pct" in summary
    assert "average_router_quality" in summary
    assert summary["total_evaluated_requests"] >= 1
