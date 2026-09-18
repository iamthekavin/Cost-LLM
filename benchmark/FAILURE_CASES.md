# Cost-LLM Benchmark: Failure Cases & Misrouting Analysis

**Owner:** Member D (Benchmarking & Cost-Quality Evaluation)  
**Last Updated:** 2026-09-18 10:02:21Z  
**Regression Threshold:** `quality_delta < -0.05`  
**Total Regressions Flagged:** 0

---

## Executive Overview

In an intelligent routing system, quality regressions occur when a prompt requiring higher cognitive capability
is dispatched to a lower tier (e.g. `deep` prompt misclassified as `moderate` or `trivial`).
Below is an auditable register of each detected regression, comparing the router's execution against the
always-strongest baseline, complete with root-cause hypotheses and architectural mitigations.

## Summary of Detected Regressions

| Task ID | Category | Expected Tier | Router Model | Baseline Model | Router Q | Baseline Q | Quality Delta |
|---|---|---|---|---|---|---|---|

---

## Detailed Case Studies & Root-Cause Hypotheses

*No significant quality regressions detected in this evaluation run.*