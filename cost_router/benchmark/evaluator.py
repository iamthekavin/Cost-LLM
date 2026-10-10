"""
Benchmark Evaluator: Assesses quality scores, evaluates trade-offs,
and computes cost-efficiency indices.
"""

from typing import Dict, Any, List
from cost_router.config import ModelTier
from cost_router.benchmark.dataset import BenchmarkItem
from cost_router.models.base import AggregatedResponse


class BenchmarkEvaluator:
    """Computes quality score and trade-off metrics for a given request evaluation."""

    def evaluate_response(
        self, item: BenchmarkItem, response: AggregatedResponse
    ) -> Dict[str, Any]:
        """Evaluates quality (0-100) and calculates cost efficiency."""
        text = response.final_output.lower()

        # 1. Rubric keyword match
        matched_keywords = [kw for kw in item.rubric_keywords if kw.lower() in text]
        keyword_ratio = (
            len(matched_keywords) / len(item.rubric_keywords)
            if item.rubric_keywords
            else 1.0
        )

        # 2. Structural and length adequacy check
        word_count = len(text.split())
        length_score = 1.0
        if word_count < 10:
            length_score = 0.3
        elif word_count < 25 and item.expected_tier in [ModelTier.BALANCED, ModelTier.FRONTIER]:
            length_score = 0.6

        # 3. Model tier adequacy vs expected tier
        # If task requires frontier reasoning, but was forced onto a weak model, penalize quality
        primary_tier = response.trace.subtasks[0].selected_tier if response.trace.subtasks else ModelTier.LOCAL
        tier_penalty = 0.0
        if item.expected_tier == ModelTier.FRONTIER and primary_tier == ModelTier.LOCAL:
            tier_penalty = 0.35 # Substantial quality drop if frontier task is sent to small local model
        elif item.expected_tier == ModelTier.FRONTIER and primary_tier == ModelTier.CHEAP:
            tier_penalty = 0.15
        elif item.expected_tier == ModelTier.BALANCED and primary_tier == ModelTier.LOCAL:
            tier_penalty = 0.20

        raw_quality = (keyword_ratio * 0.70 + length_score * 0.30) - tier_penalty
        quality_score = round(max(15.0, min(100.0, raw_quality * 100.0)), 1)

        # 4. Cost and Efficiency Metrics
        actual_cost = response.cost_summary.total_cost_usd
        baseline_cost = response.cost_summary.baseline_cost_usd
        savings_usd = response.cost_summary.savings_usd
        savings_pct = response.cost_summary.reduction_percentage

        # Efficiency index: Quality delivered per millidollar spent
        # Higher is better
        cost_in_millidollars = (actual_cost * 1000.0) + 0.01
        efficiency_index = round(quality_score / cost_in_millidollars, 2)

        return {
            "item_id": item.id,
            "category": item.category,
            "quality_score": quality_score,
            "actual_cost_usd": actual_cost,
            "baseline_cost_usd": baseline_cost,
            "savings_usd": savings_usd,
            "savings_pct": savings_pct,
            "latency_ms": response.total_latency_ms,
            "efficiency_index": efficiency_index,
            "matched_keywords": matched_keywords,
            "total_tokens": response.total_usage.total_tokens,
            "is_decomposed": response.trace.is_decomposed,
        }
