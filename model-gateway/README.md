# Cost-LLM Model Gateway (Member B)

The **Model Gateway** provides a unified, decoupled interface to execute prompts against both local and hosted large language models. It handles provider-specific API nuances, extracts accurate token metrics, computes financial costs via a shared pricing registry (`models.yaml`), implements timeout/retry resilience, executes automatic fallbacks, and supports high-throughput concurrent batch calling.

---

## Deliverables Checklist

- [x] **Working local model adapter (Ollama)** — Satisfies the "at least one local model" requirement; verified with Docker Compose and local daemon.
- [x] **Cheap hosted adapter + Premium hosted adapter** — Both cost-accurate against `pricing.yaml` / `models.yaml`.
- [x] **`/call` & `/v1/execute` endpoints** — Supports configurable timeouts, exponential backoff retries for hosted models, and seamless `fallback_model` path handling.
- [x] **Concurrent batch calling (`/call/batch`)** — Executes multi-part subtasks in parallel via `asyncio.gather`, dramatically reducing total latency.
- [x] **`models.yaml` registry** — Versioned model specifications and pricing table shared directly with Member A (Router Core).
- [x] **Comprehensive test suite** — Unit and integration tests covering response normalization, fallback recovery, concurrency latency improvement, and pricing accuracy.

---

## Architecture & Component Layout

```
model-gateway/
├── .env.example                # Example environment variables
├── models.yaml / pricing.yaml   # Canonical pricing & model registry (shared with Router Core)
├── config.py                   # Configuration and pricing calculator
├── normalize.py                # Response normalization & wrapper stripper
├── main.py                     # FastAPI application entrypoint
├── providers/                  # Backend model adapters
│   ├── base.py                 # Abstract BaseProvider interface
│   ├── local_ollama.py         # Ollama HTTP client ($0.00 cost, prompt/eval token counting)
│   ├── cheap_hosted.py         # Cheap tier: gpt-4o-mini, gemini-1.5-flash, claude-3-5-haiku
│   └── premium_hosted.py       # Premium baseline: gpt-4o, claude-3-5-sonnet, gemini-1.5-pro
├── tests/                      # Pytest test suite
│   ├── test_gateway.py         # API endpoints & /health validation
│   ├── test_providers.py       # Provider adapters with mocked HTTP responses
│   ├── test_normalization.py   # Markdown fence and conversational text stripping
│   ├── test_fallback.py        # Retries and fallback_model recovery
│   ├── test_concurrency.py     # Concurrent batch vs sequential latency verification
│   └── test_pricing.py         # Mathematical cost verification matching pricing.yaml
├── Dockerfile                  # Containerization specification
└── README.md                   # This guide and documentation
```

---

## Local Model (Ollama) Setup & Bring-Up

### Step 1: Start Ollama via Docker Compose
From the repository root:
```bash
docker compose up -d ollama
```

### Step 2: Pull the Recommended Local Model
Pull the standard 8B parameter model (`llama3.1:8b`):
```bash
docker exec -it cost-llm-ollama ollama pull llama3.1:8b
```

Alternatively, if running Ollama natively on host:
```bash
ollama run llama3.1:8b
```

### Step 3: Verify Gateway Health Probe
Query the `/health` endpoint:
```bash
curl http://localhost:8002/health
```
**Response:**
```json
{
  "status": "ok",
  "service": "model-gateway",
  "version": "1.0.0",
  "ollama_reachable": true,
  "ollama_details": {
    "reachable": true,
    "models": ["llama3.1:8b:latest"],
    "has_target_model": true
  },
  "available_models": ["llama3.1:8b", "gpt-4o-mini", "claude-3-5-haiku", "gemini-1.5-flash", "gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"]
}
```
*(If Ollama is not running, the endpoint returns `"status": "degraded"` with `"ollama_reachable": false` rather than crashing).*

---

## API Endpoints

### 1. Execute Subtask (`POST /call` or `POST /v1/execute`)
Dispatches a subtask to the selected model with retry and fallback handling.

**Request:**
```json
{
  "subtask_id": "sub_01",
  "subtask_text": "Extract table data: Q1: $4M, Q2: $5M",
  "chosen_model": "llama3.1:8b",
  "fallback_model": "gpt-4o-mini",
  "timeout_s": 30.0,
  "params": { "temperature": 0.2 }
}
```

**Response (`ModelCallResult`):**
```json
{
  "subtask_id": "sub_01",
  "model_used": "llama3.1:8b",
  "tokens_in": 18,
  "tokens_out": 24,
  "latency_ms": 142.5,
  "cost_usd": 0.000000,
  "raw_output": "{\"Q1\": 4000000, \"Q2\": 5000000}",
  "error": null
}
```

### 2. Concurrent Batch Calling (`POST /call/batch`)
Executes multiple subtasks concurrently via `asyncio.gather`.

**Request:**
```json
{
  "items": [
    { "subtask_id": "part_1", "subtask_text": "Summarize intro", "chosen_model": "llama3.1:8b" },
    { "subtask_id": "part_2", "subtask_text": "Extract financials", "chosen_model": "gpt-4o-mini" },
    { "subtask_id": "part_3", "subtask_text": "Architect strategy", "chosen_model": "gpt-4o" }
  ]
}
```

**Latency Benchmark (Concurrent vs Sequential):**
When running 3 subtasks with average latency ~200ms each:
- **Sequential Execution**: `200ms + 200ms + 200ms = ~600ms`
- **Concurrent Batch Execution**: `max(200ms, 200ms, 200ms) = ~215ms`
- **Latency Improvement**: **~64% reduction in end-to-end user latency!**

---

## Model Registry & Pricing (`pricing.yaml`)

Pricing is maintained centrally in `shared/models.yaml` and mirrored in `model-gateway/pricing.yaml`:

| Model | Tier | Provider | Input Cost ($/1M) | Output Cost ($/1M) | Default Timeout |
|---|---|---|---|---|---|
| `llama3.1:8b` | `local` | Ollama | **$0.00** | **$0.00** | 60s |
| `gpt-4o-mini` | `cheap` | OpenAI | $0.15 | $0.60 | 30s |
| `gemini-1.5-flash` | `cheap` | Google | $0.075 | $0.30 | 30s |
| `claude-3-5-haiku` | `cheap` | Anthropic | $0.80 | $4.00 | 30s |
| `gpt-4o` | `premium` (Baseline) | OpenAI | $2.50 | $10.00 | 45s |
| `claude-3-5-sonnet` | `premium` | Anthropic | $3.00 | $15.00 | 45s |
| `gemini-1.5-pro` | `premium` | Google | $1.25 | $5.00 | 45s |

---

## Running Unit Tests

```bash
pytest model-gateway/tests -v
```
To run linting:
```bash
ruff check model-gateway/
```
