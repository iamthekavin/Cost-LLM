# Cost-LLM

**Cost-LLM** is an intelligent, transparent, and controllable multi-model LLM router that sits in front of language models of differing cost and capability (including local self-hosted models). It routes each incoming request (or decomposed subtasks) to the cheapest model capable of handling it accurately, benchmarking financial savings against an "always-strongest" baseline while preserving output quality.

[![Cost-LLM CI](https://github.com/iamthekavin/Cost-LLM/actions/workflows/ci.yml/badge.svg)](https://github.com/iamthekavin/Cost-LLM/actions/workflows/ci.yml)
![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## Key Features

1. **Intelligent Complexity Scoring**: Evaluates prompt semantic intensity and assigns a complexity score (`0.0` to `1.0`) and reasoning depth (`trivial`, `moderate`, `deep`).
2. **Cost-Optimal Routing**: Dynamically maps tasks to the lowest-cost viable model tier (`local`, `cheap`, `premium`).
3. **Task Decomposition & Synthesis**: Decomposes multi-part compound queries, dispatches subtasks concurrently to best-fit models, and merges results into a single answer.
4. **End-to-End Transparency**: Every routing decision is audited with model choice, token usage, latency, monetary cost, and rationale.
5. **Control & Overrides**: Supports per-request caller overrides and administrative policy rules (whitelists, tier caps, emergency overrides).
6. **Objective Benchmarking**: Measures cost saved vs. an "always use the strongest model" (e.g. GPT-4o) baseline with automated quality scoring and delta analytics.

---

## Technology Stack & Justification

| Layer | Selection | Justification |
|---|---|---|
| **Core Runtime** | **Python 3.11** | Fast async I/O, modern typing features, high performance across all 4 microservices. |
| **API Framework** | **FastAPI + Uvicorn** | Automatic OpenAPI/Swagger generation, high throughput async endpoints, native Pydantic validation. |
| **Data Contracts** | **Pydantic v2** | Strict shared schema validation, instant JSON schema generation, zero-boilerplate serialization. |
| **Local Model Tier** | **Ollama (`llama3.1:8b`)** | $0.00 marginal token cost, local privacy, sub-300ms latency for trivial/formatting tasks. |
| **Mid-Tier Hosted** | **`gpt-4o-mini` / `gemini-1.5-flash`** | Extremely low API cost (~$0.15/1M prompt tokens), high speed for summarization & extraction. |
| **Top-Tier Baseline** | **`gpt-4o` / `claude-3-5-sonnet`** | Gold-standard reasoning ceiling; serves as the objective baseline to quantify cost savings and quality delta. |
| **Inter-Service Bus** | **Internal HTTP / JSON REST** | Decoupled, lightweight, easy to debug, mock, and monitor without message broker overhead. |
| **Log & Metric Store** | **SQLite (Dev) / PostgreSQL (Prod via SQLAlchemy)** | SQLite provides zero-dependency setup for local development; SQLAlchemy allows seamless Docker toggle to PostgreSQL. |

---

## Monorepo Layout

```
Cost-LLM/
├── README.md                           # Project overview, stack rationale, and quickstart
├── PROJECT_BOARD.md                    # Workstream deliverables and issue tracker
├── docker-compose.yml                  # Gateway + Control Plane + Router + Benchmark + Ollama
├── pyproject.toml                      # Monorepo test & lint configuration
├── docs/
│   ├── ARCHITECTURE.md                 # System topology diagrams, sequence flow, failure modes
│   └── INTERFACE_CONTRACT.md           # Formal JSON schema specifications for all 6 contracts
├── shared/                             # Shared Pydantic contracts and JSON schemas
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── schemas/
│   │   ├── contracts.py                # Single source of truth for all schemas
│   │   ├── export_schemas.py           # Utility script to export static .json schemas
│   │   └── json/                       # Exported static JSON schemas for non-Python callers
│   └── tests/
│       └── test_contracts.py           # Tests validating contract serialization
├── router-core/                        # Member A: Router Core & Task Decomposition
│   ├── router_core/
│   │   └── main.py                     # FastAPI service (Port 8001)
│   ├── tests/                          # Pytest unit tests
│   ├── requirements.txt
│   └── Dockerfile
├── model-gateway/                      # Member B: Model Gateway & Unified Adapter
│   ├── model_gateway/
│   │   └── main.py                     # FastAPI service (Port 8002)
│   ├── tests/                          # Pytest unit tests
│   ├── requirements.txt
│   └── Dockerfile
├── control-plane/                      # Member C: Transparency, Control & Dashboard
│   ├── control_plane/
│   │   └── main.py                     # FastAPI service & Dashboard (Port 8003)
│   ├── tests/                          # Pytest unit tests
│   ├── requirements.txt
│   └── Dockerfile
├── benchmark/                          # Member D: Benchmarking & Evaluation Engine
│   ├── benchmark_engine/
│   │   └── main.py                     # FastAPI service (Port 8004)
│   ├── tests/                          # Pytest unit tests
│   ├── requirements.txt
│   └── Dockerfile
└── .github/
    └── workflows/
        └── ci.yml                      # Matrix CI testing all 5 packages independently on PR
```

---

## Team Structure & Workstreams

| Workstream | Owner | Dedicated Git Branch | Directory | Primary Deliverable |
|---|---|---|---|---|
| **Router Core & Decomposition** | Member A | `feature/router-core` | `router-core/` | Complexity scoring, task splitter/merger, tier selector |
| **Model Gateway** | Member B | `feature/model-gateway` | `model-gateway/` | Unified local (Ollama) & hosted model execution with token metering |
| **Control Plane & UI** | Member C | `feature/control-plane` | `control-plane/` | Decision audit logging, override rules engine, transparency dashboard |
| **Benchmark & Evaluation** | Member D | `feature/benchmark` | `benchmark/` | Shadow baseline execution, cost savings calculation, quality delta scoring |

Detailed checklists for each member are tracked in [PROJECT_BOARD.md](file:///docs/../PROJECT_BOARD.md).

---

## Shared Interface Contracts

All four workstreams develop in parallel against locked schemas in `shared/schemas/contracts.py` and [docs/INTERFACE_CONTRACT.md](file:///docs/INTERFACE_CONTRACT.md):

1. **`RoutingRequest`**: Caller input payload `{ request_id, user_id, prompt, subtasks?, max_cost_usd?, quality_floor?, override_model?, metadata }`.
2. **`RoutingDecision`**: Router Core decision per subtask `{ request_id, subtask_id, subtask_text, complexity_score, reasoning_depth, chosen_model, chosen_tier, routing_reason, fallback_model?, overridden_by_user, timestamp }`.
3. **`ModelCallResult`**: Model Gateway execution result `{ subtask_id, model_used, tokens_in, tokens_out, latency_ms, cost_usd, raw_output, error? }`.
4. **`FinalResponse`**: Caller merged output `{ request_id, final_answer, subtask_breakdown, total_cost_usd, total_latency_ms }`.
5. **`DecisionLogEntry`**: Control Plane transparency audit record (superset of decision + result + override provenance).
6. **`BenchmarkRecord`**: Benchmark evaluation record `{ request_id, router_cost_usd, baseline_cost_usd, cost_savings_pct, router_quality_score, baseline_quality_score, quality_delta, task_category, timestamp }`.

---

## Getting Started

### Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/iamthekavin/Cost-LLM.git
   cd Cost-LLM
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. **Install shared contracts in editable mode**:
   ```bash
   pip install -e shared
   ```

4. **Install all service dependencies**:
   ```bash
   pip install -r router-core/requirements.txt
   pip install -r model-gateway/requirements.txt
   pip install -r control-plane/requirements.txt
   pip install -r benchmark/requirements.txt
   ```

5. **Run the test suite across all packages**:
   ```bash
   pytest
   ```

6. **Lint code with Ruff**:
   ```bash
   ruff check .
   ```

---

## Running with Docker Compose

To spin up the entire cluster together, including the local Ollama instance:

```bash
docker compose up --build
```

### Service Endpoints

| Service | Port | Endpoint URL | Swagger Docs |
|---|---|---|---|
| **Router Core** | `8001` | `http://localhost:8001` | `http://localhost:8001/docs` |
| **Model Gateway** | `8002` | `http://localhost:8002` | `http://localhost:8002/docs` |
| **Control Plane** | `8003` | `http://localhost:8003` | `http://localhost:8003/docs` |
| **Control Plane UI** | `8003` | `http://localhost:8003/dashboard` | N/A |
| **Benchmark Engine** | `8004` | `http://localhost:8004` | `http://localhost:8004/docs` |
| **Ollama (Local LLM)** | `11434` | `http://localhost:11434` | N/A |

To pull the default local model into Ollama:
```bash
docker exec -it cost-llm-ollama ollama pull llama3.1:8b
```
