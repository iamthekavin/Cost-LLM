"""
Unit tests for Token Counting and Cost Accounting calculations.
"""

from cost_router.models.base import calculate_cost, calculate_savings


def test_zero_cost_for_local_model():
    # llama3.2:3b runs on local hardware at $0 API cost
    cost = calculate_cost("llama3.2:3b", prompt_tokens=5000, completion_tokens=2000)
    assert cost == 0.0


def test_accurate_pricing_gpt4o_mini():
    # gpt-4o-mini is $0.15/1M prompt, $0.60/1M completion
    # 1,000,000 prompt tokens = $0.15
    # 1,000,000 completion tokens = $0.60
    cost = calculate_cost("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost == 0.75


def test_accurate_pricing_frontier():
    # o1-preview is $15.00/1M prompt, $60.00/1M completion
    cost = calculate_cost("o1-preview", prompt_tokens=100_000, completion_tokens=50_000)
    # (100_000 / 1e6) * 15.00 = 1.50
    # (50_000 / 1e6) * 60.00 = 3.00
    # Total = 4.50
    assert cost == 4.50


def test_savings_calculation():
    actual = 0.50
    baseline = 5.00
    savings, pct = calculate_savings(actual, baseline)
    assert savings == 4.50
    assert pct == 90.0


def test_zero_baseline_savings():
    savings, pct = calculate_savings(0.0, 0.0)
    assert savings == 0.0
    assert pct == 0.0
