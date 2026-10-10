# Cost-Optimized LLM Router

An intelligent, transparent, and controllable multi-model LLM router designed to drastically reduce enterprise AI expenditure while maintaining frontier-grade output quality.

---

## Executive Summary & Background

Every request sent to a frontier large language model (e.g. `o1-preview`, `gpt-4o`) incurs high financial cost. Much of this waste originates from using monolithic frontier models for routine tasks—such as extracting dates from invoices, classifying tickets, or formatting JSON—which can be performed with equal fidelity on a local zero-cost model or a low-cost cloud model.

This system solves the challenge by:
1. **Assessing Task Complexity**: Analyzing linguistic structure, reasoning depth, and semantic intent.
2. **Decomposing Compound Requests**: Automatically breaking multi-part requests into discrete subtasks (e.g. local extraction + cloud reasoning) and synthesizing the results.
3. **Multi-Tier Routing**: Routing each part to the cheapest capable model tier.
4. **Providing Full Transparency**: Generating an audit trace for every decision with real-time cost savings vs. the frontier baseline.
5. **Trade-Off Benchmarking**: Providing an empirical benchmarking suite measuring cost reduction, quality retention, and Pareto trade-off optimality.

---

## Architecture Overview

```
                      ┌──────────────────────────────────────────────┐
                      │          User Request / API / UI             │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │     Task Classifier & Complexity Scorer      │
                      │  - Multi-dimensional scoring (0.00 to 1.00)  │
                      │  - Intent classification & PII detection     │
                      │  - Decomposition potential analysis          │
                      └──────────────────────┬───────────────────────┘
                                             │
                       Single-Part           │           Multi-Part
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
         ┌─────────────────────────┐                   ┌─────────────────────────┐
         │      Tier Selector      │                   │    Subtask Decomposer   │
         │ (Balanced / Cost-First) │                   │  (Splits into subtasks) │
         └────────────┬────────────┘                   └────────────┬────────────┘
                      │                                             │
                      │                                    Subtask 1 │ Subtask 2 │ Subtask 3
                      │                                              ▼
                      │                                ┌─────────────────────────┐
                      │                                │ Subtask Routing Matrix  │
                      │                                │ (Routes each subtask)   │
                      │                                └────────────┬────────────┘
                      │                                             │
                      ├─────────────────────────────────────────────┤
                      ▼                                             ▼
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │                               Model Registry                                    │
   │  ┌──────────────────┐ ┌───────────────────┐ ┌────────────────┐ ┌─────────────┐  │
   │  │ Tier 1: Local    │ │ Tier 2: Low-Cost  │ │ Tier 3: Balanced│ │ Tier 4:     │  │
   │  │ Ollama Llama 3.2 │ │ GPT-4o-mini /     │ │ GPT-4o /       │ │ Frontier    │  │
   │  │ ($0.00 / 1M)     │ │ Haiku ($0.15/1M)  │ │ Sonnet ($2.50) │ │ o1 ($15.00) │  │
   │  └──────────────────┘ └───────────────────┘ └────────────────┘ └─────────────┘  │
   └────────────────────────────────────────┬────────────────────────────────────────┘
                                            │
                                            ▼
                           ┌──────────────────────────────────┐
                           │  Synthesizer & Aggregator Engine │
                           │  (Combines subtask outputs)      │
                           └────────────────┬─────────────────┘
                                            │
                                            ▼
                           ┌──────────────────────────────────┐
                           │    Transparency & Trace Engine   │
                           │  - Explanation of decisions      │
                           │  - Cost breakdown & % savings    │
                           │  - Real-time audit metrics       │
                           └────────────────┬─────────────────┘
                                            │
                                            ▼
                           ┌──────────────────────────────────┐
                           │   Web Dashboard & Rich CLI UI    │
                           │  (Interactive playground, evals, │
                           │   admin overrides, live charts)  │
                           └──────────────────────────────────┘
```

---

## Model Portfolio & Pricing Reference

| Tier | Default Model | Prompt Cost / 1M | Completion Cost / 1M | Latency | Target Workload |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Tier 1: Local** | `llama3.2:3b` | **$0.00** | **$0.00** | ~450ms | Entity extraction, formatting, JSON conversion, air-gapped tasks |
| **Tier 2: Low-Cost** | `gpt-4o-mini` | $0.15 | $0.60 | ~520ms | Ticket triage, classification, summarization, high-throughput |
| **Tier 3: Balanced** | `gpt-4o` | $2.50 | $10.00 | ~850ms | Algorithmic code, software architecture, multi-factor analysis |
| **Tier 4: Frontier** | `o1-preview` | $15.00 | $60.00 | ~3200ms | Formal mathematical deduction, deep economic/logic proofs |

---

## Key Features

### 1. Transparency & Auditability
Every request produces a `RoutingTrace` detailing:
- **Complexity Score**: Numerical score $\in [0.00, 1.00]$ computed from linguistic and semantic indicators.
- **Natural Language Rationale**: Explicit justification for the selected model.
- **Cost Accounting**: Exact prompt and completion tokens, dollar cost, baseline cost (always frontier), and percentage saved.

### 2. Multi-Part Prompt Decomposition
When an incoming query has compound requirements (e.g. *“1. Extract dates from invoice, 2. Classify authorization limit, 3. Conduct fiscal compliance audit”*), the router:
1. Decomposes the query into ordered `SubTask` nodes.
2. Routes easy steps (extraction/classification) to Local or Low-Cost tiers.
3. Reserves the Frontier tier exclusively for the reasoning step.
4. Aggregates results into a single synthesized response with complete model provenance.

### 3. Administrative Control & Overrides
- **Policy Presets**:
  - `balanced`: Default Pareto-optimal setting (~70-85% savings with ~98% quality).
  - `cost_first`: Aggressive savings targeting local hardware.
  - `quality_first`: Prioritizes balanced/frontier models, routing only trivial formatting locally.
  - `local_only`: 100% on-premise execution (zero API spend, strict privacy).
- **Manual Overrides**: Administrators or users can force a specific model or tier for any request.

### 4. Benchmarking & Quality-Cost Evaluation
The built-in empirical benchmarking suite compares 4 strategies across standard enterprise tasks:
1. **Always Strongest** (Baseline): 100% frontier models ($$$$).
2. **Always Local**: 100% local model ($0 API cost, degraded on complex logic).
3. **Always Low-Cost**: 100% small cloud model.
4. **Dynamic LLM Router (Ours)**: Pareto-optimal dynamic routing with decomposition.

---

## Getting Started

### Prerequisites
- Python 3.11+
- Local Ollama daemon running `llama3.2:3b` (optional, high-fidelity local fallback emulation included)

### Installation
```bash
git clone https://github.com/iamthekavin/Cost-LLM.git
cd Cost-LLM
pip install fastapi uvicorn pydantic rich python-dotenv pytest pytest-asyncio httpx
```

---

## Usage

### 1. Interactive Web Dashboard
Launch the dashboard:
```bash
python main.py serve --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser:
- **Live Playground**: Submit queries, preview decomposition plans, and view live cost savings.
- **Transparency Card**: Real-time cost comparison vs baseline and routing rationale.
- **Benchmark Studio**: Run automated benchmark suites and view Pareto scatter charts and category breakdowns.

### 2. Rich Terminal CLI

#### Route a Single Task:
```bash
python main.py route "Extract all dates and totals from invoice #1029, dated 2026-05-12 with total $3,450.00."
```

#### Route a Multi-Part Request:
```bash
python main.py route "1. Extract the invoice total and customer name from: 'Customer: Stark Labs, Invoice Total: $85,000.00, Net 30'. 2. Classify if this requires executive board approval given a $50k threshold. 3. Conduct a multi-step audit risk analysis on potential compliance liabilities under corporate GAAP rules."
```

#### Enforce Administrative Override:
```bash
python main.py route "Extract dates from text" --override gpt-4o
```

#### Run Empirical Benchmarking Suite:
```bash
python main.py benchmark
```

#### List Model Portfolio & Pricing:
```bash
python main.py models
```

---

## Automated Verification & Testing

Run all unit and integration tests:
```bash
python -m pytest -v
```
All 19 test suites test:
- Task classification & complexity hierarchy
- Single-task and multi-task routing under all policies
- Automatic prompt decomposition and aggregation
- Exact token pricing formulas and savings calculations
- Multi-strategy benchmarking suite execution
