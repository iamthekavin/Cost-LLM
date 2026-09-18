"""Local Ollama Provider Adapter (Member B).

Connects to a local Ollama instance (e.g. running Llama 3.1 8B).
Extracts prompt_eval_count and eval_count for token accuracy.
Enforces zero marginal cost ($0.00).
"""

import time
from typing import Any, Dict, Optional

import httpx
from model_gateway.config import settings
from model_gateway.normalize import build_normalized_result, normalize_error_message
from model_gateway.providers.base import BaseProvider

from shared.schemas.contracts import ModelCallResult


class LocalOllamaProvider(BaseProvider):
    """Adapter for self-hosted local models running under Ollama."""

    def __init__(self, model_name: str = "llama3.1:8b", base_url: Optional[str] = None):
        super().__init__(model_name)
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")

    async def check_health(self, timeout_s: float = 3.0) -> Dict[str, Any]:
        """Query Ollama daemon /api/tags to confirm availability and loaded models."""
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=timeout_s) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    available_models = [m.get("name") for m in data.get("models", [])]
                    return {
                        "reachable": True,
                        "status_code": res.status_code,
                        "models": available_models,
                        "has_target_model": any(self.model_name in m for m in available_models),
                    }
                return {"reachable": False, "status_code": res.status_code}
        except Exception as e:
            return {"reachable": False, "error": normalize_error_message(e)}

    async def call(
        self,
        prompt: str,
        subtask_id: str = "subtask_0",
        timeout_s: Optional[float] = None,
        **params: Any,
    ) -> ModelCallResult:
        """Invoke Ollama /api/generate endpoint."""
        timeout = timeout_s or (self.spec.default_timeout_s if self.spec else settings.default_local_timeout)
        endpoint = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": params.get("temperature", 0.7),
            },
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(endpoint, json=payload)
                latency_ms = (time.perf_counter() - start_time) * 1000.0

                if response.status_code != 200:
                    error_msg = f"Ollama HTTP {response.status_code}: {response.text}"
                    return build_normalized_result(
                        subtask_id=subtask_id,
                        model_used=self.model_name,
                        tokens_in=self.estimate_tokens(prompt),
                        tokens_out=0,
                        latency_ms=latency_ms,
                        cost_usd=0.000000,
                        raw_output="",
                        error=error_msg,
                    )

                data = response.json()
                raw_text = data.get("response", "")
                tokens_in = data.get("prompt_eval_count") or self.estimate_tokens(prompt)
                tokens_out = data.get("eval_count") or self.estimate_tokens(raw_text)

                return build_normalized_result(
                    subtask_id=subtask_id,
                    model_used=self.model_name,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=latency_ms,
                    cost_usd=0.000000,  # Local tier strictly $0.00
                    raw_output=raw_text,
                    error=None,
                )

        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return build_normalized_result(
                subtask_id=subtask_id,
                model_used=self.model_name,
                tokens_in=self.estimate_tokens(prompt),
                tokens_out=0,
                latency_ms=latency_ms,
                cost_usd=0.000000,
                raw_output="",
                error=normalize_error_message(exc),
            )
