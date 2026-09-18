"""End-to-End Smoke Benchmark Test for CI (Member D)."""
import os
import tempfile

import pytest

from benchmark.runner import BenchmarkRunner


@pytest.mark.asyncio
async def test_smoke_benchmark_execution():
    """Fast sanity check running smoke tasks dataset (~10 tasks) in CI."""
    smoke_tasks_file = os.path.join(
        os.path.dirname(__file__), "..", "tasks", "smoke_tasks.jsonl"
    )
    assert os.path.exists(smoke_tasks_file)

    with tempfile.TemporaryDirectory() as tmp_dir:
        runner = BenchmarkRunner(force_mock=True)
        results = await runner.run_benchmark(
            tasks_path=smoke_tasks_file,
            output_dir=tmp_dir,
            push_control_plane=False,
        )

        assert results["summary"]["total_tasks"] == 10
        assert results["summary"]["overall_savings_pct"] > 0.0
        assert results["summary"]["avg_router_quality"] > 0.80
        assert len(results["records"]) == 10

        # Assert output artifacts were generated
        latest_json = os.path.join(tmp_dir, "latest.json")
        assert os.path.exists(latest_json)
