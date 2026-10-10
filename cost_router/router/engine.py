"""
Core Routing Engine: Coordinates analysis, policy evaluation, administrative overrides,
multi-part decomposition, and execution routing.
"""

import uuid
from typing import Optional
from cost_router.config import (
    ModelTier,
    RoutingPolicy,
    TIER_DEFAULT_MODELS,
    POLICY_THRESHOLDS,
    global_config,
)
from cost_router.models.base import SubTaskPlan, RoutingTrace, AggregatedResponse
from cost_router.models.registry import ModelRegistry, global_registry
from cost_router.analyzer.task_classifier import TaskClassifier, global_classifier
from cost_router.analyzer.decomposer import PromptDecomposer
from cost_router.router.aggregator import ResultAggregator
from cost_router.router.tracer import RouterTracer, global_tracer


class RoutingEngine:
    """Intelligent, transparent cost-optimizing LLM router."""

    def __init__(
        self,
        classifier: Optional[TaskClassifier] = None,
        registry: Optional[ModelRegistry] = None,
        tracer: Optional[RouterTracer] = None,
    ):
        self.classifier = classifier or global_classifier
        self.registry = registry or global_registry
        self.tracer = tracer or global_tracer
        self.decomposer = PromptDecomposer(self.classifier)
        self.aggregator = ResultAggregator(self.registry)

    async def route(
        self,
        prompt: str,
        policy: Optional[RoutingPolicy] = None,
        override_model: Optional[str] = None,
        override_tier: Optional[ModelTier] = None,
        decompose: Optional[bool] = None,
    ) -> AggregatedResponse:
        """Evaluates incoming prompt, generates explainable routing plan, and executes."""
        request_id = f"req-{uuid.uuid4().hex[:8]}"
        active_policy = policy or global_config.default_policy

        # Step 1: Feature extraction & task complexity classification
        analysis = self.classifier.analyze(prompt)

        # Step 2: Evaluate administrative overrides
        is_override = False
        override_reason = None
        target_model = None
        target_tier = None

        if override_model and global_config.allow_admin_override:
            client = self.registry.get_client(override_model)
            if client:
                target_model = client.model_name
                target_tier = client.tier
                is_override = True
                override_reason = f"Manual admin override requested: {override_model}"

        elif override_tier and global_config.allow_admin_override:
            target_tier = override_tier
            target_model = TIER_DEFAULT_MODELS.get(target_tier, "llama3.2:3b")
            is_override = True
            override_reason = f"Manual admin tier override requested: {override_tier.value}"

        # Step 3: Evaluate decomposition
        should_decompose = decompose
        if should_decompose is None:
            should_decompose = (
                global_config.enable_auto_decomposition
                and not is_override
                and self.decomposer.can_decompose(prompt, analysis)
            )

        # Step 4: Plan subtasks or single routing
        subtasks = []
        explanation_lines = []

        if is_override:
            explanation_lines.append(f"Admin Override Active: {override_reason}")
            subtasks = [
                SubTaskPlan(
                    id=1,
                    title="Administrative Override Execution",
                    prompt_chunk=prompt,
                    intent=analysis.primary_intent,
                    complexity_score=analysis.complexity_score,
                    selected_tier=target_tier,
                    selected_model=target_model,
                    reasoning=f"Direct administrative assignment to {target_model}",
                    dependencies=[],
                )
            ]
        elif should_decompose:
            subtasks = self.decomposer.decompose(prompt, active_policy)
            explanation_lines.append(
                f"Multi-part request detected ({len(subtasks)} distinct subtasks). "
                f"Decomposed into an optimized multi-tier execution plan to maximize cost reduction."
            )
            for st in subtasks:
                explanation_lines.append(
                    f"  - [{st.title}]: {st.intent} (Complexity {st.complexity_score:.2f}) -> {st.selected_model}"
                )
        else:
            # Single task routing
            thresholds = POLICY_THRESHOLDS.get(active_policy, POLICY_THRESHOLDS[RoutingPolicy.BALANCED])
            comp = analysis.complexity_score

            if active_policy == RoutingPolicy.LOCAL_ONLY or comp < thresholds["local_max"]:
                target_tier = ModelTier.LOCAL
                explanation_lines.append(
                    f"Complexity score {comp:.2f} is within local threshold (<={thresholds['local_max']:.2f}). "
                    f"Routed to local zero-cost model for maximum economy."
                )
            elif comp < thresholds["cheap_max"]:
                target_tier = ModelTier.CHEAP
                explanation_lines.append(
                    f"Complexity score {comp:.2f} is within cheap tier range (<={thresholds['cheap_max']:.2f}). "
                    f"Routed to high-throughput low-cost model."
                )
            elif comp < thresholds["balanced_max"]:
                target_tier = ModelTier.BALANCED
                explanation_lines.append(
                    f"Complexity score {comp:.2f} warrants balanced general intelligence (<={thresholds['balanced_max']:.2f})."
                )
            else:
                target_tier = ModelTier.FRONTIER
                explanation_lines.append(
                    f"Complexity score {comp:.2f} exceeds balanced threshold (>{thresholds['balanced_max']:.2f}). "
                    f"Routed to frontier reasoning tier for strict logical/mathematical rigor."
                )

            target_model = TIER_DEFAULT_MODELS[target_tier]
            subtasks = [
                SubTaskPlan(
                    id=1,
                    title="Standard Request Execution",
                    prompt_chunk=prompt,
                    intent=analysis.primary_intent,
                    complexity_score=analysis.complexity_score,
                    selected_tier=target_tier,
                    selected_model=target_model,
                    reasoning=f"Selected {target_model} based on policy '{active_policy.value}'.",
                    dependencies=[],
                )
            ]

        # Step 5: Construct complete audit trace
        explanation = "\n".join(explanation_lines)
        trace = RoutingTrace(
            request_id=request_id,
            original_prompt=prompt,
            policy=active_policy,
            overall_complexity=analysis.complexity_score,
            detected_intent=analysis.primary_intent,
            is_decomposed=len(subtasks) > 1,
            is_override=is_override,
            override_reason=override_reason,
            subtasks=subtasks,
            explanation=explanation,
        )

        # Step 6: Execute and aggregate
        aggregated_response = await self.aggregator.execute_and_aggregate(trace, subtasks)

        # Step 7: Record audit telemetry
        self.tracer.record(aggregated_response)

        return aggregated_response


# Global singleton engine
global_engine = RoutingEngine()
