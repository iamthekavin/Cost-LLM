# Cost-LLM Interface Contract Specification

**Version:** `1.0.0`  
**Status:** Canonical & Locked for Parallel Workstreams  
**Consumers:** Router Core (Member A), Model Gateway (Member B), Control Plane (Member C), Benchmark (Member D)

---

## 1. Overview & Protocol Principles

All services communicate via internal **HTTP/JSON REST** endpoints. Every payload must strictly adhere to the schemas defined in this document and implemented in `shared/schemas/contracts.py`.

1. **No Breaking Modifications**: No team member may alter field types, rename properties, or remove required fields without cross-team RFC consensus.
2. **Extensibility**: All schemas permit additional metadata via `metadata` objects or non-breaking optional fields (`model_config = ConfigDict(extra="allow")`).
3. **Idempotency & Tracing**: Every flow originates with a unique `request_id` (UUIDv4) that propagates through every service, subtask, log entry, and benchmark evaluation.
4. **Timezone Standardization**: All timestamps are formatted according to **ISO 8601 UTC** (e.g. `2026-09-18T05:30:00.000000Z`).
5. **Monetary Standardization**: All monetary values (`cost_usd`, `max_cost_usd`, `total_cost_usd`) are expressed in US Dollars ($USD) as floating point numbers with 6-decimal precision.

---

## 2. Common Enums & Subtypes

### 2.1 ReasoningDepth
Enum representing the estimated cognitive intensity required to resolve a prompt:
- `"trivial"`: Simple lookups, basic factual questions, single-turn formatting, light extraction. Handled by local tier models.
- `"moderate"`: Multi-paragraph summarization, straightforward code generation, conversational synthesis, structured JSON translation. Handled by cheap/mid-tier hosted models.
- `"deep"`: Frontier reasoning, complex architecture/math proofs, delicate multi-constraint logic, multi-step code refactoring. Handled by premium frontier models.

### 2.2 ModelTier
Enum representing model operating and pricing tier:
- `"local"`: Self-hosted local instance (Ollama). Cost: $0.00 / token. Latency: Low-to-moderate based on local GPU/CPU.
- `"cheap"`: Small/mid hosted API (`gpt-4o-mini`, `claude-3-5-haiku`, `gemini-1.5-flash`). Cost: ~$0.15 - $0.60 per 1M tokens. Latency: High throughput, low latency.
- `"premium"`: Frontier hosted API (`gpt-4o`, `claude-3-5-sonnet`, `gemini-1.5-pro`). Cost: ~$2.50 - $15.00 per 1M tokens. Serves as quality ceiling and baseline.

---

## 3. Contract A: `RoutingRequest`

**Sender:** Client / Caller (User Application, API Gateway, CLI)  
**Receiver:** Router Core (`POST /v1/route`)  
**Purpose:** Defines an incoming prompt, user context, budget/quality constraints, and optional caller-specified overrides.

### JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RoutingRequest",
  "type": "object",
  "required": ["request_id", "user_id", "prompt"],
  "properties": {
    "request_id": {
      "type": "string",
      "description": "Unique UUID for the incoming caller request"
    },
    "user_id": {
      "type": "string",
      "description": "Caller or tenant identifier for quota, tracking, and telemetry"
    },
    "prompt": {
      "type": "string",
      "description": "Raw prompt text submitted by the user"
    },
    "subtasks": {
      "type": ["array", "null"],
      "description": "Optional pre-decomposed subtasks. If null or empty, Router Core will evaluate and split if needed.",
      "items": {
        "type": "object",
        "required": ["subtask_id", "prompt"],
        "properties": {
          "subtask_id": { "type": "string" },
          "prompt": { "type": "string" },
          "context": { "type": ["string", "null"] }
        }
      },
      "default": null
    },
    "max_cost_usd": {
      "type": ["number", "null"],
      "minimum": 0.0,
      "description": "Optional maximum cost cap in USD for this entire request"
    },
    "quality_floor": {
      "type": ["number", "null"],
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Minimum acceptable quality score threshold"
    },
    "override_model": {
      "type": ["string", "null"],
      "description": "Optional model name to force routing (bypasses algorithmic classifier)",
      "default": null
    },
    "metadata": {
      "type": "object",
      "description": "Arbitrary client-provided key-value metadata",
      "default": {}
    }
  }
}
```

### Example Payload
```json
{
  "request_id": "8f3b610c-99c2-466d-9bb3-772b7a421fa1",
  "user_id": "user_49102",
  "prompt": "Extract the key metrics from this revenue report and write a python script to forecast next quarter.",
  "subtasks": null,
  "max_cost_usd": 0.03,
  "quality_floor": 0.85,
  "override_model": null,
  "metadata": {
    "environment": "production",
    "client_version": "1.4.0"
  }
}
```

---

## 4. Contract B: `RoutingDecision`

**Sender:** Router Core  
**Receiver:** Model Gateway (`POST /v1/execute`), Control Plane (`POST /v1/decisions`), Benchmark  
**Purpose:** Emitted by Router Core for every evaluated task/subtask detailing complexity score, chosen model/tier, and justification.

### JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RoutingDecision",
  "type": "object",
  "required": [
    "request_id",
    "subtask_id",
    "subtask_text",
    "complexity_score",
    "reasoning_depth",
    "chosen_model",
    "chosen_tier",
    "routing_reason"
  ],
  "properties": {
    "request_id": {
      "type": "string",
      "description": "Parent request identifier"
    },
    "subtask_id": {
      "type": "string",
      "description": "Identifier for this particular subtask"
    },
    "subtask_text": {
      "type": "string",
      "description": "The prompt or decomposed subtask text dispatched for execution"
    },
    "complexity_score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Computed complexity score between 0.0 (trivial) and 1.0 (deep reasoning)"
    },
    "reasoning_depth": {
      "type": "string",
      "enum": ["trivial", "moderate", "deep"]
    },
    "chosen_model": {
      "type": "string",
      "description": "Identifier of the target model (e.g. llama3.1:8b, gpt-4o-mini, gpt-4o)"
    },
    "chosen_tier": {
      "type": "string",
      "enum": ["local", "cheap", "premium"]
    },
    "routing_reason": {
      "type": "string",
      "description": "Human-readable explanation of why this model/tier was selected"
    },
    "fallback_model": {
      "type": ["string", "null"],
      "description": "Backup model if chosen_model encounters timeout or error",
      "default": null
    },
    "overridden_by_user": {
      "type": "boolean",
      "description": "True if an override policy or user param bypassed the routing classifier",
      "default": false
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

### Example Payload
```json
{
  "request_id": "8f3b610c-99c2-466d-9bb3-772b7a421fa1",
  "subtask_id": "subtask_01",
  "subtask_text": "Extract table values: Q1: 4.2M, Q2: 4.9M, Q3: 5.1M",
  "complexity_score": 0.15,
  "reasoning_depth": "trivial",
  "chosen_model": "llama3.1:8b",
  "chosen_tier": "local",
  "routing_reason": "Structured tabular data extraction requires low reasoning complexity; local Ollama instance satisfies quality floor.",
  "fallback_model": "gpt-4o-mini",
  "overridden_by_user": false,
  "timestamp": "2026-09-18T05:30:01.120000Z"
}
```

---

## 5. Contract C: `ModelCallResult`

**Sender:** Model Gateway  
**Receiver:** Router Core (for merger), Control Plane (for audit), Benchmark  
**Purpose:** Standardized normalized response returned by the Model Gateway after invoking either a local model or a cloud provider.

### JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ModelCallResult",
  "type": "object",
  "required": [
    "subtask_id",
    "model_used",
    "tokens_in",
    "tokens_out",
    "latency_ms",
    "cost_usd",
    "raw_output"
  ],
  "properties": {
    "subtask_id": {
      "type": "string",
      "description": "Identifier of the executed subtask"
    },
    "model_used": {
      "type": "string",
      "description": "Exact model that executed the call (including provider/version)"
    },
    "tokens_in": {
      "type": "integer",
      "minimum": 0,
      "description": "Prompt input tokens counted"
    },
    "tokens_out": {
      "type": "integer",
      "minimum": 0,
      "description": "Completion output tokens generated"
    },
    "latency_ms": {
      "type": "number",
      "minimum": 0.0,
      "description": "Roundtrip execution latency in milliseconds"
    },
    "cost_usd": {
      "type": "number",
      "minimum": 0.0,
      "description": "Computed execution cost in USD"
    },
    "raw_output": {
      "type": "string",
      "description": "Normalized text content generated by the model"
    },
    "error": {
      "type": ["string", "null"],
      "description": "Error message if invocation failed",
      "default": null
    }
  }
}
```

### Example Payload
```json
{
  "subtask_id": "subtask_01",
  "model_used": "llama3.1:8b",
  "tokens_in": 128,
  "tokens_out": 42,
  "latency_ms": 182.4,
  "cost_usd": 0.000000,
  "raw_output": "{\"Q1\": 4200000, \"Q2\": 4900000, \"Q3\": 5100000}",
  "error": null
}
```

---

## 6. Contract D: `FinalResponse`

**Sender:** Router Core  
**Receiver:** Original Caller  
**Purpose:** Synthesized final answer returned after merging all subtask outputs, accompanied by full audit breakdown, total monetary cost, and total latency.

### JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "FinalResponse",
  "type": "object",
  "required": [
    "request_id",
    "final_answer",
    "subtask_breakdown",
    "total_cost_usd",
    "total_latency_ms"
  ],
  "properties": {
    "request_id": {
      "type": "string",
      "description": "Original request identifier"
    },
    "final_answer": {
      "type": "string",
      "description": "Merged and synthesized final response for the user"
    },
    "subtask_breakdown": {
      "type": "array",
      "description": "Auditable array of each subtask routing decision and execution result",
      "items": {
        "type": "object",
        "required": ["subtask_id", "decision"],
        "properties": {
          "subtask_id": { "type": "string" },
          "decision": { "$ref": "#/$defs/RoutingDecision" },
          "result": { "$ref": "#/$defs/ModelCallResult" }
        }
      }
    },
    "total_cost_usd": {
      "type": "number",
      "minimum": 0.0,
      "description": "Summed financial cost across all subtask executions"
    },
    "total_latency_ms": {
      "type": "number",
      "minimum": 0.0,
      "description": "Total roundtrip latency from request reception to response emission"
    }
  }
}
```

---

## 7. Contract E: `DecisionLogEntry`

**Sender:** Router Core / Model Gateway / Control Plane Middleware  
**Receiver:** Control Plane (`POST /v1/logs`, `GET /v1/logs/{request_id}`)  
**Storage:** SQLite / PostgreSQL database managed by Control Plane  
**Purpose:** Comprehensive audit log entry stored for transparency, security analysis, policy compliance, and UI dashboard visualization.

### JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "DecisionLogEntry",
  "type": "object",
  "required": [
    "request_id",
    "subtask_id",
    "routing_decision"
  ],
  "properties": {
    "request_id": {
      "type": "string",
      "description": "Request identifier"
    },
    "subtask_id": {
      "type": "string",
      "description": "Subtask identifier"
    },
    "user_id": {
      "type": ["string", "null"],
      "description": "Caller or tenant ID"
    },
    "prompt_text": {
      "type": ["string", "null"],
      "description": "Prompt content"
    },
    "routing_decision": {
      "$ref": "#/$defs/RoutingDecision"
    },
    "model_call_result": {
      "type": ["object", "null"],
      "$ref": "#/$defs/ModelCallResult",
      "default": null
    },
    "override_details": {
      "type": "object",
      "properties": {
        "is_overridden": { "type": "boolean", "default": false },
        "overridden_by": { "type": ["string", "null"], "default": null },
        "reason": { "type": ["string", "null"], "default": null },
        "original_model": { "type": ["string", "null"], "default": null }
      }
    },
    "client_ip": {
      "type": ["string", "null"],
      "description": "Originating client IP address for audit trails"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

---

## 8. Contract F: `BenchmarkRecord`

**Sender:** Benchmark Engine  
**Receiver:** Benchmark Reports API (`POST /v1/benchmark/records`, Dashboard)  
**Purpose:** Evaluated record quantifying cost saved versus the "always use strongest model" baseline, with objective quality delta measurement.

### JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "BenchmarkRecord",
  "type": "object",
  "required": [
    "request_id",
    "task_category",
    "router_cost_usd",
    "baseline_cost_usd",
    "cost_savings_pct",
    "router_quality_score",
    "baseline_quality_score",
    "quality_delta"
  ],
  "properties": {
    "request_id": {
      "type": "string",
      "description": "Evaluated request identifier"
    },
    "task_category": {
      "type": "string",
      "description": "Classification category (e.g. coding, math, summarization, extraction, creative)"
    },
    "router_cost_usd": {
      "type": "number",
      "minimum": 0.0,
      "description": "Cost incurred using router selection"
    },
    "baseline_cost_usd": {
      "type": "number",
      "minimum": 0.0,
      "description": "Cost if the strongest frontier baseline model (e.g. gpt-4o) were used"
    },
    "cost_savings_pct": {
      "type": "number",
      "description": "Percentage savings: ((baseline_cost - router_cost) / baseline_cost) * 100"
    },
    "router_quality_score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Evaluated quality score of router's output"
    },
    "baseline_quality_score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Evaluated quality score of baseline model's output"
    },
    "quality_delta": {
      "type": "number",
      "description": "Difference in quality: (router_quality_score - baseline_quality_score)"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

### Example Payload
```json
{
  "request_id": "8f3b610c-99c2-466d-9bb3-772b7a421fa1",
  "task_category": "extraction",
  "router_cost_usd": 0.000000,
  "baseline_cost_usd": 0.003450,
  "cost_savings_pct": 100.0,
  "router_quality_score": 0.96,
  "baseline_quality_score": 0.98,
  "quality_delta": -0.02,
  "timestamp": "2026-09-18T05:30:15.000000Z"
}
```

---

## 9. Model Tier Pricing Matrix (Reference Baseline)

| Tier | Example Model | Provider | Input Cost ($ / 1M tokens) | Output Cost ($ / 1M tokens) | Target Latency (p50) |
|---|---|---|---|---|---|
| **Local** | `llama3.1:8b` | Ollama | $0.00 | $0.00 | ~150-300ms |
| **Cheap / Mid** | `gpt-4o-mini` | OpenAI | $0.15 | $0.60 | ~300-600ms |
| **Cheap / Mid** | `gemini-1.5-flash` | Google | $0.075 | $0.30 | ~250-500ms |
| **Premium (Baseline)** | `gpt-4o` | OpenAI | $2.50 | $10.00 | ~800-1500ms |
| **Premium (Baseline)** | `claude-3-5-sonnet` | Anthropic | $3.00 | $15.00 | ~900-1800ms |

---

## 10. Summary Matrix of Contracts and Workstream Owners

| Contract | Schema Name | Emitted By | Primary Consumers | Workstream Owner |
|---|---|---|---|---|
| **A** | `RoutingRequest` | Caller / Client | Router Core | Member A |
| **B** | `RoutingDecision` | Router Core | Model Gateway, Control Plane, Benchmark | Member A |
| **C** | `ModelCallResult` | Model Gateway | Router Core, Control Plane, Benchmark | Member B |
| **D** | `FinalResponse` | Router Core | Caller / Client | Member A |
| **E** | `DecisionLogEntry` | Control Plane / Middleware | Control Plane UI & Audit Store | Member C |
| **F** | `BenchmarkRecord` | Benchmark Engine | Benchmark Storage & Reports Dashboard | Member D |
