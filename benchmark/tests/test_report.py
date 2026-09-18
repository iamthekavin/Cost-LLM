"""Tests for Report Generator and Math Calculations (Member D)."""
import os
import tempfile

from benchmark.report import (
    aggregate_tier_metrics,
    calculate_cost_savings_pct,
    calculate_quality_delta,
    generate_failure_cases_markdown,
    generate_report_markdown,
    identify_regressions,
)


def test_calculate_cost_savings_pct():
    """Verify cost savings percentage formula and boundary edge cases."""
    # 50% savings
    assert calculate_cost_savings_pct(0.005, 0.010) == 50.0
    # 100% savings (local model $0.00)
    assert calculate_cost_savings_pct(0.000, 0.010) == 100.0
    # 0% savings (same cost)
    assert calculate_cost_savings_pct(0.010, 0.010) == 0.0
    # Negative savings (router cost more)
    assert calculate_cost_savings_pct(0.015, 0.010) == -50.0
    # Baseline is zero
    assert calculate_cost_savings_pct(0.000, 0.000) == 0.0


def test_calculate_quality_delta():
    """Verify quality delta formula."""
    assert calculate_quality_delta(0.95, 0.98) == -0.03
    assert calculate_quality_delta(1.0, 1.0) == 0.0
    assert calculate_quality_delta(0.99, 0.90) == 0.09


def test_aggregate_tier_metrics():
    """Verify metrics aggregation by difficulty tier."""
    sample_records = [
        {
            "expected_difficulty": "trivial",
            "router_cost_usd": 0.0,
            "baseline_cost_usd": 0.002,
            "router_quality_score": 1.0,
            "baseline_quality_score": 1.0,
            "router_latency_ms": 150.0,
            "baseline_latency_ms": 1000.0,
        },
        {
            "expected_difficulty": "moderate",
            "router_cost_usd": 0.0005,
            "baseline_cost_usd": 0.005,
            "router_quality_score": 0.95,
            "baseline_quality_score": 0.95,
            "router_latency_ms": 350.0,
            "baseline_latency_ms": 1100.0,
        },
        {
            "expected_difficulty": "deep",
            "router_cost_usd": 0.008,
            "baseline_cost_usd": 0.010,
            "router_quality_score": 0.90,
            "baseline_quality_score": 0.98,
            "router_latency_ms": 1050.0,
            "baseline_latency_ms": 1200.0,
        },
    ]

    tier_summary = aggregate_tier_metrics(sample_records)
    assert tier_summary["trivial"]["count"] == 1
    assert tier_summary["trivial"]["savings_pct"] == 100.0
    assert tier_summary["moderate"]["savings_pct"] == 90.0
    assert tier_summary["deep"]["savings_pct"] == 20.0
    assert tier_summary["deep"]["quality_delta"] == -0.08


def test_identify_regressions():
    """Verify regression detection flags tasks with significant quality drop."""
    records = [
        {"task_id": "t1", "quality_delta": 0.0},
        {"task_id": "t2", "quality_delta": -0.02},  # minor noise, not regression
        {"task_id": "t3", "quality_delta": -0.25},  # regression
        {"task_id": "t4", "quality_delta": -0.80},  # severe regression
    ]
    regs = identify_regressions(records, delta_threshold=-0.05)
    assert len(regs) == 2
    assert regs[0]["task_id"] == "t4"  # sorted by most negative first
    assert regs[1]["task_id"] == "t3"


def test_markdown_generators():
    """Verify report and failure cases generation produce valid files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = os.path.join(tmp_dir, "REPORT.md")
        fc_path = os.path.join(tmp_dir, "FAILURE_CASES.md")

        summary = {
            "total_tasks": 10,
            "total_router_cost_usd": 0.002,
            "total_baseline_cost_usd": 0.010,
            "overall_savings_pct": 80.0,
            "avg_router_quality": 0.95,
            "avg_baseline_quality": 0.98,
            "overall_quality_delta": -0.03,
            "avg_router_latency_ms": 300.0,
            "avg_baseline_latency_ms": 1100.0,
        }
        tier_summary = {
            "trivial": {"count": 4, "savings_pct": 100.0, "avg_router_quality": 1.0, "avg_baseline_quality": 1.0, "quality_delta": 0.0, "router_cost_usd": 0.0, "baseline_cost_usd": 0.002, "avg_router_latency_ms": 150.0, "avg_baseline_latency_ms": 1000.0},
            "moderate": {"count": 3, "savings_pct": 85.0, "avg_router_quality": 0.95, "avg_baseline_quality": 0.95, "quality_delta": 0.0, "router_cost_usd": 0.0003, "baseline_cost_usd": 0.002, "avg_router_latency_ms": 350.0, "avg_baseline_latency_ms": 1100.0},
            "deep": {"count": 3, "savings_pct": 10.0, "avg_router_quality": 0.90, "avg_baseline_quality": 0.98, "quality_delta": -0.08, "router_cost_usd": 0.0017, "baseline_cost_usd": 0.006, "avg_router_latency_ms": 1050.0, "avg_baseline_latency_ms": 1200.0},
        }
        cat_summary = {
            "math": {"count": 3, "savings_pct": 20.0, "avg_router_quality": 0.90, "avg_baseline_quality": 0.95, "quality_delta": -0.05, "router_cost_usd": 0.001, "baseline_cost_usd": 0.002},
        }
        regressions = [
            {
                "task_id": "math_01",
                "task_category": "math",
                "expected_difficulty": "deep",
                "router_model": "gpt-4o-mini",
                "baseline_model": "gpt-4o",
                "router_quality_score": 0.0,
                "baseline_quality_score": 1.0,
                "quality_delta": -1.0,
                "router_cost_usd": 0.0001,
                "baseline_cost_usd": 0.001,
                "prompt": "Solve complex problem",
                "router_output": "Wrong answer",
                "baseline_output": "Correct answer",
            }
        ]

        r_md = generate_report_markdown(summary, tier_summary, cat_summary, regressions, report_path)
        assert "# Cost-LLM Benchmark Evaluation Report" in r_md
        assert os.path.exists(report_path)

        fc_md = generate_failure_cases_markdown(regressions, fc_path)
        assert "# Cost-LLM Benchmark: Failure Cases" in fc_md
        assert "math_01" in fc_md
        assert os.path.exists(fc_path)
