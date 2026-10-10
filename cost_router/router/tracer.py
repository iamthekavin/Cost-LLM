"""
Tracer: Audit telemetry and persistent logging for all routing decisions and cost accounting.
"""

from typing import List, Dict, Any
from collections import deque
from cost_router.models.base import AggregatedResponse, RoutingTrace


class RouterTracer:
    """Tracks historical requests, cumulative expenditure, and savings metrics."""

    def __init__(self, max_history: int = 500):
        self.history: deque[AggregatedResponse] = deque(maxlen=max_history)
        self.total_queries: int = 0
        self.total_actual_cost: float = 0.0
        self.total_baseline_cost: float = 0.0
        self.tier_counts: Dict[str, int] = {
            "local": 0,
            "cheap": 0,
            "balanced": 0,
            "frontier": 0,
        }
        self.model_counts: Dict[str, int] = {}

    def record(self, response: AggregatedResponse):
        """Records an executed query and updates cumulative accounting."""
        self.history.appendleft(response)
        self.total_queries += 1
        self.total_actual_cost += response.cost_summary.total_cost_usd
        self.total_baseline_cost += response.cost_summary.baseline_cost_usd

        # Track tier and model distribution across subtasks or single task
        if response.subtask_results:
            for sub in response.subtask_results:
                tier_val = sub.tier.value
                self.tier_counts[tier_val] = self.tier_counts.get(tier_val, 0) + 1
                self.model_counts[sub.model_name] = self.model_counts.get(sub.model_name, 0) + 1
        elif response.trace.subtasks:
            for st in response.trace.subtasks:
                tier_val = st.selected_tier.value
                self.tier_counts[tier_val] = self.tier_counts.get(tier_val, 0) + 1
                self.model_counts[st.selected_model] = self.model_counts.get(st.selected_model, 0) + 1

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Returns aggregated telemetry summary."""
        total_savings = max(0.0, self.total_baseline_cost - self.total_actual_cost)
        pct_savings = (
            (total_savings / self.total_baseline_cost * 100.0)
            if self.total_baseline_cost > 0
            else 0.0
        )

        return {
            "total_queries": self.total_queries,
            "total_actual_cost_usd": round(self.total_actual_cost, 6),
            "total_baseline_cost_usd": round(self.total_baseline_cost, 6),
            "total_savings_usd": round(total_savings, 6),
            "savings_percentage": round(pct_savings, 2),
            "tier_distribution": dict(self.tier_counts),
            "model_distribution": dict(self.model_counts),
        }

    def get_recent_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent execution traces for administrative inspection."""
        results = []
        for item in list(self.history)[:limit]:
            results.append({
                "request_id": item.request_id,
                "prompt": item.trace.original_prompt[:120] + ("..." if len(item.trace.original_prompt) > 120 else ""),
                "policy": item.trace.policy.value,
                "complexity": item.trace.overall_complexity,
                "is_decomposed": item.trace.is_decomposed,
                "is_override": item.trace.is_override,
                "cost_usd": item.cost_summary.total_cost_usd,
                "baseline_cost_usd": item.cost_summary.baseline_cost_usd,
                "savings_pct": item.cost_summary.reduction_percentage,
                "latency_ms": item.total_latency_ms,
                "timestamp": item.trace.timestamp,
                "subtasks_count": len(item.trace.subtasks),
                "explanation": item.trace.explanation,
            })
        return results


# Global tracer instance
global_tracer = RouterTracer()
