"""Base Provider Interface for Cost-LLM Model Gateway."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from model_gateway.config import settings

from shared.schemas.contracts import ModelCallResult


class BaseProvider(ABC):
    """Abstract base class that all backend model adapters must implement."""

    def __init__(self, model_name: str):
        self.model_name = settings.resolve_model_name(model_name)
        self.spec = settings.get_model_spec(self.model_name)

    @abstractmethod
    async def call(
        self,
        prompt: str,
        subtask_id: str = "subtask_0",
        timeout_s: Optional[float] = None,
        **params: Any,
    ) -> ModelCallResult:
        """
        Execute model invocation.
        Must return a standardized ModelCallResult with accurate token metrics, latency, and cost.
        """
        pass

    def estimate_tokens(self, text: str) -> int:
        """Heuristic fallback token estimation (~4 chars/token) if provider omits token counts."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def compute_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Compute execution cost in USD based on pricing registry."""
        return settings.calculate_cost(self.model_name, tokens_in, tokens_out)
