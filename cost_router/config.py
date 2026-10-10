"""
Configuration settings, pricing tables, model tiers, and routing policies.
"""

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class ModelTier(str, Enum):
    LOCAL = "local"          # Tier 1: Local Ollama (llama3.2:3b), $0 compute cost
    CHEAP = "cheap"          # Tier 2: Low-cost cloud (gpt-4o-mini, haiku)
    BALANCED = "balanced"    # Tier 3: Balanced cloud (gpt-4o, sonnet)
    FRONTIER = "frontier"    # Tier 4: Frontier reasoning (o1-preview, opus)


class RoutingPolicy(str, Enum):
    BALANCED = "balanced"          # Pareto-optimal: High cost savings (~75-85%) with ~98% quality
    COST_FIRST = "cost_first"      # Max savings: aggressive routing to local and cheap models
    QUALITY_FIRST = "quality_first"# High performance: only simple formatting goes to cheap/local
    LOCAL_ONLY = "local_only"      # 100% routed to local model (air-gapped/privacy-preserving)
    MANUAL = "manual"              # Explicit administrative override to a specified model


class PricingInfo(BaseModel):
    prompt_per_1m: float      # USD per 1M prompt/input tokens
    completion_per_1m: float  # USD per 1M completion/output tokens
    estimated_latency_ms: int # Baseline latency estimate
    description: str


# Real-world reference pricing table per 1M tokens (USD)
MODEL_PRICING: Dict[str, PricingInfo] = {
    # Tier 1: Local
    "llama3.2:3b": PricingInfo(
        prompt_per_1m=0.00,
        completion_per_1m=0.00,
        estimated_latency_ms=450,
        description="Local Llama 3.2 3B (Ollama on local machine) - Zero API Cost, Air-gapped"
    ),
    # Tier 2: Cheap
    "gpt-4o-mini": PricingInfo(
        prompt_per_1m=0.15,
        completion_per_1m=0.60,
        estimated_latency_ms=520,
        description="OpenAI GPT-4o-mini - Fast, efficient, high throughput"
    ),
    "claude-3-5-haiku": PricingInfo(
        prompt_per_1m=0.25,
        completion_per_1m=1.25,
        estimated_latency_ms=480,
        description="Anthropic Claude 3.5 Haiku - High speed, low cost"
    ),
    # Tier 3: Balanced
    "gpt-4o": PricingInfo(
        prompt_per_1m=2.50,
        completion_per_1m=10.00,
        estimated_latency_ms=850,
        description="OpenAI GPT-4o - Strong multimodal general intelligence"
    ),
    "claude-3-5-sonnet": PricingInfo(
        prompt_per_1m=3.00,
        completion_per_1m=15.00,
        estimated_latency_ms=920,
        description="Anthropic Claude 3.5 Sonnet - Top-tier coding and synthesis"
    ),
    # Tier 4: Frontier
    "o1-preview": PricingInfo(
        prompt_per_1m=15.00,
        completion_per_1m=60.00,
        estimated_latency_ms=3200,
        description="OpenAI o1-preview - Deep multi-step reasoning and logical deduction"
    ),
}

# Default model associated with each tier
TIER_DEFAULT_MODELS: Dict[ModelTier, str] = {
    ModelTier.LOCAL: "llama3.2:3b",
    ModelTier.CHEAP: "gpt-4o-mini",
    ModelTier.BALANCED: "gpt-4o",
    ModelTier.FRONTIER: "o1-preview",
}

# Threshold configuration for routing policies based on complexity score in [0.0, 1.0]
# [local_max, cheap_max, balanced_max]
# Complexity < local_max -> LOCAL
# Complexity < cheap_max -> CHEAP
# Complexity < balanced_max -> BALANCED
# Complexity >= balanced_max -> FRONTIER
POLICY_THRESHOLDS: Dict[RoutingPolicy, Dict[str, float]] = {
    RoutingPolicy.BALANCED: {
        "local_max": 0.25,
        "cheap_max": 0.60,
        "balanced_max": 0.85,
    },
    RoutingPolicy.COST_FIRST: {
        "local_max": 0.45,
        "cheap_max": 0.75,
        "balanced_max": 0.92,
    },
    RoutingPolicy.QUALITY_FIRST: {
        "local_max": 0.15,
        "cheap_max": 0.40,
        "balanced_max": 0.70,
    },
    RoutingPolicy.LOCAL_ONLY: {
        "local_max": 1.01, # everything routes local
        "cheap_max": 1.01,
        "balanced_max": 1.01,
    },
}


class RouterConfig(BaseModel):
    """Runtime configuration for the router."""
    default_policy: RoutingPolicy = Field(default=RoutingPolicy.BALANCED)
    baseline_model: str = Field(default="o1-preview") # Baseline for measuring cost reduction
    ollama_base_url: str = Field(default="http://127.0.0.1:11434")
    enable_auto_decomposition: bool = Field(default=True)
    decomposition_complexity_threshold: float = Field(default=0.40)
    allow_admin_override: bool = Field(default=True)
    simulation_mode: bool = Field(default=False) # If True, simulates LLMs without external calls
    custom_thresholds: Optional[Dict[str, float]] = None


# Singleton configuration instance
global_config = RouterConfig()
