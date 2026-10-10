"""
Command Line Interface (CLI) for Cost-Optimized LLM Router.
Provides rich terminal formatting, live queries, benchmarks, and server launching.
"""

import sys
import asyncio
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from cost_router.config import ModelTier, RoutingPolicy, global_config
from cost_router.models.registry import global_registry
from cost_router.router.engine import global_engine
from cost_router.benchmark.runner import BenchmarkRunner

console = Console()


def cmd_route(args):
    """Executes a single prompt with transparent routing explanation."""
    policy = RoutingPolicy(args.policy) if args.policy else RoutingPolicy.BALANCED
    override = args.override

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Analyzing complexity and routing request..."),
        transient=True,
    ) as progress:
        progress.add_task("route", total=None)
        response = asyncio.run(
            global_engine.route(
                prompt=args.prompt,
                policy=policy,
                override_model=override,
            )
        )

    trace = response.trace

    # Display Routing Audit Panel
    audit_table = Table(title="LLM Routing Audit & Cost Summary", border_style="cyan")
    audit_table.add_column("Metric", style="bold white", width=24)
    audit_table.add_column("Value", style="cyan")

    audit_table.add_row("Request ID", trace.request_id)
    audit_table.add_row("Detected Intent", trace.detected_intent)
    audit_table.add_row("Complexity Score", f"{trace.overall_complexity:.2f} / 1.00")
    audit_table.add_row("Routing Policy", trace.policy.value)
    audit_table.add_row("Multi-Part Decomposed?", "Yes" if trace.is_decomposed else "No")
    audit_table.add_row("Manual Override?", f"Yes ({trace.override_reason})" if trace.is_override else "No (Dynamic)")

    if trace.is_decomposed:
        for idx, st in enumerate(trace.subtasks, 1):
            audit_table.add_row(f"  Subtask {idx} Model", f"{st.selected_model} ({st.selected_tier.value.upper()})")
    else:
        audit_table.add_row("Selected Model", f"{trace.subtasks[0].selected_model} ({trace.subtasks[0].selected_tier.value.upper()})")

    audit_table.add_row("Total Tokens", f"{response.total_usage.total_tokens} (prompt: {response.total_usage.prompt_tokens}, out: {response.total_usage.completion_tokens})")
    audit_table.add_row("Routed Actual Cost", f"${response.cost_summary.total_cost_usd:.6f} USD")
    audit_table.add_row("Baseline Cost (Always Frontier)", f"${response.cost_summary.baseline_cost_usd:.6f} USD")
    audit_table.add_row("Cost Savings", f"[bold green]${response.cost_summary.savings_usd:.6f} USD ({response.cost_summary.reduction_percentage:.1f}% Saved)[/bold green]")
    audit_table.add_row("Latency", f"{response.total_latency_ms:.0f} ms")

    console.print(audit_table)

    console.print(Panel(
        f"[bold yellow]Routing Explanation:[/bold yellow]\n{trace.explanation}",
        title="Transparency Trace",
        border_style="yellow"
    ))

    console.print(Panel(
        response.final_output,
        title="[bold green]Synthesized Output[/bold green]",
        border_style="green"
    ))


def cmd_benchmark(args):
    """Runs the trade-off benchmarking suite and outputs a rich comparison table."""
    console.print("[bold cyan]Starting Cost vs Quality Benchmarking Suite...[/bold cyan]")

    runner = BenchmarkRunner(global_engine)
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold magenta]Evaluating strategies across diverse task categories..."),
        transient=True,
    ) as progress:
        progress.add_task("bench", total=None)
        results = asyncio.run(runner.run_full_benchmark())

    table = Table(title="Empirical Benchmarking: Cost vs Quality Trade-off", border_style="magenta")
    table.add_column("Strategy", style="bold white")
    table.add_column("Total Cost ($)", justify="right", style="cyan")
    table.add_column("Cost Reduction", justify="right", style="green")
    table.add_column("Quality Score", justify="right", style="yellow")
    table.add_column("Avg Latency", justify="right", style="dim")
    table.add_column("Efficiency Index", justify="right", style="bold magenta")

    for key, s in results["summary_by_strategy"].items():
        is_router = key == "dynamic_router"
        strat_display = f"[bold green]>> {s['strategy_name']}[/bold green]" if is_router else s['strategy_name']
        table.add_row(
            strat_display,
            f"${s['total_cost_usd']:.5f}",
            f"{s['cost_reduction_pct']:.1f}%",
            f"{s['avg_quality_score']:.1f} / 100",
            f"{s['avg_latency_ms']:.0f} ms",
            f"{s['cost_efficiency_ratio']:.1f}",
        )

    console.print(table)

    # Category analysis table
    cat_table = Table(title="Dynamic Router Performance By Category", border_style="blue")
    cat_table.add_column("Category", style="bold white")
    cat_table.add_column("Items", justify="center")
    cat_table.add_column("Total Cost ($)", justify="right", style="cyan")
    cat_table.add_column("Avg Quality", justify="right", style="yellow")

    for cat, data in results["category_breakdown"].items():
        cat_table.add_row(cat, str(data["count"]), f"${data['cost']:.5f}", f"{data['avg_quality']:.1f}%")

    console.print(cat_table)


def cmd_models(args):
    """Lists registered models, tiers, and pricing."""
    table = Table(title="Registered Model Portfolio & Pricing Catalog", border_style="green")
    table.add_column("Model Name", style="bold white")
    table.add_column("Tier", style="yellow")
    table.add_column("Input Cost/1M", justify="right")
    table.add_column("Output Cost/1M", justify="right")
    table.add_column("Latency (est)", justify="right")
    table.add_column("Hardware / Description", style="dim")

    for m in global_registry.list_models_info():
        table.add_row(
            m["model_name"],
            m["tier"].upper(),
            f"${m['prompt_cost_per_1m']:.2f}",
            f"${m['completion_cost_per_1m']:.2f}",
            f"{m['estimated_latency_ms']} ms",
            m["description"]
        )
    console.print(table)


def cmd_serve(args):
    """Starts the FastAPI Web Dashboard & REST API server."""
    import uvicorn
    console.print(f"[bold green]Launching Web Dashboard at http://localhost:{args.port}[/bold green]")
    uvicorn.run("cost_router.api.server:app", host=args.host, port=args.port, reload=False)


def main():
    parser = argparse.ArgumentParser(description="Cost-Optimized LLM Routing CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # route command
    p_route = subparsers.add_parser("route", help="Route and execute an incoming prompt")
    p_route.add_argument("prompt", type=str, help="Prompt text")
    p_route.add_argument("--policy", choices=[p.value for p in RoutingPolicy], default="balanced", help="Routing policy preset")
    p_route.add_argument("--override", type=str, default=None, help="Manual model override")
    p_route.set_defaults(func=cmd_route)

    # benchmark command
    p_bench = subparsers.add_parser("benchmark", help="Run comparative benchmark suite")
    p_bench.set_defaults(func=cmd_benchmark)

    # models command
    p_models = subparsers.add_parser("models", help="List registered models and pricing")
    p_models.set_defaults(func=cmd_models)

    # serve command
    p_serve = subparsers.add_parser("serve", help="Start the Web Dashboard and API")
    p_serve.add_argument("--host", type=str, default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
