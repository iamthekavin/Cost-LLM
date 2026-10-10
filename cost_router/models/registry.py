"""
Model Registry: Central catalog of all available local and cloud LLM instances.
"""

from typing import Dict, List, Optional
from cost_router.config import ModelTier, MODEL_PRICING, TIER_DEFAULT_MODELS
from cost_router.models.base import BaseLLMClient
from cost_router.models.ollama_client import OllamaClient
from cost_router.models.cloud_clients import CloudLLMClient


class ModelRegistry:
    """Registry maintaining active clients and capabilities for all model tiers."""

    def __init__(self):
        self._clients: Dict[str, BaseLLMClient] = {}
        self._initialize_defaults()

    def _initialize_defaults(self):
        # Tier 1: Local Ollama
        self.register_client(OllamaClient("llama3.2:3b"))

        # Tier 2: Low-cost cloud
        self.register_client(CloudLLMClient("gpt-4o-mini", ModelTier.CHEAP))
        self.register_client(CloudLLMClient("claude-3-5-haiku", ModelTier.CHEAP))

        # Tier 3: Balanced cloud
        self.register_client(CloudLLMClient("gpt-4o", ModelTier.BALANCED))
        self.register_client(CloudLLMClient("claude-3-5-sonnet", ModelTier.BALANCED))

        # Tier 4: Frontier cloud
        self.register_client(CloudLLMClient("o1-preview", ModelTier.FRONTIER))

    def register_client(self, client: BaseLLMClient):
        self._clients[client.model_name] = client

    def get_client(self, model_name: str) -> Optional[BaseLLMClient]:
        return self._clients.get(model_name)

    def get_tier_client(self, tier: ModelTier) -> BaseLLMClient:
        default_model = TIER_DEFAULT_MODELS.get(tier, "llama3.2:3b")
        client = self.get_client(default_model)
        if not client:
            # Fallback to local
            return self.get_client("llama3.2:3b")
        return client

    def list_models_info(self) -> List[dict]:
        results = []
        for name, client in self._clients.items():
            pricing = MODEL_PRICING.get(name)
            results.append({
                "model_name": name,
                "tier": client.tier.value,
                "prompt_cost_per_1m": pricing.prompt_per_1m if pricing else 0.0,
                "completion_cost_per_1m": pricing.completion_per_1m if pricing else 0.0,
                "estimated_latency_ms": pricing.estimated_latency_ms if pricing else 0,
                "description": pricing.description if pricing else "",
                "is_local": client.tier == ModelTier.LOCAL,
            })
        return results


# Global singleton registry
global_registry = ModelRegistry()
