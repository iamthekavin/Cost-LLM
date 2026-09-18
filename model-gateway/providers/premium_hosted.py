"""Premium / Frontier Hosted Model Provider Adapter (Member B).

Handles gold-standard frontier reasoning models:
- OpenAI GPT-4o
- Anthropic Claude 3.5 Sonnet
- Google Gemini 1.5 Pro

This adapter serves as the objective "always-strongest" baseline against which
Member D (Benchmark) evaluates financial savings and quality preservation.
"""

from typing import Any, Optional

from model_gateway.providers.cheap_hosted import CheapHostedProvider

from shared.schemas.contracts import ModelCallResult


class PremiumHostedProvider(CheapHostedProvider):
    """Adapter for premium hosted models (inherits multi-provider dispatch with premium specs)."""

    def __init__(self, model_name: str = "gpt-4o"):
        super().__init__(model_name)

    async def call(
        self,
        prompt: str,
        subtask_id: str = "subtask_0",
        timeout_s: Optional[float] = None,
        **params: Any,
    ) -> ModelCallResult:
        """Call premium provider with premium timeout and pricing."""
        # Ensure default max_tokens is generous for frontier answers
        if "max_tokens" not in params:
            params["max_tokens"] = 2048

        return await super().call(prompt, subtask_id=subtask_id, timeout_s=timeout_s, **params)
