"""Tests verifying concurrent batch calling vs sequential execution."""

import asyncio
import time
from unittest.mock import patch

import pytest
from model_gateway.router import execute_batch_concurrently

from shared.schemas.contracts import ModelCallResult


@pytest.mark.asyncio
async def test_concurrent_batch_latency_vs_sequential():
    """
    Verify that executing N subtasks in batch runs concurrently via asyncio.gather.
    Each task sleeps 0.1s.
    Sequential: 3 * 0.1s = ~0.30s.
    Concurrent: max(0.1s) = ~0.10s.
    """
    async def mock_delayed_call(*args, **kwargs):
        await asyncio.sleep(0.1)
        subtask_id = kwargs.get("subtask_id", "sub-0")
        return ModelCallResult(
            subtask_id=subtask_id,
            model_used="llama3.1:8b",
            tokens_in=10,
            tokens_out=20,
            latency_ms=100.0,
            cost_usd=0.0,
            raw_output=f"Output for {subtask_id}",
            error=None,
        )

    batch_items = [
        {"subtask_id": f"sub-{i}", "subtask_text": f"Prompt {i}", "chosen_model": "llama3.1:8b"}
        for i in range(3)
    ]

    with patch("model_gateway.providers.local_ollama.LocalOllamaProvider.call", side_effect=mock_delayed_call):
        start_concurrent = time.perf_counter()
        results = await execute_batch_concurrently(batch_items)
        elapsed_concurrent = time.perf_counter() - start_concurrent

        assert len(results) == 3
        for i, res in enumerate(results):
            assert res.subtask_id == f"sub-{i}"
            assert res.error is None

        # Concurrency check: elapsed time should be well below sequential time (0.3s)
        assert elapsed_concurrent < 0.25, f"Expected concurrent execution < 0.25s, got {elapsed_concurrent:.3f}s"
