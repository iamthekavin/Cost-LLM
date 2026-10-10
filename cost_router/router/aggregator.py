"""
Aggregator: Coordinates subtask pipeline execution, injects dependency context,
and synthesizes multi-part outputs with clear model provenance.
"""

import time
from typing import List
from cost_router.config import global_config
from cost_router.models.base import (
    SubTaskPlan,
    RoutingTrace,
    AggregatedResponse,
    ModelResponse,
    TokenUsage,
    CostMetrics,
    calculate_cost,
    calculate_savings,
)
from cost_router.models.registry import ModelRegistry


class ResultAggregator:
    """Executes subtask workflows, aggregates outputs, and verifies cost accounting."""

    def __init__(self, registry: ModelRegistry):
        self.registry = registry

    async def execute_and_aggregate(
        self, trace: RoutingTrace, subtasks: List[SubTaskPlan]
    ) -> AggregatedResponse:
        overall_start = time.perf_counter()
        subtask_results: List[ModelResponse] = []
        completed_outputs: dict[int, str] = {}

        # Execute each subtask in topological order
        for subtask in subtasks:
            client = self.registry.get_client(subtask.selected_model)
            if not client:
                client = self.registry.get_tier_client(subtask.selected_tier)

            # Context injection if dependencies exist
            prompt_to_send = subtask.prompt_chunk
            if subtask.dependencies:
                dep_contexts = []
                for dep_id in subtask.dependencies:
                    if dep_id in completed_outputs:
                        dep_contexts.append(f"[Context from Step {dep_id}]:\n{completed_outputs[dep_id]}")
                if dep_contexts:
                    prompt_to_send = f"{chr(10).join(dep_contexts)}\n\n[Current Task Instruction]:\n{subtask.prompt_chunk}"

            # Execute generation
            system_msg = (
                f"You are executing part of a decomposed workflow. Task focus: {subtask.title}. "
                "Provide a precise, high-quality answer."
            )
            response = await client.generate(prompt=prompt_to_send, system_prompt=system_msg)
            subtask_results.append(response)
            completed_outputs[subtask.id] = response.text

        total_elapsed_ms = (time.perf_counter() - overall_start) * 1000

        # Synthesize final output
        if len(subtasks) == 1:
            final_output = subtask_results[0].text
        else:
            final_output = self._synthesize_multi_part_response(subtasks, subtask_results)

        # Aggregate tokens and compute final cost
        total_prompt_tokens = sum(r.usage.prompt_tokens for r in subtask_results)
        total_completion_tokens = sum(r.usage.completion_tokens for r in subtask_results)
        total_actual_cost = sum(r.cost.total_cost_usd for r in subtask_results)

        # Baseline cost calculation:
        # What it would have cost if all prompt and completion tokens were handled by Tier 4 Frontier
        baseline_model = global_config.baseline_model
        baseline_cost = calculate_cost(baseline_model, total_prompt_tokens, total_completion_tokens)
        savings_usd, reduction_pct = calculate_savings(total_actual_cost, baseline_cost)

        usage = TokenUsage(
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            total_tokens=total_prompt_tokens + total_completion_tokens,
        )

        cost_summary = CostMetrics(
            prompt_cost_usd=round(sum(r.cost.prompt_cost_usd for r in subtask_results), 6),
            completion_cost_usd=round(sum(r.cost.completion_cost_usd for r in subtask_results), 6),
            total_cost_usd=round(total_actual_cost, 6),
            baseline_cost_usd=baseline_cost,
            savings_usd=savings_usd,
            reduction_percentage=reduction_pct,
        )

        return AggregatedResponse(
            request_id=trace.request_id,
            final_output=final_output,
            trace=trace,
            total_latency_ms=round(total_elapsed_ms, 2),
            total_usage=usage,
            cost_summary=cost_summary,
            subtask_results=subtask_results,
        )

    def _synthesize_multi_part_response(
        self, subtasks: List[SubTaskPlan], results: List[ModelResponse]
    ) -> str:
        """Constructs an aggregated document detailing each subtask output and model attribution."""
        sections = [
            "## Synthesized Solution (Multi-Part Routed Workflow)\n"
        ]

        for plan, res in zip(subtasks, results):
            sections.append(
                f"### {plan.title}\n"
                f"*Model: `{res.model_name}` ({res.tier.value.upper()} Tier) | Cost: ${res.cost.total_cost_usd:.6f}*\n\n"
                f"{res.text.strip()}\n"
            )

        sections.append(
            "\n---\n"
            "### Routing & Cost Transparency Summary\n"
            "This compound request was dynamically divided across models. "
            "Simpler extraction/formatting parts were processed at zero or near-zero cost, "
            "conserving expensive frontier capacity exclusively for reasoning steps."
        )

        return "\n".join(sections)
