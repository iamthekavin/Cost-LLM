"""Unit tests verifying cost calculation matches pricing.yaml specifications."""

import pytest
from model_gateway.config import settings


def test_local_model_pricing_zero():
    cost = settings.calculate_cost("llama3.1:8b", tokens_in=50000, tokens_out=50000)
    assert cost == 0.000000

    # Test alias
    cost_alias = settings.calculate_cost("llama3.1", tokens_in=10000, tokens_out=10000)
    assert cost_alias == 0.000000


def test_gpt_4o_mini_pricing():
    # gpt-4o-mini: $0.15 / 1M in, $0.60 / 1M out
    # 100,000 in -> 0.015 USD
    # 50,000 out -> 0.030 USD
    # Total = 0.045000 USD
    cost = settings.calculate_cost("gpt-4o-mini", tokens_in=100000, tokens_out=50000)
    assert cost == pytest.approx(0.045000, abs=1e-6)


def test_gemini_flash_pricing():
    # gemini-1.5-flash: $0.075 / 1M in, $0.30 / 1M out
    # 1,000,000 in -> 0.075 USD
    # 1,000,000 out -> 0.300 USD
    # Total = 0.375000 USD
    cost = settings.calculate_cost("gemini-1.5-flash", tokens_in=1000000, tokens_out=1000000)
    assert cost == pytest.approx(0.375000, abs=1e-6)


def test_claude_haiku_pricing():
    # claude-3-5-haiku: $0.80 / 1M in, $4.00 / 1M out
    # 10,000 in -> 0.008 USD
    # 5,000 out -> 0.020 USD
    # Total = 0.028000 USD
    cost = settings.calculate_cost("claude-3-5-haiku", tokens_in=10000, tokens_out=5000)
    assert cost == pytest.approx(0.028000, abs=1e-6)


def test_gpt_4o_baseline_pricing():
    # gpt-4o: $2.50 / 1M in, $10.00 / 1M out
    # 10,000 in -> 0.025 USD
    # 2,000 out -> 0.020 USD
    # Total = 0.045000 USD
    cost = settings.calculate_cost("gpt-4o", tokens_in=10000, tokens_out=2000)
    assert cost == pytest.approx(0.045000, abs=1e-6)


def test_claude_sonnet_pricing():
    # claude-3-5-sonnet: $3.00 / 1M in, $15.00 / 1M out
    # 100,000 in -> 0.300 USD
    # 20,000 out -> 0.300 USD
    # Total = 0.600000 USD
    cost = settings.calculate_cost("claude-3-5-sonnet", tokens_in=100000, tokens_out=20000)
    assert cost == pytest.approx(0.600000, abs=1e-6)


def test_gemini_pro_pricing():
    # gemini-1.5-pro: $1.25 / 1M in, $5.00 / 1M out
    # 100,000 in -> 0.125 USD
    # 10,000 out -> 0.050 USD
    # Total = 0.175000 USD
    cost = settings.calculate_cost("gemini-1.5-pro", tokens_in=100000, tokens_out=10000)
    assert cost == pytest.approx(0.175000, abs=1e-6)
