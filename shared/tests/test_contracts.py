"""Test verification for shared schema contracts and JSON schema generation."""

import pytest

from shared.schemas.contracts import (
    BenchmarkRecord,
    DecisionLogEntry,
    FinalResponse,
    ModelCallResult,
    ModelTier,
    OverrideDetails,
    ReasoningDepth,
    RoutingDecision,
    RoutingRequest,
    SubtaskBreakdownItem,
    SubtaskPrompt,
)


def test_routing_request_instantiation():
    req = RoutingRequest(
        request_id="req-123",
        user_id="user-abc",
        prompt="Write a Python script to sort a list",
        subtasks=[SubtaskPrompt(subtask_id="sub-1", prompt="Sort list algorithm")],
        max_cost_usd=0.05,
        quality_floor=0.8,
        override_model=None,
        metadata={"priority": "high"},
    )
    assert req.request_id == "req-123"
    assert req.user_id == "user-abc"
    assert len(req.subtasks) == 1
    assert req.subtasks[0].subtask_id == "sub-1"


def test_routing_decision_instantiation():
    decision = RoutingDecision(
        request_id="req-123",
        subtask_id="sub-1",
        subtask_text="Sort list algorithm",
        complexity_score=0.2,
        reasoning_depth=ReasoningDepth.TRIVIAL,
        chosen_model="llama3.1:8b",
        chosen_tier=ModelTier.LOCAL,
        routing_reason="Trivial programming task easily resolved by 8B local model",
        fallback_model="gpt-4o-mini",
        overridden_by_user=False,
    )
    assert decision.chosen_model == "llama3.1:8b"
    assert decision.chosen_tier == ModelTier.LOCAL
    assert decision.complexity_score == 0.2


def test_model_call_result_instantiation():
    result = ModelCallResult(
        subtask_id="sub-1",
        model_used="llama3.1:8b",
        tokens_in=35,
        tokens_out=60,
        latency_ms=145.2,
        cost_usd=0.0,
        raw_output="def sort_list(lst): return sorted(lst)",
        error=None,
    )
    assert result.subtask_id == "sub-1"
    assert result.cost_usd == 0.0
    assert result.tokens_out == 60


def test_final_response_instantiation():
    decision = RoutingDecision(
        request_id="req-123",
        subtask_id="sub-1",
        subtask_text="Sort list algorithm",
        complexity_score=0.2,
        reasoning_depth=ReasoningDepth.TRIVIAL,
        chosen_model="llama3.1:8b",
        chosen_tier=ModelTier.LOCAL,
        routing_reason="Trivial task",
    )
    result = ModelCallResult(
        subtask_id="sub-1",
        model_used="llama3.1:8b",
        tokens_in=35,
        tokens_out=60,
        latency_ms=145.2,
        cost_usd=0.0,
        raw_output="def sort_list(lst): return sorted(lst)",
    )
    final_resp = FinalResponse(
        request_id="req-123",
        final_answer="def sort_list(lst): return sorted(lst)",
        subtask_breakdown=[
            SubtaskBreakdownItem(subtask_id="sub-1", decision=decision, result=result)
        ],
        total_cost_usd=0.0,
        total_latency_ms=145.2,
    )
    assert final_resp.request_id == "req-123"
    assert len(final_resp.subtask_breakdown) == 1


def test_decision_log_entry_instantiation():
    decision = RoutingDecision(
        request_id="req-123",
        subtask_id="sub-1",
        subtask_text="Sort list algorithm",
        complexity_score=0.2,
        reasoning_depth=ReasoningDepth.TRIVIAL,
        chosen_model="llama3.1:8b",
        chosen_tier=ModelTier.LOCAL,
        routing_reason="Trivial task",
    )
    log_entry = DecisionLogEntry(
        request_id="req-123",
        subtask_id="sub-1",
        user_id="user-abc",
        prompt_text="Sort list algorithm",
        routing_decision=decision,
        override_details=OverrideDetails(is_overridden=False),
        client_ip="127.0.0.1",
    )
    assert log_entry.request_id == "req-123"
    assert log_entry.routing_decision.chosen_model == "llama3.1:8b"


def test_benchmark_record_instantiation():
    bench = BenchmarkRecord(
        request_id="req-123",
        task_category="coding",
        router_cost_usd=0.0,
        baseline_cost_usd=0.0025,
        cost_savings_pct=100.0,
        router_quality_score=0.92,
        baseline_quality_score=0.95,
        quality_delta=-0.03,
    )
    assert bench.cost_savings_pct == 100.0
    assert bench.quality_delta == pytest.approx(-0.03)


def test_json_schema_export():
    models = [
        RoutingRequest,
        RoutingDecision,
        ModelCallResult,
        FinalResponse,
        DecisionLogEntry,
        BenchmarkRecord,
    ]
    for model in models:
        schema = model.model_json_schema()
        assert "title" in schema
        assert "properties" in schema
