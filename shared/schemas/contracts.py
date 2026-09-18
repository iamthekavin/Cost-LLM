"""
Cost-LLM Shared Schema Contracts
Standardized data contracts for all 4 workstreams:
- Member A (Router Core)
- Member B (Model Gateway)
- Member C (Control Plane)
- Member D (Benchmark)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReasoningDepth(str, Enum):
    """Reasoning depth required for a prompt or subtask."""
    TRIVIAL = "trivial"
    MODERATE = "moderate"
    DEEP = "deep"


class ModelTier(str, Enum):
    """Model tier representing cost/capability profile."""
    LOCAL = "local"
    CHEAP = "cheap"
    PREMIUM = "premium"


class SubtaskPrompt(BaseModel):
    """Optional decomposed subtask provided directly by caller or generated during routing."""
    model_config = ConfigDict(extra="allow")

    subtask_id: str = Field(..., description="Unique identifier for the subtask")
    prompt: str = Field(..., description="Prompt text specific to this subtask")
    context: Optional[str] = Field(default=None, description="Optional inherited or parent context")


class RoutingRequest(BaseModel):
    """Contract A: Caller payload sent to Router Core."""
    model_config = ConfigDict(extra="allow")

    request_id: str = Field(..., description="Unique identifier for the caller request (UUID recommended)")
    user_id: str = Field(..., description="Identifier of caller or tenant for rate limiting and billing")
    prompt: str = Field(..., description="Raw text prompt submitted by user")
    subtasks: Optional[List[SubtaskPrompt]] = Field(
        default=None,
        description="Optional pre-split subtasks. If null or empty, Router Core splits if required."
    )
    max_cost_usd: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Optional budget ceiling in USD for servicing this entire request"
    )
    quality_floor: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum acceptable quality threshold between 0.0 and 1.0"
    )
    override_model: Optional[str] = Field(
        default=None,
        description="Caller-forced model identifier (bypasses routing classifier if provided)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata (e.g. client app, tags, telemetry)"
    )


class RoutingDecision(BaseModel):
    """Contract B: Router Core decision for each (sub)task."""
    model_config = ConfigDict(extra="allow")

    request_id: str = Field(..., description="Parent request identifier")
    subtask_id: str = Field(..., description="Identifier for this specific subtask")
    subtask_text: str = Field(..., description="Actual text sent to the chosen model")
    complexity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated reasoning complexity between 0.0 (trivial) and 1.0 (frontier deep reasoning)"
    )
    reasoning_depth: ReasoningDepth = Field(
        ...,
        description="Categorical reasoning depth (trivial, moderate, deep)"
    )
    chosen_model: str = Field(
        ...,
        description="Identifier of model selected for execution (e.g., llama3.1:8b, gpt-4o-mini, gpt-4o)"
    )
    chosen_tier: ModelTier = Field(
        ...,
        description="Tier of the chosen model (local, cheap, premium)"
    )
    routing_reason: str = Field(
        ...,
        description="Short human-readable rationale explaining why this model/tier was selected"
    )
    fallback_model: Optional[str] = Field(
        default=None,
        description="Designated secondary model if chosen_model times out or fails"
    )
    overridden_by_user: bool = Field(
        default=False,
        description="True if an explicit user or admin override dictated chosen_model"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the routing decision was made"
    )


class ModelCallResult(BaseModel):
    """Contract C: Model Gateway execution output per subtask."""
    model_config = ConfigDict(extra="allow")

    subtask_id: str = Field(..., description="Identifier corresponding to the executed subtask")
    model_used: str = Field(..., description="Actual model that completed the execution")
    tokens_in: int = Field(default=0, ge=0, description="Prompt/input token count")
    tokens_out: int = Field(default=0, ge=0, description="Completion/output token count")
    latency_ms: float = Field(default=0.0, ge=0.0, description="End-to-end execution latency in milliseconds")
    cost_usd: float = Field(default=0.0, ge=0.0, description="Calculated monetary cost in USD")
    raw_output: str = Field(..., description="Model generated text response")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")


class SubtaskBreakdownItem(BaseModel):
    """Pairing of a RoutingDecision and its corresponding ModelCallResult."""
    model_config = ConfigDict(extra="allow")

    subtask_id: str = Field(..., description="Subtask identifier")
    decision: RoutingDecision = Field(..., description="Routing decision for this subtask")
    result: Optional[ModelCallResult] = Field(default=None, description="Execution result from Model Gateway")


class FinalResponse(BaseModel):
    """Contract D: Merged output returned to the original caller."""
    model_config = ConfigDict(extra="allow")

    request_id: str = Field(..., description="Original request identifier")
    final_answer: str = Field(..., description="Synthesized, merged final response text")
    subtask_breakdown: List[SubtaskBreakdownItem] = Field(
        default_factory=list,
        description="Per-subtask execution audit (RoutingDecision + ModelCallResult)"
    )
    total_cost_usd: float = Field(default=0.0, ge=0.0, description="Summed monetary cost of all subtasks in USD")
    total_latency_ms: float = Field(default=0.0, ge=0.0, description="End-to-end request latency in milliseconds")


class OverrideDetails(BaseModel):
    """Metadata regarding manual or policy overrides."""
    model_config = ConfigDict(extra="allow")

    is_overridden: bool = Field(default=False, description="Whether an override took place")
    overridden_by: Optional[str] = Field(default=None, description="Actor or policy name (e.g. user, admin, rate-limit-policy)")
    reason: Optional[str] = Field(default=None, description="Explanation for manual override")
    original_model: Optional[str] = Field(default=None, description="Model that router originally selected")


class DecisionLogEntry(BaseModel):
    """Contract E: Audit log entry stored and exposed by Control Plane."""
    model_config = ConfigDict(extra="allow")

    request_id: str = Field(..., description="Request identifier")
    subtask_id: str = Field(..., description="Subtask identifier")
    user_id: Optional[str] = Field(default=None, description="Caller / tenant ID")
    prompt_text: Optional[str] = Field(default=None, description="Prompt or subtask text")
    routing_decision: RoutingDecision = Field(..., description="Router decision details")
    model_call_result: Optional[ModelCallResult] = Field(default=None, description="Model Gateway result if executed")
    override_details: OverrideDetails = Field(
        default_factory=OverrideDetails,
        description="Information regarding manual or administrative overrides"
    )
    client_ip: Optional[str] = Field(default=None, description="Client IP address for security & auditing")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when log entry was persisted"
    )


class BenchmarkRecord(BaseModel):
    """Contract F: Benchmark evaluation record comparing router vs baseline."""
    model_config = ConfigDict(extra="allow")

    request_id: str = Field(..., description="Evaluated request identifier")
    task_category: str = Field(
        default="general",
        description="Category of prompt (e.g. coding, math, summarization, creative, extraction)"
    )
    router_cost_usd: float = Field(..., ge=0.0, description="Actual cost incurred using router selection")
    baseline_cost_usd: float = Field(
        ...,
        ge=0.0,
        description="Estimated cost if the prompt had been sent to the always-strongest model"
    )
    cost_savings_pct: float = Field(
        ...,
        description="Percentage savings: ((baseline_cost - router_cost) / baseline_cost) * 100"
    )
    router_quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Quality evaluation of router's output (0.0 to 1.0)"
    )
    baseline_quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Quality evaluation of baseline model's output (0.0 to 1.0)"
    )
    quality_delta: float = Field(
        ...,
        description="Quality difference: (router_quality_score - baseline_quality_score)"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of benchmark execution"
    )
