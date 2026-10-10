"""
Benchmark Dataset: Comprehensive suite of real-world enterprise LLM requests
spanning varying complexity tiers, multi-part requests, and reasoning depths.
"""

from typing import List, Dict, Any
from pydantic import BaseModel
from cost_router.config import ModelTier


class BenchmarkItem(BaseModel):
    id: str
    category: str
    prompt: str
    expected_tier: ModelTier
    expected_intent: str
    rubric_keywords: List[str]
    description: str


BENCHMARK_SUITE: List[BenchmarkItem] = [
    # Category 1: Simple Extraction & Formatting (Tier 1: Local / Free)
    BenchmarkItem(
        id="bm-ext-01",
        category="Extraction & Formatting",
        prompt="Extract all transaction amounts and dates from this invoice snippet:\nInvoice #9401, dated 2026-03-15. Amount: $4,520.50. Paid via ACH on 2026-03-18 with fee $12.00.",
        expected_tier=ModelTier.LOCAL,
        expected_intent="DATA_EXTRACTION",
        rubric_keywords=["4,520.50", "2026-03-15", "12.00", "2026-03-18"],
        description="Extract monetary amounts and dates from raw invoice text."
    ),
    BenchmarkItem(
        id="bm-fmt-02",
        category="Extraction & Formatting",
        prompt="Convert the following employee list into clean JSON format with keys 'name', 'role', and 'department':\n1. Alice Chen (Senior Engineer, Infrastructure)\n2. Marcus Vance (Designer, UX)",
        expected_tier=ModelTier.LOCAL,
        expected_intent="FORMATTING",
        rubric_keywords=["Alice Chen", "Senior Engineer", "Marcus Vance", "name", "role"],
        description="Transform unstructured personnel list into standardized JSON."
    ),

    # Category 2: Classification & Triage (Tier 1 / Tier 2: Cheap)
    BenchmarkItem(
        id="bm-cls-03",
        category="Classification & Triage",
        prompt="Classify the sentiment and urgency level of this customer ticket:\n'URGENT: Our production database connection pool has been exhausted for the last 20 minutes! Users cannot log in.'",
        expected_tier=ModelTier.CHEAP,
        expected_intent="CLASSIFICATION",
        rubric_keywords=["urgent", "critical", "negative", "high", "severity"],
        description="Categorize production outage support ticket by sentiment and urgency."
    ),
    BenchmarkItem(
        id="bm-cls-04",
        category="Classification & Triage",
        prompt="Categorize this incoming email into one of [Sales, Billing, Technical Support, Spam]:\n'Hello, I noticed unauthorized recurring charges of $49 on my Visa statement from last month. Please refund immediately.'",
        expected_tier=ModelTier.CHEAP,
        expected_intent="CLASSIFICATION",
        rubric_keywords=["Billing", "refund", "charges"],
        description="Route customer dispute email to appropriate billing department."
    ),

    # Category 3: Summarization & Transformation (Tier 2: Cheap)
    BenchmarkItem(
        id="bm-sum-05",
        category="Summarization",
        prompt="Summarize the key architectural trade-offs of microservices vs monoliths in exactly three bullet points for an executive briefing.",
        expected_tier=ModelTier.CHEAP,
        expected_intent="SUMMARIZATION",
        rubric_keywords=["microservices", "monolith", "complexity", "deployment", "scalability"],
        description="Generate 3-bullet executive summary on architectural trade-offs."
    ),

    # Category 4: Code & Algorithmic Design (Tier 3: Balanced)
    BenchmarkItem(
        id="bm-code-06",
        category="Coding & Architecture",
        prompt="Write a Python class implementing a thread-safe sliding window rate limiter with configurable capacity and time window, including type annotations and error handling.",
        expected_tier=ModelTier.BALANCED,
        expected_intent="CODE_GENERATION",
        rubric_keywords=["class", "def", "threading", "lock", "window", "time", "rate"],
        description="Implement thread-safe concurrency rate limiter in Python."
    ),
    BenchmarkItem(
        id="bm-code-07",
        category="Coding & Architecture",
        prompt="Provide a FastAPI route handler that accepts a file upload, checks that the MIME type is 'application/pdf', verifies size does not exceed 10MB, and saves it asynchronously to disk.",
        expected_tier=ModelTier.BALANCED,
        expected_intent="CODE_GENERATION",
        rubric_keywords=["FastAPI", "UploadFile", "pdf", "10", "async", "await"],
        description="Build secure asynchronous file upload endpoint in FastAPI."
    ),

    # Category 5: Deep Logic, Math & Multi-Step Reasoning (Tier 4: Frontier)
    BenchmarkItem(
        id="bm-rsn-08",
        category="Deep Reasoning & Math",
        prompt="Analyze the following economic scenario: A monopolist faces inverse demand P = 120 - 2Q and marginal cost MC = 20. If a tax of $10 per unit is imposed on the monopolist, calculate the exact change in consumer surplus, deadweight loss, and explain why the price increases by less than the full tax.",
        expected_tier=ModelTier.FRONTIER,
        expected_intent="MULTI_STEP_REASONING",
        rubric_keywords=["surplus", "deadweight", "tax", "monopoly", "demand", "price", "elasticity"],
        description="Multi-step microeconomic monopoly tax incidence and deadweight loss proof."
    ),
    BenchmarkItem(
        id="bm-rsn-09",
        category="Deep Reasoning & Math",
        prompt="Evaluate the formal security implications of a distributed Byzantine Fault Tolerance consensus algorithm when f < n/3 nodes are adversarial, and prove whether liveness is preserved during asymmetric network partitions.",
        expected_tier=ModelTier.FRONTIER,
        expected_intent="MULTI_STEP_REASONING",
        rubric_keywords=["byzantine", "consensus", "liveness", "partition", "adversarial", "proof"],
        description="Formal distributed systems proof of Byzantine liveness under partition."
    ),

    # Category 6: Multi-Part Composite Workflows (Router Splits & Combines)
    BenchmarkItem(
        id="bm-cmp-10",
        category="Multi-Part Composite",
        prompt="1. Extract the invoice total and vendor name from: 'Vendor: Acronis Cloud Solutions, Total: $14,250.00, Terms: Net 30'. 2. Classify whether this requires secondary VP sign-off given a $10,000 corporate threshold. 3. Finally, conduct a detailed fiscal compliance audit risk analysis on potential liability if paid after Net 30 days.",
        expected_tier=ModelTier.FRONTIER, # The composite query encompasses low and high tiers
        expected_intent="MULTI_STEP_REASONING",
        rubric_keywords=["Acronis", "14,250", "sign-off", "VP", "audit", "compliance", "liability"],
        description="Multi-part workflow: Extraction (Local) + Classification (Cheap) + Audit Risk Analysis (Frontier)."
    ),
]
