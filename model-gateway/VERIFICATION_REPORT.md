# Cost-LLM Verification Report: Member B (model-gateway)

**Target Repository:** `https://github.com/iamthekavin/Cost-LLM.git`  
**Target Branch:** `feature/model-gateway`  
**Evaluation Standard:** [`docs/INTERFACE_CONTRACT.md`](../docs/INTERFACE_CONTRACT.md) & [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)  
**Date of Verification:** 2026-09-18  
**Verifier:** Independent QA / Integration Verifier  

---

## Executive Summary Dashboard

| Check | Objective | Verdict | Summary Findings |
|---|---|:---:|---|
| **CHECK 1** | Stack comes up cleanly & genuine `/health` probe | **FAIL** *(Partial)* | Native Ollama & Gateway `/health` genuine probe **PASSED** (reflected offline/online state); Docker Desktop daemon was stopped on host preventing clean `docker-compose up`. `version: "3.8"` obsolete in compose file. |
| **CHECK 2** | Schema conformance for `ModelCallResult` across all tiers | **FAIL** *(Partial)* | Local tier passes 100% with live tokens from Ollama. Hosted tiers conform to schema but fail with HTTP 401 due to unmocked external URLs (`api.openai.com`) when API keys are absent. |
| **CHECK 3** | Shared pricing/model registry path and content | **FAIL** | Model list in code matches registry 100%, but registry is **duplicated** across `shared/models.yaml` and `model-gateway/pricing.yaml`, violating single-canonical-path rule. |
| **CHECK 4** | Fallback path under real failure | **PASS** | Primary model failure gracefully retries against `fallback_model` (`llama3.1:8b (fallback from ...)`), and non-fallback failure returns structured error without crashing. |
| **CHECK 5** | Concurrent batch calling, measured | **PASS** | Batch execution wall-clock time was **1506.62 ms** vs sequential sum of **3527.98 ms** (7.5% margin from slowest call of 1401.06 ms, well within the +20% threshold). |

---

## Detailed Check-by-Check Findings

### CHECK 1 — Stack Comes Up Cleanly

#### Objectives
1. Run `docker-compose up` from repo root.
2. Confirm Ollama container starts, the required local model is pulled/available, and the gateway service starts without errors.
3. Hit `GET /health` on the gateway: confirm healthy status genuinely reflects local model availability (kill Ollama, confirm unhealthy report).

#### Execution & Evidence
1. **`docker-compose up` Execution:**
   - **Command:** `docker compose up`
   - **Result:**
     ```
     level=warning msg="D:\Internal-hack\docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion"
     unable to get image 'internal-hack-router-core': error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/images/internal-hack-router-core/json": open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
     ```
   - **Diagnosis:** The Docker Desktop engine (`com.docker.service`) was stopped on the host and cannot be launched in a non-elevated user context. Additionally, `version: "3.8"` in `docker-compose.yml` produces deprecation warnings in Docker Compose v5.

2. **Native Daemon & Gateway Health Verification:**
   To test the gateway's logic against a live Ollama instance, Ollama was started natively at `http://127.0.0.1:11434` with model `llama3.1:8b`, and `model-gateway` was started on port 8002.
   - **Gateway Startup Command:**
     ```powershell
     $env:PYTHONPATH="model-gateway;."
     python -m uvicorn app.main:app --port 8002
     ```
   - **Startup Time:** 1.2 seconds.
   
3. **`/health` Response (Ollama Online):**
   - **HTTP Status:** `200 OK`
   - **Response Body:**
     ```json
     {
       "status": "ok",
       "service": "model-gateway",
       "version": "1.0.0",
       "ollama_reachable": true,
       "ollama_details": {
         "reachable": true,
         "status_code": 200,
         "models": [
           "llama3.1:8b",
           "llama3.2:3b"
         ],
         "has_target_model": true
       },
       "available_models": [
         "llama3.1:8b",
         "gpt-4o-mini",
         "claude-3-5-haiku",
         "gemini-1.5-flash",
         "gpt-4o",
         "claude-3-5-sonnet",
         "gemini-1.5-pro"
       ]
     }
     ```

4. **Killing Ollama & Verifying Health Probe:**
   - **Command Run:**
     ```powershell
     Get-Process -Name "*ollama*" | Stop-Process -Force
     ```
   - **`/health` Response (Ollama Killed):**
     - **HTTP Status:** `200 OK`
     - **Response Body:**
       ```json
       {
         "status": "degraded",
         "service": "model-gateway",
         "version": "1.0.0",
         "ollama_reachable": false,
         "ollama_details": {
           "reachable": false,
           "error": "ConnectTimeout"
         },
         "available_models": [
           "llama3.1:8b",
           "gpt-4o-mini",
           "claude-3-5-haiku",
           "gemini-1.5-flash",
           "gpt-4o",
           "claude-3-5-sonnet",
           "gemini-1.5-pro"
         ]
       }
       ```
   - **Verdict:** The `/health` endpoint **genuinely inspects the live connection** and correctly transitions from `status: "ok"` to `status: "degraded"`. However, because `docker-compose up` could not start the container stack on the system, Check 1 is graded **FAIL (Environment Blocked)**.

---

### CHECK 2 — Schema Conformance for `ModelCallResult` (All Three Tiers)

#### Contract Standard (`docs/INTERFACE_CONTRACT.md` § 5)
```json
{
  "required": ["subtask_id", "model_used", "tokens_in", "tokens_out", "latency_ms", "cost_usd", "raw_output"],
  "properties": {
    "subtask_id": { "type": "string" },
    "model_used": { "type": "string" },
    "tokens_in": { "type": "integer", "minimum": 0 },
    "tokens_out": { "type": "integer", "minimum": 0 },
    "latency_ms": { "type": "number", "minimum": 0.0 },
    "cost_usd": { "type": "number", "minimum": 0.0 },
    "raw_output": { "type": "string" },
    "error": { "type": ["string", "null"], "default": null }
  }
}
```

#### Tier 1: Local Tier (`llama3.1:8b`)
- **Request Sent:**
  ```json
  POST /call
  {
    "subtask_id": "test-local-01",
    "subtask_text": "Say hello in one sentence.",
    "chosen_model": "llama3.1:8b"
  }
  ```
- **Raw Response Received:**
  ```json
  {
    "subtask_id": "test-local-01",
    "model_used": "llama3.1:8b",
    "tokens_in": 31,
    "tokens_out": 3,
    "latency_ms": 8238.53,
    "cost_usd": 0.0,
    "raw_output": "Hello!",
    "error": null
  }
  ```
- **Field-by-Field Diff:**
  - `subtask_id`: `"test-local-01"` (string) — **PASS**
  - `model_used`: `"llama3.1:8b"` (string) — **PASS**
  - `tokens_in`: `31` (integer) — **PASS** (matches Ollama reported `prompt_eval_count`)
  - `tokens_out`: `3` (integer) — **PASS** (matches Ollama reported `eval_count`)
  - `latency_ms`: `8238.53` (float) — **PASS** (real measured wall-clock time)
  - `cost_usd`: `0.0` (float) — **PASS** (local model must be strictly $0.00)
  - `raw_output`: `"Hello!"` (string) — **PASS** (clean normalized text)
  - `error`: `null` (null) — **PASS** (null on success, not an empty string)
- **Hand-Calculated Cost:** `(31 * 0.0) + (3 * 0.0) = $0.000000` (Exact Match).
- **Tier 1 Verdict:** **PASS**

---

#### Tier 2: Cheap Hosted Tier (`gpt-4o-mini`)
- **Request Sent:**
  ```json
  POST /call
  {
    "subtask_id": "test-cheap-01",
    "subtask_text": "Say hello in one sentence.",
    "chosen_model": "gpt-4o-mini"
  }
  ```
- **Raw Response Received:**
  ```json
  {
    "subtask_id": "test-cheap-01",
    "model_used": "gpt-4o-mini",
    "tokens_in": 6,
    "tokens_out": 0,
    "latency_ms": 681.79,
    "cost_usd": 0.0,
    "raw_output": "",
    "error": "OpenAI HTTP 401: {\n    \"error\": {\n        \"message\": \"Incorrect API key provided: mock-key. You can find your API key at https://platform.openai.com/account/api-keys.\",\n        \"type\": \"invalid_request_error\",\n        \"param\": null,\n        \"code\": \"invalid_api_key\"\n    }\n}\n"
  }
  ```
- **Field-by-Field Diff:**
  - Schema keys & types match `ModelCallResult`.
  - `tokens_in`: `6` (estimated fallback heuristic `len(text) // 4` because provider call failed with HTTP 401).
  - `tokens_out`: `0` (provider failed to complete).
  - `cost_usd`: `0.0`.
  - `error`: String containing provider 401 payload.
- **Hand-Calculated Cost for Successful Call (from Unit Test Suite):**
  - Prompt tokens: `50`, Output tokens: `20`
  - Input price: $0.15 / 1M tokens -> `(50 / 1_000_000) * 0.15 = $0.0000075`
  - Output price: $0.60 / 1M tokens -> `(20 / 1_000_000) * 0.60 = $0.0000120`
  - Expected Cost: `$0.0000195` -> rounded to 6 decimals: **`$0.000020`**
  - Gateway output in `test_cheap_hosted_openai_success`: **`$0.000020`** (Exact Match).
- **Tier 2 Verdict:** **FAIL (External API Dependency)**: `cheap_hosted.py` directly issues an outbound network request to `https://api.openai.com` with `'mock-key'` when no environment variable is present, rather than supporting a local mock mode or configurable base URL (`OPENAI_BASE_URL`).

---

#### Tier 3: Premium Hosted Tier (`gpt-4o`)
- **Request Sent:**
  ```json
  POST /call
  {
    "subtask_id": "test-prem-01",
    "subtask_text": "Say hello in one sentence.",
    "chosen_model": "gpt-4o"
  }
  ```
- **Raw Response Received:**
  ```json
  {
    "subtask_id": "test-prem-01",
    "model_used": "gpt-4o",
    "tokens_in": 6,
    "tokens_out": 0,
    "latency_ms": 935.28,
    "cost_usd": 0.0,
    "raw_output": "",
    "error": "OpenAI HTTP 401: {\n    \"error\": {\n        \"message\": \"Incorrect API key provided: mock-key. You can find your API key at https://platform.openai.com/account/api-keys.\",\n        \"type\": \"invalid_request_error\",\n        \"param\": null,\n        \"code\": \"invalid_api_key\"\n    }\n}\n"
  }
  ```
- **Hand-Calculated Cost for Successful Baseline Call (from Unit Test Suite):**
  - Prompt tokens: `500`, Output tokens: `200`
  - Input price: $2.50 / 1M tokens -> `(500 / 1_000_000) * 2.50 = $0.001250`
  - Output price: $10.00 / 1M tokens -> `(200 / 1_000_000) * 10.00 = $0.002000`
  - Expected Baseline Cost: **`$0.003250`**
  - Gateway output in `test_premium_hosted_baseline_success`: **`$0.003250`** (Exact Match).
- **Tier 3 Verdict:** **FAIL (External API Dependency)**: Same issue as Tier 2.

---

### CHECK 3 — Shared Pricing/Model Registry Path & Content

#### Objectives
1. Confirm `pricing.yaml` / `models.yaml` exists at a single canonical path and is NOT duplicated or diverged.
2. Confirm every model in code exists in the registry with tier, pricing, and context window.
3. Confirm path is documented in `model-gateway/README.md`.

#### Audit Findings
- **File Paths Found:**
  - `shared/models.yaml` (84 lines)
  - `model-gateway/pricing.yaml` (40 lines)
- **Duplication & Divergence Issue:**
  `shared/models.yaml` contains full model metadata (`context_window`, `default_timeout_s`, `aliases`), while `model-gateway/pricing.yaml` contains only a partial subset. Having two files creates synchronization risk.
- **Code Reference Cross-Check:**
  The 3 provider adapters reference the following models:
  - `llama3.1:8b` -> present in `shared/models.yaml` (`context_window: 131072`, `cost: $0/$0`)
  - `gpt-4o-mini` -> present in `shared/models.yaml` (`context_window: 128000`, `cost: $0.15/$0.60`)
  - `claude-3-5-haiku` -> present in `shared/models.yaml` (`context_window: 200000`, `cost: $0.80/$4.00`)
  - `gemini-1.5-flash` -> present in `shared/models.yaml` (`context_window: 1048576`, `cost: $0.075/$0.30`)
  - `gpt-4o` -> present in `shared/models.yaml` (`context_window: 128000`, `cost: $2.50/$10.00`)
  - `claude-3-5-sonnet` -> present in `shared/models.yaml` (`context_window: 200000`, `cost: $3.00/$15.00`)
  - `gemini-1.5-pro` -> present in `shared/models.yaml` (`context_window: 2097152`, `cost: $1.25/$5.00`)
  - **Models referenced in code but missing in registry:** **NONE (0 missing)**.
- **Canonical Content of `shared/models.yaml`:**
  ```yaml
  version: "1.0.0"
  updated_at: "2026-09-18"

  models:
    llama3.1:8b:
      tier: "local"
      provider: "ollama"
      context_window: 131072
      cost_per_1m_in: 0.000000
      cost_per_1m_out: 0.000000
      default_timeout_s: 60.0
      aliases: ["llama3.1", "llama-3.1-8b", "llama3"]
    gpt-4o-mini:
      tier: "cheap"
      provider: "openai"
      context_window: 128000
      cost_per_1m_in: 0.150000
      cost_per_1m_out: 0.600000
      default_timeout_s: 30.0
    claude-3-5-haiku:
      tier: "cheap"
      provider: "anthropic"
      context_window: 200000
      cost_per_1m_in: 0.800000
      cost_per_1m_out: 4.000000
      default_timeout_s: 30.0
    gemini-1.5-flash:
      tier: "cheap"
      provider: "google"
      context_window: 1048576
      cost_per_1m_in: 0.075000
      cost_per_1m_out: 0.300000
      default_timeout_s: 30.0
    gpt-4o:
      tier: "premium"
      provider: "openai"
      context_window: 128000
      cost_per_1m_in: 2.500000
      cost_per_1m_out: 10.000000
      default_timeout_s: 45.0
    claude-3-5-sonnet:
      tier: "premium"
      provider: "anthropic"
      context_window: 200000
      cost_per_1m_in: 3.000000
      cost_per_1m_out: 15.000000
      default_timeout_s: 45.0
    gemini-1.5-pro:
      tier: "premium"
      provider: "google"
      context_window: 2097152
      cost_per_1m_in: 1.250000
      cost_per_1m_out: 5.000000
      default_timeout_s: 45.0
  ```
- **Verdict:** **FAIL**: The file `model-gateway/pricing.yaml` is redundant and should be replaced by a single canonical file at `shared/models.yaml`.

---

### CHECK 4 — Fallback Path Under Real Failure

#### Scenario 4A: Primary Failure with Valid Fallback
- **Failure Injected:** Injected non-existent model name `chosen_model: "non-existent-model-xyz"` with `fallback_model: "llama3.1:8b"`.
- **Request Body:**
  ```json
  POST /call
  {
    "subtask_id": "test-fallback-01",
    "subtask_text": "Say fallback test in one word.",
    "chosen_model": "non-existent-model-xyz",
    "fallback_model": "llama3.1:8b"
  }
  ```
- **Response Received:**
  ```json
  {
    "subtask_id": "test-fallback-01",
    "model_used": "llama3.1:8b (fallback from non-existent-model-xyz)",
    "tokens_in": 32,
    "tokens_out": 3,
    "latency_ms": 5138.81,
    "cost_usd": 0.0,
    "raw_output": "Regression.",
    "error": null
  }
  ```
- **Analysis:**
  - `model_used` explicitly records the fallback path: `"llama3.1:8b (fallback from non-existent-model-xyz)"`.
  - Service recovered successfully, returned `error: null` and valid output.

#### Scenario 4B: Primary Failure with No Fallback
- **Failure Injected:** `chosen_model: "non-existent-model-xyz"`, `fallback_model: null`.
- **Request Body:**
  ```json
  POST /call
  {
    "subtask_id": "test-nofallback-02",
    "subtask_text": "Say fail in one word.",
    "chosen_model": "non-existent-model-xyz",
    "fallback_model": null
  }
  ```
- **Response Received:**
  ```json
  {
    "subtask_id": "test-nofallback-02",
    "model_used": "non-existent-model-xyz",
    "tokens_in": 5,
    "tokens_out": 0,
    "latency_ms": 1227.02,
    "cost_usd": 0.0,
    "raw_output": "",
    "error": "OpenAI HTTP 401: {\n    \"error\": {\n        \"message\": \"Incorrect API key provided: mock-key...\"\n    }\n}\n"
  }
  ```
- **Analysis:** Clean `ModelCallResult` returned with error diagnostics; server did not crash or drop the connection.
- **Verdict:** **PASS**

---

### CHECK 5 — Concurrent Batch Calling (Measured)

#### Methodology
A batch of 3 subtasks was dispatched simultaneously to `POST /call/batch` against local `llama3.1:8b`:
```json
POST /call/batch
{
  "items": [
    { "subtask_id": "batch-sub-1", "subtask_text": "Say 1.", "chosen_model": "llama3.1:8b" },
    { "subtask_id": "batch-sub-2", "subtask_text": "Say 2.", "chosen_model": "llama3.1:8b" },
    { "subtask_id": "batch-sub-3", "subtask_text": "Say 3.", "chosen_model": "llama3.1:8b" }
  ]
}
```

#### Measured Results
- **Subtask 1 Latency:** `1401.06 ms`
- **Subtask 2 Latency:** `1178.12 ms`
- **Subtask 3 Latency:** `948.80 ms`
- **Sequential Sum (T_seq):** `1401.06 + 1178.12 + 948.80 = 3527.98 ms`
- **Slowest Individual Call (T_max):** `1401.06 ms`
- **Actual Measured Batch Latency (T_batch):** **`1506.62 ms`** (Client wall-clock: `1544 ms`)

#### Concurrency Evaluation
- **Batch vs Slowest Call Margin:**
  $$\text{Margin} = \frac{T_{\text{batch}} - T_{\text{max}}}{T_{\text{max}}} = \frac{1506.62 - 1401.06}{1401.06} = +7.53\%$$
- **Threshold:** Margin $\le +20.0\%$.
- **Result:** $+7.53\% \le +20.0\%$ (**PASS**).
- **Latency Savings vs Sequential:**
  $$\frac{3527.98 - 1506.62}{3527.98} = 57.3\% \text{ reduction in latency}$$
- **Verdict:** **PASS**

---

## Action Items Flagged for Member B

Before Member A (Router Core) and Member D (Benchmark) integrate against `feature/model-gateway`, Member B must resolve the following:

1. **Configurable Base URLs for Hosted Providers (Fix for Check 2):**
   - **File:** `model-gateway/providers/cheap_hosted.py` (Line 54) & `model-gateway/providers/premium_hosted.py`
   - **Issue:** Hardcoded `https://api.openai.com/v1/chat/completions` prevents testing hosted adapters locally with mock endpoints or Ollama's OpenAI compatibility layer.
   - **Fix:** Allow `OPENAI_BASE_URL` (defaulting to `https://api.openai.com/v1` or an emulator like `http://localhost:11434/v1`).

2. **Consolidate Pricing Registry to Single Canonical Path (Fix for Check 3):**
   - **Files:** Remove `model-gateway/pricing.yaml` and point `model-gateway/config.py` exclusively at `shared/models.yaml`.
   - **Issue:** Duplication between `shared/models.yaml` and `model-gateway/pricing.yaml` violates the single-source-of-truth contract.

3. **Clean Up `docker-compose.yml` (Fix for Check 1):**
   - Remove obsolete `version: "3.8"` line from `docker-compose.yml` to prevent Docker Compose v5 warnings.
