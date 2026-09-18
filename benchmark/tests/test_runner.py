"""Tests for Benchmark Runner Harness (Member D)."""
import pytest

from benchmark.runner import BenchmarkRunner, LocalRouterPipelineSimulator, calculate_cost
from shared.schemas.contracts import BenchmarkRecord, FinalResponse, ModelTier, RoutingRequest


def test_calculate_cost():
    """Verify cost calculation matches official Contract pricing."""
    # llama3.1:8b is strictly $0.00
    assert calculate_cost("llama3.1:8b", 500, 200) == 0.0

    # gpt-4o-mini ($0.15/1M in, $0.60/1M out)
    # 1000 in = 0.00015, 1000 out = 0.00060 -> total 0.00075
    assert calculate_cost("gpt-4o-mini", 1000, 1000) == 0.00075

    # gpt-4o ($2.50/1M in, $10.00/1M out)
    # 1000 in = 0.0025, 1000 out = 0.010 -> total 0.0125
    assert calculate_cost("gpt-4o", 1000, 1000) == 0.0125


def test_simulator_router_execution():
    """Verify simulator generates valid FinalResponse contract objects."""
    sim = LocalRouterPipelineSimulator()

    # Trivial task
    req_t = RoutingRequest(request_id="req_t", user_id="u1", prompt="Extract order 123")
    meta_t = {"task_id": "t1", "expected_difficulty": "trivial", "ground_truth": "123"}
    resp_t = sim.execute_router_pipeline(req_t, meta_t)

    assert isinstance(resp_t, FinalResponse)
    assert resp_t.total_cost_usd == 0.0
    assert len(resp_t.subtask_breakdown) == 1
    assert resp_t.subtask_breakdown[0].decision.chosen_tier == ModelTier.LOCAL

    # Deep task
    req_d = RoutingRequest(request_id="req_d", user_id="u1", prompt="Solve high level theorem")
    meta_d = {"task_id": "d1", "expected_difficulty": "deep", "ground_truth": "QED"}
    resp_d = sim.execute_router_pipeline(req_d, meta_d)

    assert isinstance(resp_d, FinalResponse)
    assert resp_d.total_cost_usd > 0.0
    assert resp_d.subtask_breakdown[0].decision.chosen_tier == ModelTier.PREMIUM


def test_simulator_multipart_decomposition():
    """Verify multi-part tasks decompose into multiple subtasks with breakdown."""
    sim = LocalRouterPipelineSimulator()
    req = RoutingRequest(
        request_id="req_mp",
        user_id="u1",
        prompt="Part 1: Extract email AND Part 2: Summarize text",
    )
    meta = {"task_id": "mp1", "is_multi_part": True, "expected_difficulty": "moderate"}
    resp = sim.execute_router_pipeline(req, meta)

    assert len(resp.subtask_breakdown) >= 2
    assert resp.subtask_breakdown[0].subtask_id == "sub_1"
    assert resp.subtask_breakdown[1].subtask_id == "sub_2"


@pytest.mark.asyncio
async def test_runner_single_task():
    """Verify run_single_task generates a valid BenchmarkRecord contract."""
    runner = BenchmarkRunner(force_mock=True)
    task = {
        "task_id": "test_t1",
        "prompt": "Extract 999",
        "category": "extraction",
        "expected_difficulty": "trivial",
        "is_multi_part": False,
        "scoring_method": "exact_match",
        "ground_truth": "999",
    }

    result = await runner.run_single_task(task, is_live=False)
    rec = result["record"]

    assert isinstance(rec, BenchmarkRecord)
    assert rec.task_category == "extraction"
    assert rec.router_cost_usd == 0.0
    assert rec.baseline_cost_usd > 0.0
    assert rec.cost_savings_pct == 100.0
    assert rec.router_quality_score == 1.0
    assert rec.baseline_quality_score == 1.0
    assert rec.quality_delta == 0.0
