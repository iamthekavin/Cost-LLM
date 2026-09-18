"""Cheap / Mid-Tier Hosted Model Provider Adapter (Member B).

Handles small, cost-efficient hosted models (e.g. GPT-4o-mini, Claude 3.5 Haiku, Gemini 1.5 Flash).
Normalizes provider-specific API formats and calculates precise monetary cost from pricing.yaml.
"""

import time
from typing import Any, Optional

import httpx
from model_gateway.config import settings
from model_gateway.normalize import build_normalized_result, normalize_error_message
from model_gateway.providers.base import BaseProvider

from shared.schemas.contracts import ModelCallResult


class CheapHostedProvider(BaseProvider):
    """Adapter for cheap hosted models."""

    def __init__(self, model_name: str = "gpt-4o-mini"):
        super().__init__(model_name)
        self.provider = (self.spec.provider if self.spec else "openai").lower()

    def _get_api_key(self) -> Optional[str]:
        if self.provider == "anthropic":
            return settings.anthropic_api_key
        elif self.provider == "google":
            return settings.gemini_api_key
        return settings.openai_api_key

    async def call(
        self,
        prompt: str,
        subtask_id: str = "subtask_0",
        timeout_s: Optional[float] = None,
        **params: Any,
    ) -> ModelCallResult:
        timeout = timeout_s or (self.spec.default_timeout_s if self.spec else settings.default_hosted_timeout)
        api_key = self._get_api_key()

        start_time = time.perf_counter()

        if self.provider == "anthropic":
            return await self._call_anthropic(prompt, subtask_id, api_key, timeout, start_time, **params)
        elif self.provider == "google":
            return await self._call_gemini(prompt, subtask_id, api_key, timeout, start_time, **params)
        else:
            return await self._call_openai(prompt, subtask_id, api_key, timeout, start_time, **params)

    async def _call_openai(
        self, prompt: str, subtask_id: str, api_key: Optional[str], timeout: float, start_time: float, **params: Any
    ) -> ModelCallResult:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key or 'mock-key'}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": params.get("temperature", 0.7),
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(url, json=payload, headers=headers)
                latency_ms = (time.perf_counter() - start_time) * 1000.0

                if res.status_code != 200:
                    return build_normalized_result(
                        subtask_id=subtask_id,
                        model_used=self.model_name,
                        tokens_in=self.estimate_tokens(prompt),
                        tokens_out=0,
                        latency_ms=latency_ms,
                        cost_usd=0.0,
                        raw_output="",
                        error=f"OpenAI HTTP {res.status_code}: {res.text}",
                    )

                data = res.json()
                raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                tokens_in = usage.get("prompt_tokens") or self.estimate_tokens(prompt)
                tokens_out = usage.get("completion_tokens") or self.estimate_tokens(raw_text)
                cost = self.compute_cost(tokens_in, tokens_out)

                return build_normalized_result(
                    subtask_id=subtask_id,
                    model_used=self.model_name,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                    raw_output=raw_text,
                )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return build_normalized_result(
                subtask_id=subtask_id,
                model_used=self.model_name,
                tokens_in=self.estimate_tokens(prompt),
                tokens_out=0,
                latency_ms=latency_ms,
                cost_usd=0.0,
                raw_output="",
                error=normalize_error_message(exc),
            )

    async def _call_anthropic(
        self, prompt: str, subtask_id: str, api_key: Optional[str], timeout: float, start_time: float, **params: Any
    ) -> ModelCallResult:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key or "mock-key",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "max_tokens": params.get("max_tokens", 1024),
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(url, json=payload, headers=headers)
                latency_ms = (time.perf_counter() - start_time) * 1000.0

                if res.status_code != 200:
                    return build_normalized_result(
                        subtask_id=subtask_id,
                        model_used=self.model_name,
                        tokens_in=self.estimate_tokens(prompt),
                        tokens_out=0,
                        latency_ms=latency_ms,
                        cost_usd=0.0,
                        raw_output="",
                        error=f"Anthropic HTTP {res.status_code}: {res.text}",
                    )

                data = res.json()
                content_blocks = data.get("content", [])
                raw_text = "".join([c.get("text", "") for c in content_blocks if c.get("type") == "text"])
                usage = data.get("usage", {})
                tokens_in = usage.get("input_tokens") or self.estimate_tokens(prompt)
                tokens_out = usage.get("output_tokens") or self.estimate_tokens(raw_text)
                cost = self.compute_cost(tokens_in, tokens_out)

                return build_normalized_result(
                    subtask_id=subtask_id,
                    model_used=self.model_name,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                    raw_output=raw_text,
                )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return build_normalized_result(
                subtask_id=subtask_id,
                model_used=self.model_name,
                tokens_in=self.estimate_tokens(prompt),
                tokens_out=0,
                latency_ms=latency_ms,
                cost_usd=0.0,
                raw_output="",
                error=normalize_error_message(exc),
            )

    async def _call_gemini(
        self, prompt: str, subtask_id: str, api_key: Optional[str], timeout: float, start_time: float, **params: Any
    ) -> ModelCallResult:
        key = api_key or "mock-key"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": params.get("temperature", 0.7)},
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(url, json=payload)
                latency_ms = (time.perf_counter() - start_time) * 1000.0

                if res.status_code != 200:
                    return build_normalized_result(
                        subtask_id=subtask_id,
                        model_used=self.model_name,
                        tokens_in=self.estimate_tokens(prompt),
                        tokens_out=0,
                        latency_ms=latency_ms,
                        cost_usd=0.0,
                        raw_output="",
                        error=f"Google Gemini HTTP {res.status_code}: {res.text}",
                    )

                data = res.json()
                candidates = data.get("candidates", [{}])
                parts = candidates[0].get("content", {}).get("parts", [])
                raw_text = "".join([p.get("text", "") for p in parts])
                usage = data.get("usageMetadata", {})
                tokens_in = usage.get("promptTokenCount") or self.estimate_tokens(prompt)
                tokens_out = usage.get("candidatesTokenCount") or self.estimate_tokens(raw_text)
                cost = self.compute_cost(tokens_in, tokens_out)

                return build_normalized_result(
                    subtask_id=subtask_id,
                    model_used=self.model_name,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                    raw_output=raw_text,
                )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return build_normalized_result(
                subtask_id=subtask_id,
                model_used=self.model_name,
                tokens_in=self.estimate_tokens(prompt),
                tokens_out=0,
                latency_ms=latency_ms,
                cost_usd=0.0,
                raw_output="",
                error=normalize_error_message(exc),
            )
