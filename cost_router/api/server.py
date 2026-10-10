"""
FastAPI Server & REST API.
Provides interactive endpoints for prompt routing, complexity previews,
administrative controls, telemetry metrics, and benchmarking.
"""

import os
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from cost_router.config import (
    ModelTier,
    RoutingPolicy,
    global_config,
    POLICY_THRESHOLDS,
)
from cost_router.models.registry import global_registry
from cost_router.analyzer.task_classifier import global_classifier
from cost_router.analyzer.decomposer import PromptDecomposer
from cost_router.router.engine import global_engine
from cost_router.router.tracer import global_tracer
from cost_router.benchmark.runner import BenchmarkRunner


app = FastAPI(
    title="Cost-Optimized LLM Router",
    description="Intelligent multi-tier model routing with prompt decomposition and cost transparency",
    version="1.0.0",
)

# Route Request Models
class RouteRequest(BaseModel):
    prompt: str = Field(..., description="The user prompt to route")
    policy: Optional[RoutingPolicy] = Field(default=None, description="Routing policy preset")
    override_model: Optional[str] = Field(default=None, description="Manual model override")
    override_tier: Optional[ModelTier] = Field(default=None, description="Manual tier override")
    decompose: Optional[bool] = Field(default=None, description="Force multi-part decomposition")


class ConfigUpdateRequest(BaseModel):
    default_policy: Optional[RoutingPolicy] = None
    baseline_model: Optional[str] = None
    enable_auto_decomposition: Optional[bool] = None
    allow_admin_override: Optional[bool] = None
    simulation_mode: Optional[bool] = None


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "cost-optimized-llm-router"}


@app.get("/api/models")
async def list_models():
    """List all registered models, tiers, pricing, and live availability."""
    models_info = global_registry.list_models_info()
    # Check live Ollama status
    local_client = global_registry.get_client("llama3.2:3b")
    ollama_live = await local_client.is_available() if local_client else False

    for m in models_info:
        if m["is_local"]:
            m["is_available"] = ollama_live
        else:
            m["is_available"] = True

    return {
        "models": models_info,
        "baseline_model": global_config.baseline_model,
        "local_daemon_active": ollama_live,
    }


@app.get("/api/config")
async def get_config():
    """Returns current active configuration, thresholds, and policies."""
    return {
        "default_policy": global_config.default_policy.value,
        "baseline_model": global_config.baseline_model,
        "enable_auto_decomposition": global_config.enable_auto_decomposition,
        "allow_admin_override": global_config.allow_admin_override,
        "simulation_mode": global_config.simulation_mode,
        "policies": [p.value for p in RoutingPolicy],
        "thresholds": {k.value: v for k, v in POLICY_THRESHOLDS.items()},
    }


@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest):
    """Update runtime configuration settings."""
    if req.default_policy is not None:
        global_config.default_policy = req.default_policy
    if req.baseline_model is not None:
        global_config.baseline_model = req.baseline_model
    if req.enable_auto_decomposition is not None:
        global_config.enable_auto_decomposition = req.enable_auto_decomposition
    if req.allow_admin_override is not None:
        global_config.allow_admin_override = req.allow_admin_override
    if req.simulation_mode is not None:
        global_config.simulation_mode = req.simulation_mode

    return {"message": "Configuration updated successfully", "config": req}


@app.post("/api/preview")
async def preview_routing(req: RouteRequest):
    """Instantly preview complexity score and decomposition plan without executing models."""
    analysis = global_classifier.analyze(req.prompt)
    decomposer = PromptDecomposer(global_classifier)
    active_policy = req.policy or global_config.default_policy

    if req.override_model:
        plan_desc = f"Administrative override to {req.override_model}"
        subtasks = []
    elif decomposer.can_decompose(req.prompt, analysis):
        plan_desc = "Multi-part request detected. Will decompose into subtasks."
        subtasks = [s.model_dump() for s in decomposer.decompose(req.prompt, active_policy)]
    else:
        plan_desc = "Single-task request."
        subtasks = []

    return {
        "analysis": analysis.model_dump(),
        "preview_plan": plan_desc,
        "subtasks": subtasks,
        "policy": active_policy.value,
    }


@app.post("/api/route")
async def route_prompt(req: RouteRequest):
    """Execute incoming prompt through the cost-optimizing LLM router."""
    try:
        response = await global_engine.route(
            prompt=req.prompt,
            policy=req.policy,
            override_model=req.override_model,
            override_tier=req.override_tier,
            decompose=req.decompose,
        )
        return response.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics")
async def get_metrics():
    """Retrieve cumulative cost savings, token consumption, and routing telemetry."""
    return global_tracer.get_summary_metrics()


@app.get("/api/history")
async def get_history(limit: int = 50):
    """Retrieve audit history of routed requests."""
    return global_tracer.get_recent_history(limit=limit)


@app.post("/api/benchmark/run")
async def run_benchmark():
    """Run automated comparative benchmark suite across 4 strategies."""
    runner = BenchmarkRunner(global_engine)
    results = await runner.run_full_benchmark()
    return results


# Mount static assets for the Dashboard UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def serve_index():
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Web dashboard static files not found."}
