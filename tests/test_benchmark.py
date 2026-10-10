"""
Unit tests for Benchmarking and Trade-Off Evaluation.
"""

import pytest
from cost_router.benchmark.dataset import BENCHMARK_SUITE
from cost_router.benchmark.evaluator import BenchmarkEvaluator
from cost_router.benchmark.runner import BenchmarkRunner
from cost_router.router.engine import RoutingEngine


@pytest.mark.asyncio
async def test_benchmark_runner_subset():
    engine = RoutingEngine()
    runner = BenchmarkRunner(engine)

    # Run on first 3 benchmark items for rapid verification
    sample_items = BENCHMARK_SUITE[:3]
    results = await runner.run_full_benchmark(sample_items)

    assert "summary_by_strategy" in results
    assert "pareto_trade_off_points" in results
    assert len(results["pareto_trade_off_points"]) == 4

    # Compare Dynamic Router cost against Always Frontier
    dyn_summary = results["summary_by_strategy"]["dynamic_router"]
    frontier_summary = results["summary_by_strategy"]["always_frontier"]

    assert dyn_summary["total_cost_usd"] < frontier_summary["total_cost_usd"]
    assert dyn_summary["cost_reduction_pct"] > 50.0
    assert dyn_summary["avg_quality_score"] >= 70.0
