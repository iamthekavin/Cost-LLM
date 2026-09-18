"""Configuration and Model Registry Loader for Cost-LLM Model Gateway."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class ModelPricingSpec(BaseModel):
    tier: str = Field(..., description="Model tier: local, cheap, premium")
    provider: str = Field(..., description="Provider: ollama, openai, anthropic, google")
    context_window: int = Field(default=128000)
    cost_per_1m_in: float = Field(default=0.0)
    cost_per_1m_out: float = Field(default=0.0)
    default_timeout_s: float = Field(default=30.0)
    aliases: list[str] = Field(default_factory=list)


class GatewaySettings:
    def __init__(self):
        # Environment variables
        self.ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.default_local_model: str = os.getenv("DEFAULT_LOCAL_MODEL", "llama3.1:8b")
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self.gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")

        self.openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.anthropic_base_url: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1").rstrip("/")
        self.gemini_base_url: str = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        self.mock_hosted: bool = os.getenv("MOCK_HOSTED", "true").lower() in ("1", "true", "yes")

        self.gateway_port: int = int(os.getenv("GATEWAY_PORT", "8002"))
        self.gateway_host: str = os.getenv("GATEWAY_HOST", "0.0.0.0")
        self.default_hosted_timeout: float = float(os.getenv("DEFAULT_HOSTED_TIMEOUT_SECONDS", "30.0"))
        self.default_local_timeout: float = float(os.getenv("DEFAULT_LOCAL_TIMEOUT_SECONDS", "60.0"))
        self.max_hosted_retries: int = int(os.getenv("MAX_HOSTED_RETRIES", "2"))
        self.retry_initial_delay: float = float(os.getenv("RETRY_INITIAL_DELAY_SECONDS", "0.5"))

        # Load models.yaml registry
        self.models: Dict[str, ModelPricingSpec] = {}
        self.alias_map: Dict[str, str] = {}
        self._load_registry()

    def _load_registry(self):
        # Single canonical registry path: shared/models.yaml
        search_paths = [
            Path(__file__).resolve().parent.parent.parent / "shared" / "models.yaml",
            Path("shared/models.yaml"),
        ]

        loaded_data: Optional[Dict[str, Any]] = None
        for p in search_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        loaded_data = yaml.safe_load(f)
                    if loaded_data and "models" in loaded_data:
                        break
                except Exception:
                    continue

        if not loaded_data or "models" not in loaded_data:
            # Fallback hardcoded defaults if files missing
            loaded_data = {
                "models": {
                    "llama3.1:8b": {
                        "tier": "local",
                        "provider": "ollama",
                        "cost_per_1m_in": 0.0,
                        "cost_per_1m_out": 0.0,
                    },
                    "gpt-4o-mini": {
                        "tier": "cheap",
                        "provider": "openai",
                        "cost_per_1m_in": 0.15,
                        "cost_per_1m_out": 0.60,
                    },
                    "gpt-4o": {
                        "tier": "premium",
                        "provider": "openai",
                        "cost_per_1m_in": 2.50,
                        "cost_per_1m_out": 10.00,
                    },
                }
            }

        for model_id, spec_dict in loaded_data.get("models", {}).items():
            spec = ModelPricingSpec(**spec_dict)
            self.models[model_id] = spec
            self.alias_map[model_id.lower()] = model_id
            for alias in spec.aliases:
                self.alias_map[alias.lower()] = model_id

    def resolve_model_name(self, model_name: str) -> str:
        """Resolve model alias or return normalized model id."""
        key = model_name.strip().lower()
        return self.alias_map.get(key, model_name.strip())

    def get_model_spec(self, model_name: str) -> Optional[ModelPricingSpec]:
        resolved = self.resolve_model_name(model_name)
        return self.models.get(resolved)

    def calculate_cost(self, model_name: str, tokens_in: int, tokens_out: int) -> float:
        """Calculate execution cost in USD with 6-decimal floating point precision."""
        spec = self.get_model_spec(model_name)
        if not spec or spec.tier == "local":
            return 0.000000

        cost_in = (tokens_in / 1_000_000.0) * spec.cost_per_1m_in
        cost_out = (tokens_out / 1_000_000.0) * spec.cost_per_1m_out
        return round(cost_in + cost_out, 6)


settings = GatewaySettings()
