"""Dispatcher, Resilience, Retries, and Fallback Router (Member B)."""

import asyncio
from typing import Any, Dict, List, Optional

from model_gateway.config import settings
from model_gateway.normalize import build_normalized_result
from model_gateway.providers.base import BaseProvider
from model_gateway.providers.cheap_hosted import CheapHostedProvider
from model_gateway.providers.local_ollama import LocalOllamaProvider
from model_gateway.providers.premium_hosted import PremiumHostedProvider
from shared.schemas.contracts import ModelCallResult


def get_provider(model_name: str) -> BaseProvider:
    """Factory creating the appropriate provider adapter based on model registry tier."""
    resolved_name = settings.resolve_model_name(model_name)
    spec = settings.get_model_spec(resolved_name)

    if spec:
        if spec.tier == "local" or spec.provider == "ollama":
            return LocalOllamaProvider(resolved_name)
        elif spec.tier == "premium":
            return PremiumHostedProvider(resolved_name)
        else:
            return CheapHostedProvider(resolved_name)

    # If unlisted model, infer from name
    lower = resolved_name.lower()
    if "llama" in lower or "mistral" in lower or "ollama" in lower:
        return LocalOllamaProvider(resolved_name)
    elif "4o-mini" in lower or "haiku" in lower or "flash" in lower:
        return CheapHostedProvider(resolved_name)
    else:
        return PremiumHostedProvider(resolved_name)


async def execute_call(
    subtask_id: str,
    prompt: str,
    chosen_model: str,
    fallback_model: Optional[str] = None,
    timeout_s: Optional[float] = None,
    max_retries: Optional[int] = None,
    **params: Any,
) -> ModelCallResult:
    """
    Execute a subtask against chosen_model with timeouts, retries, and fallback handling.
    """
    provider = get_provider(chosen_model)
    retries = max_retries if max_retries is not None else (
        settings.max_hosted_retries if provider.spec and provider.spec.tier != "local" else 0
    )

    last_result: Optional[ModelCallResult] = None
    delay = settings.retry_initial_delay

    # Primary execution loop with retries
    for attempt in range(retries + 1):
        try:
            result = await provider.call(prompt, subtask_id=subtask_id, timeout_s=timeout_s, **params)
            if not result.error:
                return result

            last_result = result
        except Exception as e:
            last_result = build_normalized_result(
                subtask_id=subtask_id,
                model_used=chosen_model,
                tokens_in=0,
                tokens_out=0,
                latency_ms=0.0,
                cost_usd=0.0,
                raw_output="",
                error=f"Attempt {attempt + 1} failed: {str(e)}",
            )

        if attempt < retries:
            await asyncio.sleep(delay)
            delay *= 2.0

    # Primary model failed after all retries — check fallback path
    if fallback_model and fallback_model.strip() and fallback_model != chosen_model:
        fallback_provider = get_provider(fallback_model)
        try:
            fallback_res = await fallback_provider.call(
                prompt, subtask_id=subtask_id, timeout_s=timeout_s, **params
            )
            if not fallback_res.error:
                # Mark that fallback occurred in model_used description
                return ModelCallResult(
                    subtask_id=subtask_id,
                    model_used=f"{fallback_provider.model_name} (fallback from {chosen_model})",
                    tokens_in=fallback_res.tokens_in,
                    tokens_out=fallback_res.tokens_out,
                    latency_ms=fallback_res.latency_ms,
                    cost_usd=fallback_res.cost_usd,
                    raw_output=fallback_res.raw_output,
                    error=None,
                )
            # Fallback also failed
            combined_error = f"Primary [{chosen_model}] failed ({last_result.error if last_result else 'unknown'}), and fallback [{fallback_model}] failed ({fallback_res.error})"
            return ModelCallResult(
                subtask_id=subtask_id,
                model_used=f"{fallback_provider.model_name} (failed fallback)",
                tokens_in=fallback_res.tokens_in,
                tokens_out=fallback_res.tokens_out,
                latency_ms=fallback_res.latency_ms,
                cost_usd=fallback_res.cost_usd,
                raw_output="",
                error=combined_error,
            )
        except Exception as fb_exc:
            combined_error = f"Primary [{chosen_model}] failed ({last_result.error if last_result else 'unknown'}), and fallback exception: {str(fb_exc)}"
            return ModelCallResult(
                subtask_id=subtask_id,
                model_used=f"{fallback_model} (failed fallback)",
                tokens_in=0,
                tokens_out=0,
                latency_ms=last_result.latency_ms if last_result else 0.0,
                cost_usd=0.0,
                raw_output="",
                error=combined_error,
            )

    return last_result if last_result else build_normalized_result(
        subtask_id=subtask_id,
        model_used=chosen_model,
        tokens_in=0,
        tokens_out=0,
        latency_ms=0.0,
        cost_usd=0.0,
        raw_output="",
        error="Execution failed with no result returned",
    )


async def execute_batch_concurrently(items: List[Dict[str, Any]]) -> List[ModelCallResult]:
    """Execute multiple subtasks concurrently using asyncio.gather."""
    tasks = [
        execute_call(
            subtask_id=item.get("subtask_id", f"subtask_{i}"),
            prompt=item.get("subtask_text") or item.get("prompt", ""),
            chosen_model=item.get("chosen_model", "llama3.1:8b"),
            fallback_model=item.get("fallback_model"),
            timeout_s=item.get("timeout_s"),
            params=item.get("params", {}),
        )
        for i, item in enumerate(items)
    ]
    return await asyncio.gather(*tasks)
