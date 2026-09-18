"""Model Gateway FastAPI Application (Member B).

Unified model execution interface across local (Ollama) and hosted providers.
Features:
- /health: Validates gateway & local Ollama daemon connectivity
- /call & /v1/execute: Dispatches subtasks, handles retries, timeouts, and fallback_model
- /call/batch: Concurrently executes multiple subtasks
"""

import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from model_gateway.config import settings
from model_gateway.providers.local_ollama import LocalOllamaProvider
from model_gateway.router import execute_batch_concurrently, execute_call
from shared.schemas.contracts import ModelCallResult, RoutingDecision

app = FastAPI(
    title="Cost-LLM Model Gateway",
    description="Unified model adapter for local (Ollama) and hosted LLMs with metering, retries, and fallback",
    version="1.0.0",
)


class CallRequest(BaseModel):
    """Execution request specification."""
    subtask_id: str = Field(default="subtask_0", description="Subtask identifier")
    subtask_text: str = Field(..., description="Prompt or text to process")
    chosen_model: str = Field(default="llama3.1:8b", description="Primary model identifier")
    fallback_model: Optional[str] = Field(default=None, description="Backup model if chosen_model fails")
    timeout_s: Optional[float] = Field(default=None, description="Request timeout in seconds")
    params: Dict[str, Any] = Field(default_factory=dict, description="Model generation parameters")


class BatchCallRequest(BaseModel):
    items: List[CallRequest] = Field(..., description="List of subtask execution requests")


class BatchCallResponse(BaseModel):
    batch_size: int
    total_latency_ms: float
    results: List[ModelCallResult]


@app.get("/health")
async def health_check():
    """
    Healthcheck endpoint confirming Gateway and Ollama daemon connectivity.
    Reports 'ok' if Ollama is reachable, 'degraded' if Ollama is offline.
    """
    ollama = LocalOllamaProvider(settings.default_local_model)
    ollama_status = await ollama.check_health(timeout_s=2.0)

    is_healthy = ollama_status.get("reachable", False)
    status_label = "ok" if is_healthy else "degraded"

    return {
        "status": status_label,
        "service": "model-gateway",
        "version": "1.0.0",
        "ollama_reachable": is_healthy,
        "ollama_details": ollama_status,
        "available_models": list(settings.models.keys()),
    }


@app.post("/call", response_model=ModelCallResult)
async def call_model(req: CallRequest):
    """Unified entrypoint to call any model with timeout, retries, and fallback."""
    result = await execute_call(
        subtask_id=req.subtask_id,
        prompt=req.subtask_text,
        chosen_model=req.chosen_model,
        fallback_model=req.fallback_model,
        timeout_s=req.timeout_s,
        params=req.params,
    )
    return result


@app.post("/v1/execute", response_model=ModelCallResult)
async def execute_subtask(decision: RoutingDecision):
    """Canonical INTERFACE_CONTRACT endpoint accepting RoutingDecision directly from Router Core."""
    result = await execute_call(
        subtask_id=decision.subtask_id,
        prompt=decision.subtask_text,
        chosen_model=decision.chosen_model,
        fallback_model=decision.fallback_model,
    )
    return result


@app.post("/call/batch", response_model=BatchCallResponse)
async def call_batch(req: BatchCallRequest):
    """Execute multiple subtasks concurrently via asyncio.gather."""
    if not req.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batch cannot be empty")

    start_time = time.perf_counter()
    raw_items = [item.model_dump() for item in req.items]
    results = await execute_batch_concurrently(raw_items)
    total_latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    return BatchCallResponse(
        batch_size=len(results),
        total_latency_ms=total_latency_ms,
        results=results,
    )
