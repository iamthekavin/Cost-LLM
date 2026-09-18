"""Unit tests for retries and fallback_model handling in router."""

from unittest.mock import AsyncMock, patch

import pytest
from model_gateway.router import execute_call

from shared.schemas.contracts import ModelCallResult


@pytest.mark.asyncio
async def test_fallback_triggered_when_primary_fails():
    fail_result = ModelCallResult(
        subtask_id="sub-fallback-1",
        model_used="llama3.1:8b",
        tokens_in=10,
        tokens_out=0,
        latency_ms=50.0,
        cost_usd=0.0,
        raw_output="",
        error="Ollama connection refused",
    )
    fallback_success = ModelCallResult(
        subtask_id="sub-fallback-1",
        model_used="gpt-4o-mini",
        tokens_in=15,
        tokens_out=30,
        latency_ms=180.0,
        cost_usd=0.000020,
        raw_output="Fallback recovered answer",
        error=None,
    )

    with patch("model_gateway.providers.local_ollama.LocalOllamaProvider.call", new_callable=AsyncMock) as mock_primary, \
         patch("model_gateway.providers.cheap_hosted.CheapHostedProvider.call", new_callable=AsyncMock) as mock_fallback:
        mock_primary.return_value = fail_result
        mock_fallback.return_value = fallback_success

        result = await execute_call(
            subtask_id="sub-fallback-1",
            prompt="Hello",
            chosen_model="llama3.1:8b",
            fallback_model="gpt-4o-mini",
        )

        assert result.subtask_id == "sub-fallback-1"
        assert result.error is None
        assert "fallback from llama3.1:8b" in result.model_used
        assert result.raw_output == "Fallback recovered answer"
        mock_primary.assert_called_once()
        mock_fallback.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_both_fail():
    fail_primary = ModelCallResult(
        subtask_id="sub-fb-2",
        model_used="llama3.1:8b",
        tokens_in=0,
        tokens_out=0,
        latency_ms=10.0,
        cost_usd=0.0,
        raw_output="",
        error="Daemon dead",
    )
    fail_fallback = ModelCallResult(
        subtask_id="sub-fb-2",
        model_used="gpt-4o-mini",
        tokens_in=0,
        tokens_out=0,
        latency_ms=20.0,
        cost_usd=0.0,
        raw_output="",
        error="Rate limit exceeded",
    )

    with patch("model_gateway.providers.local_ollama.LocalOllamaProvider.call", new_callable=AsyncMock) as mock_primary, \
         patch("model_gateway.providers.cheap_hosted.CheapHostedProvider.call", new_callable=AsyncMock) as mock_fallback:
        mock_primary.return_value = fail_primary
        mock_fallback.return_value = fail_fallback

        result = await execute_call(
            subtask_id="sub-fb-2",
            prompt="Hello",
            chosen_model="llama3.1:8b",
            fallback_model="gpt-4o-mini",
        )

        assert result.error is not None
        assert "Daemon dead" in result.error
        assert "Rate limit exceeded" in result.error
        assert "failed fallback" in result.model_used


@pytest.mark.asyncio
async def test_retry_success_on_second_attempt():
    fail_first = ModelCallResult(
        subtask_id="sub-retry-1",
        model_used="gpt-4o-mini",
        tokens_in=0,
        tokens_out=0,
        latency_ms=15.0,
        cost_usd=0.0,
        raw_output="",
        error="HTTP 502 Bad Gateway",
    )
    success_second = ModelCallResult(
        subtask_id="sub-retry-1",
        model_used="gpt-4o-mini",
        tokens_in=25,
        tokens_out=40,
        latency_ms=190.0,
        cost_usd=0.000028,
        raw_output="Success on retry",
        error=None,
    )

    with patch("model_gateway.providers.cheap_hosted.CheapHostedProvider.call", new_callable=AsyncMock) as mock_call, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        mock_call.side_effect = [fail_first, success_second]

        result = await execute_call(
            subtask_id="sub-retry-1",
            prompt="Hello",
            chosen_model="gpt-4o-mini",
            max_retries=2,
        )

        assert result.error is None
        assert result.raw_output == "Success on retry"
        assert mock_call.call_count == 2
