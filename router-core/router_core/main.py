"""Router Core FastAPI Application (Member A)."""
from fastapi import FastAPI

from shared.schemas.contracts import (
    FinalResponse,
    ModelTier,
    ReasoningDepth,
    RoutingDecision,
    RoutingRequest,
    SubtaskBreakdownItem,
)

app = FastAPI(
    title="Cost-LLM Router Core",
    description="Complexity classification, decomposition, and model routing engine",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "router-core", "version": "0.1.0"}


@app.post("/v1/route", response_model=FinalResponse)
async def route_request(request: RoutingRequest):
    """
    Main entrypoint for callers.
    Member A will implement:
    1. Prompt complexity scoring & reasoning depth evaluation
    2. Subtask decomposition (if prompt is multi-part)
    3. Model selection / tier allocation
    4. Model Gateway dispatch
    5. Result synthesis and merger
    """
    stub_decision = RoutingDecision(
        request_id=request.request_id,
        subtask_id="subtask_0",
        subtask_text=request.prompt,
        complexity_score=0.1,
        reasoning_depth=ReasoningDepth.TRIVIAL,
        chosen_model="llama3.1:8b",
        chosen_tier=ModelTier.LOCAL,
        routing_reason="Scaffolding placeholder decision",
        overridden_by_user=bool(request.override_model),
    )

    return FinalResponse(
        request_id=request.request_id,
        final_answer="Router Core scaffolding response placeholder.",
        subtask_breakdown=[
            SubtaskBreakdownItem(
                subtask_id="subtask_0",
                decision=stub_decision,
                result=None,
            )
        ],
        total_cost_usd=0.0,
        total_latency_ms=0.0,
    )
