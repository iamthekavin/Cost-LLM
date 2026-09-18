"""Model Gateway FastAPI Application (Member B)."""
from fastapi import FastAPI

from shared.schemas.contracts import ModelCallResult, RoutingDecision

app = FastAPI(
    title="Cost-LLM Model Gateway",
    description="Unified model adapter for local (Ollama) and hosted LLMs with metering",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "model-gateway", "version": "0.1.0"}


@app.post("/v1/execute", response_model=ModelCallResult)
async def execute_subtask(decision: RoutingDecision):
    """
    Unified execution entrypoint for Model Gateway.
    Member B will implement:
    1. Provider client dispatch (Ollama local, OpenAI, Anthropic, Google)
    2. Input/output token counting
    3. Latency measurement
    4. Cost calculation ($USD per 1M tokens)
    5. Response normalization and error handling
    """
    return ModelCallResult(
        subtask_id=decision.subtask_id,
        model_used=decision.chosen_model,
        tokens_in=10,
        tokens_out=25,
        latency_ms=120.0,
        cost_usd=0.0 if decision.chosen_tier == "local" else 0.0001,
        raw_output=f"Model Gateway scaffolding response for [{decision.subtask_id}].",
        error=None,
    )
