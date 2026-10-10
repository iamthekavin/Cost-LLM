"""
Unit tests for Routing Engine and Policy Enforcement.
"""

import pytest
from cost_router.config import ModelTier, RoutingPolicy
from cost_router.router.engine import RoutingEngine


@pytest.fixture
def engine():
    return RoutingEngine()


@pytest.mark.asyncio
async def test_route_simple_task_balanced(engine):
    prompt = "Extract all dates from this short paragraph: March 5th, 2026."
    res = await engine.route(prompt=prompt, policy=RoutingPolicy.BALANCED)

    # Simple extraction should route to local tier (llama3.2:3b)
    assert res.trace.subtasks[0].selected_tier == ModelTier.LOCAL
    assert res.trace.subtasks[0].selected_model == "llama3.2:3b"
    assert res.cost_summary.total_cost_usd == 0.0 # Zero-cost local execution
    assert res.cost_summary.reduction_percentage == 100.0


@pytest.mark.asyncio
async def test_route_coding_task_balanced(engine):
    prompt = "Write a python FastAPI async endpoint that validates user tokens and handles exceptions."
    res = await engine.route(prompt=prompt, policy=RoutingPolicy.BALANCED)

    # Moderate coding task routes to balanced or cheap tier, not local
    assert res.trace.subtasks[0].selected_tier in [ModelTier.CHEAP, ModelTier.BALANCED]
    assert res.cost_summary.savings_usd > 0.0 # Substantial savings vs o1-preview frontier


@pytest.mark.asyncio
async def test_route_frontier_reasoning(engine):
    prompt = "Deduce and prove that this game theory strategy forms a unique subgame perfect Nash equilibrium using formal logic."
    res = await engine.route(prompt=prompt, policy=RoutingPolicy.BALANCED)

    assert res.trace.subtasks[0].selected_tier == ModelTier.FRONTIER
    assert res.trace.subtasks[0].selected_model == "o1-preview"


@pytest.mark.asyncio
async def test_local_only_policy(engine):
    # Even a complex prompt must route to local under LOCAL_ONLY policy
    prompt = "Conduct a high-level mathematical proof of quantum decoherence."
    res = await engine.route(prompt=prompt, policy=RoutingPolicy.LOCAL_ONLY)

    assert res.trace.subtasks[0].selected_tier == ModelTier.LOCAL
    assert res.trace.subtasks[0].selected_model == "llama3.2:3b"
    assert res.cost_summary.total_cost_usd == 0.0


@pytest.mark.asyncio
async def test_administrative_override(engine):
    prompt = "Extract numbers 1, 2, 3"
    res = await engine.route(
        prompt=prompt,
        override_model="gpt-4o",
    )

    assert res.trace.is_override is True
    assert res.trace.subtasks[0].selected_model == "gpt-4o"
    assert "Manual admin override" in res.trace.override_reason
