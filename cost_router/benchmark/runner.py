"""
Benchmark Runner: Executes comprehensive comparative evaluations across routing strategies.
Validates the cost-quality trade-off balancing system.
"""

from typing import List, Dict, Any
from cost_router.config import ModelTier, RoutingPolicy
from cost_router.benchmark.dataset import BENCHMARK_SUITE, BenchmarkItem
from cost_router.benchmark.evaluator import BenchmarkEvaluator
from cost_router.router.engine import RoutingEngine


class BenchmarkRunner:
    """Runs automated benchmarks comparing dynamic LLM routing against fixed baselines."""

    def __init__(self, engine: RoutingEngine):
        self.engine = engine
        self.evaluator = BenchmarkEvaluator()

    async def run_full_benchmark(
        self, items: List[BenchmarkItem] = None
    ) -> Dict[str, Any]:
        """Runs the benchmark suite against 4 distinct routing configurations."""
        items_to_run = items or BENCHMARK_SUITE

        strategies = {
            "always_frontier": {
                "name": "Always Strongest (Baseline)",
                "policy": RoutingPolicy.MANUAL,
                "override_model": "o1-preview",
            },
            "always_local": {
                "name": "Always Local (Llama 3.2 3B)",
                "policy": RoutingPolicy.LOCAL_ONLY,
                "override_model": "llama3.2:3b",
            },
            "naive_cheap": {
                "name": "Always Low-Cost (GPT-4o-mini)",
                "policy": RoutingPolicy.MANUAL,
                "override_model": "gpt-4o-mini",
            },
            "dynamic_router": {
                "name": "Dynamic LLM Router (Ours)",
                "policy": RoutingPolicy.BALANCED,
                "override_model": None,
            },
        }

        results_by_strategy: Dict[str, List[Dict[str, Any]]] = {k: [] for k in strategies}

        for strat_key, strat_conf in strategies.items():
            for item in items_to_run:
                resp = await self.engine.route(
                    prompt=item.prompt,
                    policy=strat_conf["policy"],
                    override_model=strat_conf["override_model"],
                )
                evaluation = self.evaluator.evaluate_response(item, resp)
                results_by_strategy[strat_key].append(evaluation)

        # Compute aggregate summary statistics
        summary = {}
        baseline_cost = sum(
            r["actual_cost_usd"] for r in results_by_strategy["always_frontier"]
        )

        pareto_points = []

        for strat_key, evals in results_by_strategy.items():
            total_cost = sum(e["actual_cost_usd"] for e in evals)
            avg_quality = sum(e["quality_score"] for e in evals) / len(evals)
            avg_latency = sum(e["latency_ms"] for e in evals) / len(evals)
            savings_usd = max(0.0, baseline_cost - total_cost)
            reduction_pct = (
                (savings_usd / baseline_cost * 100.0) if baseline_cost > 0 else 0.0
            )

            efficiency = round(avg_quality / ((total_cost * 1000) + 0.1), 2)

            summary[strat_key] = {
                "strategy_name": strategies[strat_key]["name"],
                "total_cost_usd": round(total_cost, 6),
                "avg_quality_score": round(avg_quality, 1),
                "avg_latency_ms": round(avg_latency, 1),
                "cost_reduction_pct": round(reduction_pct, 2),
                "cost_savings_usd": round(savings_usd, 6),
                "cost_efficiency_ratio": efficiency,
            }

            pareto_points.append({
                "strategy": strategies[strat_key]["name"],
                "cost_usd": round(total_cost, 5),
                "quality": round(avg_quality, 1),
                "reduction_pct": round(reduction_pct, 1),
            })

        # Category breakdown for the dynamic router
        category_breakdown = {}
        for ev in results_by_strategy["dynamic_router"]:
            cat = ev["category"]
            if cat not in category_breakdown:
                category_breakdown[cat] = {"cost": 0.0, "quality": [], "count": 0}
            category_breakdown[cat]["cost"] += ev["actual_cost_usd"]
            category_breakdown[cat]["quality"].append(ev["quality_score"])
            category_breakdown[cat]["count"] += 1

        for cat, data in category_breakdown.items():
            data["cost"] = round(data["cost"], 6)
            data["avg_quality"] = round(sum(data["quality"]) / len(data["quality"]), 1)
            del data["quality"]

        return {
            "total_items_evaluated": len(items_to_run),
            "summary_by_strategy": summary,
            "pareto_trade_off_points": pareto_points,
            "category_breakdown": category_breakdown,
            "detailed_evaluations": results_by_strategy,
        }
