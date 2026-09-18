"""Unit tests for Provider Adapters (Ollama, Cheap Hosted, Premium Hosted)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from model_gateway.providers.cheap_hosted import CheapHostedProvider
from model_gateway.providers.local_ollama import LocalOllamaProvider
from model_gateway.providers.premium_hosted import PremiumHostedProvider


@pytest.mark.asyncio
async def test_ollama_provider_success():
    provider = LocalOllamaProvider("llama3.1:8b")

    mock_resp = httpx.Response(
        status_code=200,
        json={
            "model": "llama3.1:8b",
            "response": "Hello world from local Ollama",
            "prompt_eval_count": 12,
            "eval_count": 35,
        },
        request=httpx.Request("POST", "http://localhost:11434/api/generate"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await provider.call("Say hello", subtask_id="sub-1")

        assert result.subtask_id == "sub-1"
        assert result.model_used == "llama3.1:8b"
        assert result.tokens_in == 12
        assert result.tokens_out == 35
        assert result.cost_usd == 0.000000  # Local model must be 0 cost
        assert "Hello world" in result.raw_output
        assert result.error is None


@pytest.mark.asyncio
async def test_ollama_provider_connection_error():
    provider = LocalOllamaProvider("llama3.1:8b")

    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Ollama offline")):
        result = await provider.call("Test prompt", subtask_id="sub-2")
        assert result.subtask_id == "sub-2"
        assert result.error is not None
        assert "ConnectError" in result.error
        assert result.cost_usd == 0.0


@pytest.mark.asyncio
async def test_cheap_hosted_openai_success():
    provider = CheapHostedProvider("gpt-4o-mini")

    mock_resp = httpx.Response(
        status_code=200,
        json={
            "choices": [{"message": {"content": "Sorted: [1, 2, 3]"}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20},
        },
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await provider.call("Sort [3, 1, 2]", subtask_id="sub-3")

        assert result.subtask_id == "sub-3"
        assert result.model_used == "gpt-4o-mini"
        assert result.tokens_in == 50
        assert result.tokens_out == 20
        assert result.raw_output == "Sorted: [1, 2, 3]"
        # Cost check: (50/1M * 0.15) + (20/1M * 0.60) = 0.0000075 + 0.000012 = 0.0000195 -> 0.000020
        assert result.cost_usd > 0.0
        assert result.error is None


@pytest.mark.asyncio
async def test_cheap_hosted_anthropic_success():
    provider = CheapHostedProvider("claude-3-5-haiku")

    mock_resp = httpx.Response(
        status_code=200,
        json={
            "content": [{"type": "text", "text": "Extracted key metrics"}],
            "usage": {"input_tokens": 100, "output_tokens": 40},
        },
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await provider.call("Extract metrics", subtask_id="sub-4")

        assert result.subtask_id == "sub-4"
        assert result.model_used == "claude-3-5-haiku"
        assert result.tokens_in == 100
        assert result.tokens_out == 40
        assert result.raw_output == "Extracted key metrics"
        assert result.cost_usd > 0.0


@pytest.mark.asyncio
async def test_premium_hosted_baseline_success():
    provider = PremiumHostedProvider("gpt-4o")

    mock_resp = httpx.Response(
        status_code=200,
        json={
            "choices": [{"message": {"content": "Deep mathematical proof completed."}}],
            "usage": {"prompt_tokens": 500, "completion_tokens": 200},
        },
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await provider.call("Prove theorem X", subtask_id="sub-5")

        assert result.subtask_id == "sub-5"
        assert result.model_used == "gpt-4o"
        assert result.tokens_in == 500
        assert result.tokens_out == 200
        # gpt-4o pricing: (500/1M * 2.50) + (200/1M * 10.00) = 0.00125 + 0.00200 = 0.00325
        assert result.cost_usd == pytest.approx(0.003250, abs=1e-6)
        assert result.error is None
