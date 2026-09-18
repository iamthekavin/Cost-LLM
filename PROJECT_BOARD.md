# Cost-LLM Project Board & Workstream Tracking

**Repository:** [iamthekavin/Cost-LLM](https://github.com/iamthekavin/Cost-LLM)  
**Coordination Model:** 4 parallel workstreams, independent packages, shared contracts.  
**Base Branch:** `main`

---

## Workstream Overview & Branch Assignments

| Workstream | Owner | Dedicated Git Branch | Package Directory | Port | Status |
|---|---|---|---|---|---|
| **Router Core & Task Decomposition** | Member A | `feature/router-core` | `router-core/` | `8001` | 🟡 Ready for Development |
| **Model Gateway & Adapters** | Member B | `feature/model-gateway` | `model-gateway/` | `8002` | 🟡 Ready for Development |
| **Transparency, Control & Dashboard** | Member C | `feature/control-plane` | `control-plane/` | `8003` | 🟡 Ready for Development |
| **Benchmarking & Cost-Quality Eval** | Member D | `feature/benchmark` | `benchmark/` | `8004` | 🟡 Ready for Development |

---

## Issue #1: Member A — Router Core & Task Decomposition

**Branch:** `feature/router-core`  
**Package:** `router-core/`  
**Owner:** Member A  
**Interface Contracts:** Consumes `RoutingRequest` (Contract A), emits `RoutingDecision` (Contract B), returns `FinalResponse` (Contract D).

### Deliverables Checklist
- [ ] **Complexity Scoring Engine**:
  - [ ] Implement semantic complexity analyzer (`0.0` to `1.0`).
  - [ ] Classify incoming prompts into `ReasoningDepth` enum (`trivial`, `moderate`, `deep`).
  - [ ] Support prompt token length heuristics and keyword/intent markers.
- [ ] **Task Decomposition (Splitter)**:
  - [ ] Detect compound/multi-part requests (e.g. "summarize this data AND generate a python chart").
  - [ ] Split compound requests into discrete, executable `SubtaskPrompt` units.
  - [ ] Preserve context dependency across subtasks.
- [ ] **Routing Policy Matcher**:
  - [ ] Route `trivial` subtasks to `local` tier (`llama3.1:8b` on Ollama).
  - [ ] Route `moderate` subtasks to `cheap` tier (`gpt-4o-mini` / `gemini-1.5-flash`).
  - [ ] Route `deep` subtasks to `premium` tier (`gpt-4o` / `claude-3-5-sonnet`).
  - [ ] Respect caller-provided `max_cost_usd` budget ceilings and `quality_floor`.
  - [ ] Support caller-provided `override_model` to bypass automatic classification.
- [ ] **Result Merger & Synthesis**:
  - [ ] Coordinate concurrent subtask calls to Model Gateway (`POST http://model-gateway:8002/v1/execute`).
  - [ ] Synthesize individual outputs into a coherent `final_answer`.
  - [ ] Assemble `subtask_breakdown` containing both decisions and execution metrics.
  - [ ] Aggregate total cost in USD and total roundtrip latency in milliseconds.
- [ ] **Testing & Verification**:
  - [ ] Unit tests for complexity classifier edge cases.
  - [ ] Unit tests for multi-part splitter and merger logic.
  - [ ] Mocked integration tests calling Model Gateway.

---

## Issue #2: Member B — Model Gateway & Unified Adapter

**Branch:** `feature/model-gateway`  
**Package:** `model-gateway/`  
**Owner:** Member B  
**Interface Contracts:** Consumes `RoutingDecision` (Contract B), returns `ModelCallResult` (Contract C).

### Deliverables Checklist
- [ ] **Unified Provider Interface (`POST /v1/execute`)**:
  - [ ] Implement provider-agnostic adapter accepting `RoutingDecision`.
  - [ ] Normalize varying provider outputs into standard `ModelCallResult`.
- [ ] **Local Model Adapter (Ollama)**:
  - [ ] Connect to local Ollama daemon (`http://localhost:11434` or Docker container).
  - [ ] Stream/invoke `llama3.1:8b` (or `mistral:7b`).
  - [ ] Handle connection drops and local daemon warm-up latency.
- [ ] **Hosted Model Adapters**:
  - [ ] OpenAI client adapter (`gpt-4o-mini`, `gpt-4o`).
  - [ ] Anthropic client adapter (`claude-3-5-haiku`, `claude-3-5-sonnet`).
  - [ ] Google Gemini client adapter (`gemini-1.5-flash`, `gemini-1.5-pro`).
- [ ] **Metering & Cost Engine**:
  - [ ] Accurate token counting (using `tiktoken` or provider usage metadata).
  - [ ] Maintain real-time token pricing table ($ / 1M prompt and completion tokens).
  - [ ] Calculate exact `cost_usd` per execution (local tier strictly $0.00).
  - [ ] Measure exact high-resolution `latency_ms`.
- [ ] **Resilience & Fallbacks**:
  - [ ] Catch rate-limits (HTTP 429) and timeouts with exponential backoff.
  - [ ] Automatic failover to `fallback_model` if primary model is unavailable.
- [ ] **Testing & Verification**:
  - [ ] Unit tests mocking each provider client.
  - [ ] Token count and cost calculation validation tests.

---

## Issue #3: Member C — Transparency, Control & Dashboard

**Branch:** `feature/control-plane`  
**Package:** `control-plane/`  
**Owner:** Member C  
**Interface Contracts:** Consumes `DecisionLogEntry` (Contract E), provides override policies to Router Core.

### Deliverables Checklist
- [ ] **Audit Logging & Persistence**:
  - [ ] Design async SQLAlchemy database schema for `DecisionLogEntry`.
  - [ ] Ingest logs via `POST /v1/logs` and support high-throughput async writes.
  - [ ] Expose query endpoints (`GET /v1/logs/{request_id}`, `GET /v1/logs?user_id=X&limit=50`).
- [ ] **Policy & Override Engine**:
  - [ ] Implement manual per-request and persistent user/tenant override rules.
  - [ ] Expose override management API (`GET /v1/overrides`, `POST /v1/overrides`, `DELETE /v1/overrides/{rule_id}`).
  - [ ] Support regex-based prompt overrides, tier ceilings, and user whitelist rules.
- [ ] **Control Plane Dashboard (UI)**:
  - [ ] Build a sleek, responsive administrative dashboard (Dark mode, glassmorphism).
  - [ ] Live feed of routing decisions with subtask breakdowns.
  - [ ] Real-time cost, token, and tier distribution visualizations.
  - [ ] Interactive UI controls to add, toggle, and test routing overrides on the fly.
- [ ] **Testing & Verification**:
  - [ ] Unit tests for database CRUD and schema migrations.
  - [ ] API tests for log ingestion and override rules engine.
  - [ ] UI integration test.

---

## Issue #4: Member D — Benchmarking & Cost-Quality Evaluation

**Branch:** `feature/benchmark`  
**Package:** `benchmark/`  
**Owner:** Member D  
**Interface Contracts:** Ingests `DecisionLogEntry` (Contract E), emits and stores `BenchmarkRecord` (Contract F).

### Deliverables Checklist
- [ ] **Baseline Cost Calculator**:
  - [ ] Calculate shadow baseline cost for every prompt as if serviced by the "always-strongest" model (`gpt-4o` / `claude-3-5-sonnet`).
  - [ ] Compute exact percentage cost savings: `((baseline_cost - router_cost) / baseline_cost) * 100`.
- [ ] **Objective Quality Evaluation Engine**:
  - [ ] Implement LLM-as-a-judge or automated reference scoring for output quality (`0.0` to `1.0`).
  - [ ] Measure quality difference: `router_quality_score - baseline_quality_score`.
  - [ ] Segment evaluations across `task_category` (e.g. coding, summarization, extraction, reasoning).
- [ ] **Benchmark Ingestion & Storage**:
  - [ ] Ingest decision logs asynchronously via background worker or `POST /v1/benchmark/evaluate`.
  - [ ] Persist `BenchmarkRecord` entries in persistent storage.
- [ ] **Benchmark Reporting & Analytics**:
  - [ ] Expose `GET /v1/benchmark/summary` computing cumulative savings, average quality delta, and tier breakdown.
  - [ ] Generate downloadable Markdown and CSV evaluation reports.
- [ ] **Testing & Verification**:
  - [ ] Unit tests for cost savings formula and edge cases ($0 router cost).
  - [ ] Unit tests for quality delta scoring.
