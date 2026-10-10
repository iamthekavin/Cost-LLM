"""
Base abstractions, data contracts, and response schemas for LLM execution.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from cost_router.config import ModelTier, RoutingPolicy, MODEL_PRICING


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class CostMetrics(BaseModel):
    prompt_cost_usd: float = 0.0
    completion_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    baseline_cost_usd: float = 0.0
    savings_usd: float = 0.0
    reduction_percentage: float = 0.0


class ModelResponse(BaseModel):
    text: str
    model_name: str
    tier: ModelTier
    usage: TokenUsage
    cost: CostMetrics
    latency_ms: float
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SubTaskPlan(BaseModel):
    id: int
    title: str
    prompt_chunk: str
    intent: str
    complexity_score: float
    selected_tier: ModelTier
    selected_model: str
    reasoning: str
    dependencies: List[int] = Field(default_factory=list)


class RoutingTrace(BaseModel):
    request_id: str
    original_prompt: str
    policy: RoutingPolicy
    overall_complexity: float
    detected_intent: str
    is_decomposed: bool
    is_override: bool
    override_reason: Optional[str] = None
    subtasks: List[SubTaskPlan] = Field(default_factory=list)
    explanation: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AggregatedResponse(BaseModel):
    request_id: str
    final_output: str
    trace: RoutingTrace
    total_latency_ms: float
    total_usage: TokenUsage
    cost_summary: CostMetrics
    subtask_results: List[ModelResponse] = Field(default_factory=list)


def calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculates cost in USD given model and token counts."""
    pricing = MODEL_PRICING.get(model_name)
    if not pricing:
        return 0.0
    prompt_cost = (prompt_tokens / 1_000_000.0) * pricing.prompt_per_1m
    completion_cost = (completion_tokens / 1_000_000.0) * pricing.completion_per_1m
    return round(prompt_cost + completion_cost, 6)


def calculate_savings(actual_cost: float, baseline_cost: float) -> tuple[float, float]:
    """Returns (savings_usd, reduction_percentage)."""
    savings = max(0.0, baseline_cost - actual_cost)
    pct = (savings / baseline_cost * 100.0) if baseline_cost > 0 else 0.0
    return round(savings, 6), round(pct, 2)


class BaseLLMClient(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, model_name: str, tier: ModelTier):
        self.model_name = model_name
        self.tier = tier

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> ModelResponse:
        """Generate response for given prompt."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider/model is reachable."""
        pass
