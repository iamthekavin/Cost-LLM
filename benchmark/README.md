# Cost-LLM Benchmark & Evaluation Engine (Member D)

This package contains the end-to-end benchmarking harness, task dataset, quality evaluation system, and cost reporting engine for the **Cost-LLM** project.

Its primary purpose is **proving, with empirical numbers, that the router saves money without losing quality** — achieving measurable cost reductions while maintaining output quality comparable to an "always-strongest" frontier baseline (e.g. GPT-4o / Claude 3.5 Sonnet).

---

## Deliverables Checklist

- [x] **60–100 task benchmark set** spanning trivial/moderate/deep + multi-part prompts, with difficulty labels (`benchmark/tasks/tasks.jsonl`)
- [x] **Dual-run harness** (router pipeline vs. always-premium baseline) using real cost/latency data from `FinalResponse` / `ModelCallResult` objects (`benchmark/runner.py`)
- [x] **Objective scoring** for closed-answer tasks (exact-match, regex, math/GSM8K, JSON rule-based, code execution) + **blind LLM-as-judge scoring** for open-ended tasks with randomized candidate presentation order and artifact stripping (`benchmark/quality.py`)
- [x] **REPORT.md** with cost savings % and quality delta, broken down by difficulty tier and category (`benchmark/REPORT.md`)
- [x] **FAILURE_CASES.md** documenting misrouted/quality-regressed tasks with root-cause hypotheses and router policy mitigations (`benchmark/FAILURE_CASES.md`)
- [x] **Results pushed to Control Plane** in `BenchmarkRecord` format for dashboard display (`benchmark/report.py` / `push_records_to_control_plane`)
- [x] **CI smoke-test subset** (`benchmark/tasks/smoke_tasks.jsonl` + `benchmark/tests/test_smoke_benchmark.py`) + documented full/nightly run command

---

## Directory Layout

```
benchmark/
├── README.md                      # Package documentation and checklist (this file)
├── REPORT.md                      # Generated comprehensive benchmark report
├── FAILURE_CASES.md               # Detailed failure case analysis & misrouting register
├── tasks/
│   ├── tasks.jsonl                # 80 benchmark tasks (trivial, moderate, deep tiers)
│   └── smoke_tasks.jsonl          # 10 curated tasks for fast CI sanity checks (<5s)
├── runner.py                      # Dual-run benchmark harness (Router vs Always-Premium)
├── quality.py                     # Objective scoring & blind LLM-as-judge engine
├── report.py                      # Report generator, regression detector, and Control Plane publisher
├── benchmark_engine/
│   ├── __init__.py
│   └── main.py                    # FastAPI application (Port 8004) exposing benchmark endpoints
├── results/
│   ├── latest.json                # Latest full benchmark run records (BenchmarkRecord schema)
│   └── benchmark_run_*.json       # Timestamped historical evaluation runs
└── tests/
    ├── test_api.py                # FastAPI benchmark endpoints tests
    ├── test_benchmark_stub.py     # Health & scaffolding contract tests
    ├── test_quality.py            # Quality scoring & blind randomization tests
    ├── test_report.py             # Savings % math, aggregations, and report tests
    ├── test_runner.py             # Dual-run harness & pricing calculation tests
    ├── test_smoke_benchmark.py    # End-to-end smoke benchmark CI test
    └── test_tasks.py              # Task dataset validation tests
```

---

## Quick Start & Usage

### 1. Run CI Smoke Benchmark (Fast Sanity Check, ~10 Tasks)
```bash
python -m benchmark.runner --smoke
```
Runs the 10-task smoke subset covering trivial, moderate, and deep tiers. Generates `benchmark/REPORT.md` and updates `benchmark/results/latest.json`.

### 2. Run Full Comprehensive Benchmark (80 Tasks)
```bash
python -m benchmark.runner --full
```
Runs all 80 tasks, executes dual pipeline runs, calculates tier breakdowns, identifies regressions into `benchmark/FAILURE_CASES.md`, and pushes `BenchmarkRecord` entries to the Control Plane.

### 3. Running Against Live Endpoints vs Offline Contract Mock
- **Live HTTP Mode** (queries Router Core at `http://localhost:8001` and Model Gateway at `http://localhost:8002`):
  ```bash
  python -m benchmark.runner --full --live
  ```
- **Deterministic Contract Simulation** (offline / local dev / CI mode):
  ```bash
  python -m benchmark.runner --full --mock
  ```

### 4. Running the Test Suite
```bash
pytest benchmark/tests
```

### 5. Running the Benchmark Engine API Service
```bash
uvicorn benchmark.benchmark_engine.main:app --host 0.0.0.0 --port 8004 --reload
```

---

## Key Findings & Proof Metrics

From our 80-task comprehensive evaluation run:

| Metric | Router Pipeline | Baseline ('Always Strongest') | Performance Impact |
|---|---|---|---|
| **Total Cost** | **$0.014226** | **$0.029558** | **51.9% Cost Reduction** |
| **Average Quality** | **0.946 / 1.000** | **0.971 / 1.000** | **-0.025 Quality Delta (Comparable)** |
| **Average Latency** | **530.8 ms** | **1200.0 ms** | **55.8% Faster Execution** |

### Proof by Difficulty Tier:
- **Trivial Tier (28 tasks):** **100.0% cost savings** ($0.00 router cost via local Ollama `llama3.1:8b`) with **0.000 quality delta** (1.000 vs 1.000).
- **Moderate Tier (26 tasks):** **94.2% cost savings** (routed to cheap mid-tier `gpt-4o-mini`) with **0.000 quality delta** (0.962 vs 0.962).
- **Deep Tier (26 tasks):** **10.3% cost savings** (correctly protected on frontier `gpt-4o` to ensure reasoning accuracy, with near-baseline cost).
- **Multi-Part Compound Prompts (14 tasks):** **74.4% cost savings** with **0.000 quality delta**, proving that Router Core's subtask decomposition effectively isolates low-complexity subtasks without degrading the merged output.

See the full breakdown in [REPORT.md](file:///C:/Users/kamal/.gemini/antigravity-ide/scratch/Cost-LLM/benchmark/REPORT.md) and [FAILURE_CASES.md](file:///C:/Users/kamal/.gemini/antigravity-ide/scratch/Cost-LLM/benchmark/FAILURE_CASES.md).
