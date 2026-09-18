"""
Quality Scoring Engine for Cost-LLM Benchmark (Member D).

Implements:
1. Objective scoring for closed-answer tasks (exact-match, regex, math/GSM8K, JSON rule-based, code execution).
2. Blinded LLM-as-a-judge scoring for open-ended tasks (summarization, rewriting, analysis)
   using a standardized rubric (correctness, completeness, coherence, instruction-following; 1-5 each)
   with presentation order randomization and provider artifact stripping.
"""

import json
import math
import random
import re
from typing import Any, Dict, Optional, Tuple


def normalize_text(text: str) -> str:
    """Normalize text for consistent comparison (strip whitespace and common wrappers)."""
    if not text:
        return ""
    cleaned = text.strip()
    # Remove enclosing quotes if entire string is quoted
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        cleaned = cleaned[1:-1].strip()
    return cleaned


def strip_identifying_artifacts(text: str) -> str:
    """
    Strip identifying prefixes, model declarations, or test scaffold phrases
    to ensure unbiased blind evaluation by LLM-as-judge.
    """
    if not text:
        return ""
    cleaned = text.strip()

    patterns = [
        r"^Model Gateway scaffolding response for.*?\.\s*",
        r"^Router Core scaffolding response placeholder\.\s*",
        r"^As an AI language model,?\s*",
        r"^As a large language model trained by \w+,?\s*",
        r"^Here is the requested (response|answer|output):?\s*",
        r"^Here is the (summary|translation|rewrite):?\s*",
        r"^Sure, here is.*?:?\s*",
        r"^Certainly!?\s*",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    return cleaned


def score_exact_match(predicted: str, ground_truth: str) -> float:
    """Score exact match after normalization (case-insensitive and whitespace-stripped)."""
    norm_pred = normalize_text(predicted).lower()
    norm_gt = normalize_text(ground_truth).lower()
    return 1.0 if norm_pred == norm_gt else 0.0


def score_regex(predicted: str, pattern: str) -> float:
    """Score regex pattern match."""
    if not predicted or not pattern:
        return 0.0
    match = re.search(pattern, predicted, flags=re.IGNORECASE | re.MULTILINE)
    return 1.0 if match else 0.0


def extract_last_number(text: str) -> Optional[float]:
    """Extract the last integer or float from a string, supporting GSM8K '#### <number>' format."""
    if not text:
        return None

    # Check for GSM8K delimiter first
    gsm_match = re.search(r"####\s*([+-]?\d+(?:\.\d+)?)", text)
    if gsm_match:
        try:
            return float(gsm_match.group(1))
        except ValueError:
            pass

    # Extract all numbers and take the last one
    numbers = re.findall(r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", text)
    if numbers:
        last_num = numbers[-1].replace(",", "")
        try:
            return float(last_num)
        except ValueError:
            return None
    return None


def score_math(predicted: str, ground_truth: str) -> float:
    """Score math answers by extracting and comparing numerical values."""
    pred_num = extract_last_number(predicted)
    gt_num = extract_last_number(ground_truth)

    if pred_num is None or gt_num is None:
        return 0.0

    return 1.0 if math.isclose(pred_num, gt_num, rel_tol=1e-3, abs_tol=1e-3) else 0.0


def score_rule_based(predicted: str, ground_truth: str, rubric: str = "") -> float:
    """
    Score structured outputs (e.g. JSON dictionaries).
    Checks validity of JSON and field-level matching against ground truth.
    """
    if not predicted:
        return 0.0

    # Extract JSON substring if embedded in markdown blocks
    json_candidate = predicted.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", json_candidate, flags=re.DOTALL)
    if match:
        json_candidate = match.group(1)
    elif "{" in json_candidate and "}" in json_candidate:
        start = json_candidate.find("{")
        end = json_candidate.rfind("}") + 1
        json_candidate = json_candidate[start:end]

    try:
        pred_dict = json.loads(json_candidate)
    except Exception:
        # If ground_truth contains comma-separated keywords, check set presence
        if "," in ground_truth:
            expected_tokens = [t.strip().lower() for t in ground_truth.split(",") if t.strip()]
            found = sum(1 for t in expected_tokens if t in predicted.lower())
            return found / max(1, len(expected_tokens))
        return 0.0

    try:
        gt_dict = json.loads(ground_truth)
    except Exception:
        # Ground truth might be plain text or partial
        return 0.5 if pred_dict else 0.0

    if not isinstance(gt_dict, dict) or not isinstance(pred_dict, dict):
        return 1.0 if pred_dict == gt_dict else 0.0

    # Compare key matches
    total_keys = len(gt_dict)
    if total_keys == 0:
        return 1.0 if len(pred_dict) == 0 else 0.5

    matched_keys = 0
    for k, v in gt_dict.items():
        if k in pred_dict:
            pred_val = pred_dict[k]
            # Normalization for string comparisons
            if isinstance(v, str) and isinstance(pred_val, str):
                if v.strip().lower() == pred_val.strip().lower():
                    matched_keys += 1
            elif isinstance(v, (int, float)) and isinstance(pred_val, (int, float)):
                if math.isclose(float(v), float(pred_val), rel_tol=1e-2):
                    matched_keys += 1
            elif pred_val == v:
                matched_keys += 1

    return matched_keys / total_keys


def score_code(predicted: str, ground_truth: str) -> float:
    """
    Score Python code generation by extracting code blocks, compiling syntax,
    and executing unit test assertions embedded in the ground truth.
    """
    if not predicted:
        return 0.0

    # Extract code from ```python ... ``` block if present
    code_body = predicted
    match = re.search(r"```(?:python)?\s*(.*?)\s*```", predicted, flags=re.DOTALL)
    if match:
        code_body = match.group(1)

    # Extract assertions from ground_truth
    assertion_lines = [
        line for line in ground_truth.splitlines() if line.strip().startswith("assert ")
    ]

    exec_code = code_body + "\n" + "\n".join(assertion_lines)

    # Syntax check first
    try:
        compile(code_body, "<candidate>", "exec")
    except SyntaxError:
        return 0.0

    # Execute inside isolated dictionary
    restricted_globals: Dict[str, Any] = {"__builtins__": __builtins__}
    try:
        exec(exec_code, restricted_globals)  # noqa: S102
        return 1.0
    except AssertionError:
        return 0.3  # Compiled and ran, but failed assertion
    except Exception:
        return 0.1  # Runtime exception during execution


# =========================================================================
# Blinded LLM-as-a-Judge Implementation
# =========================================================================

JUDGE_PROMPT_TEMPLATE = """You are an expert, impartial evaluator assessing two candidate AI responses for a task.

[TASK PROMPT]
{prompt}

[GROUND TRUTH / REFERENCE CRITERIA]
{ground_truth}

[SPECIFIC EVALUATION RUBRIC]
{rubric}

[CANDIDATE 1]
{candidate_1}

[CANDIDATE 2]
{candidate_2}

Score both candidates on a 1 to 5 integer scale for each of the following 4 criteria:
1. Correctness (1-5): Factual accuracy and absence of hallucinations or errors.
2. Completeness (1-5): Addresses all required instructions, constraints, and sub-questions.
3. Coherence (1-5): Clarity, organization, fluent tone, and readable structure.
4. Instruction-Following (1-5): Strictly abides by all formatting, length, and style constraints.

Return ONLY a valid JSON object matching this schema:
{{
  "candidate_1": {{
    "correctness": 1,
    "completeness": 1,
    "coherence": 1,
    "instruction_following": 1,
    "reasoning": "Brief rationale"
  }},
  "candidate_2": {{
    "correctness": 1,
    "completeness": 1,
    "coherence": 1,
    "instruction_following": 1,
    "reasoning": "Brief rationale"
  }}
}}
"""


def _heuristic_judge_fallback(
    prompt: str,
    candidate_text: str,
    ground_truth: str = "",
    rubric: str = "",
) -> Tuple[float, Dict[str, Any]]:
    """
    Deterministic fallback judge for environments without an active external LLM key.
    Calculates 1-5 scores across the 4 criteria based on semantic overlap, length appropriateness,
    formatting conformance, and lack of error signatures.
    """
    text = strip_identifying_artifacts(candidate_text)
    if not text:
        return 0.2, {
            "correctness": 1,
            "completeness": 1,
            "coherence": 1,
            "instruction_following": 1,
            "reasoning": "Empty output.",
        }

    # 1. Correctness (1-5)
    correctness = 4
    if ground_truth:
        gt_words = set(re.findall(r"\w+", ground_truth.lower()))
        cand_words = set(re.findall(r"\w+", text.lower()))
        overlap = len(gt_words & cand_words) / max(1, len(gt_words))
        if overlap > 0.6:
            correctness = 5
        elif overlap < 0.2:
            correctness = 2
    if "error" in text.lower() or "exception" in text.lower():
        correctness = max(1, correctness - 2)

    # 2. Completeness (1-5)
    word_count = len(text.split())
    if word_count < 5:
        completeness = 2
    elif word_count < 15:
        completeness = 3
    elif word_count <= 250:
        completeness = 5
    else:
        completeness = 4

    # 3. Coherence (1-5)
    coherence = 5
    if text.count("\n\n") > 1 or "." in text:
        coherence = 5
    else:
        coherence = 4

    # 4. Instruction Following (1-5)
    instruction_following = 4
    if "bullet" in prompt.lower() and ("-" in text or "*" in text or "•" in text):
        instruction_following = 5
    if "json" in prompt.lower():
        try:
            json.loads(text)
            instruction_following = 5
        except Exception:
            instruction_following = max(1, instruction_following - 1)
    if "sentence" in prompt.lower() and text.count(".") >= 1:
        instruction_following = 5

    total_pts = correctness + completeness + coherence + instruction_following
    normalized_score = round(total_pts / 20.0, 4)

    return normalized_score, {
        "correctness": correctness,
        "completeness": completeness,
        "coherence": coherence,
        "instruction_following": instruction_following,
        "reasoning": "Evaluated via deterministic criteria rubric.",
    }


def score_llm_judge(
    prompt: str,
    router_output: str,
    baseline_output: str,
    ground_truth: str = "",
    rubric: str = "",
    judge_client: Optional[Any] = None,
    seed: Optional[int] = None,
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Executes a blind LLM-as-a-judge comparison between router and baseline outputs.
    - Randomly flips order of candidate 1 and candidate 2.
    - Strips identifying artifacts.
    - Uses live judge_client if provided, or falls back to deterministic heuristic judge.
    - Normalizes scores to 0.0 - 1.0 range.
    """
    clean_router = strip_identifying_artifacts(router_output)
    clean_baseline = strip_identifying_artifacts(baseline_output)

    # Randomize candidate presentation order to eliminate position bias
    rng = random.Random(seed)
    order_flip = rng.choice([True, False])

    if order_flip:
        cand_1_text, cand_2_text = clean_baseline, clean_router
        c1_source, c2_source = "baseline", "router"
    else:
        cand_1_text, cand_2_text = clean_router, clean_baseline
        c1_source, c2_source = "router", "baseline"

    # If live judge client is provided
    if judge_client and hasattr(judge_client, "evaluate"):
        try:
            judge_response = judge_client.evaluate(
                prompt=prompt,
                candidate_1=cand_1_text,
                candidate_2=cand_2_text,
                ground_truth=ground_truth,
                rubric=rubric,
            )
            c1_scores = judge_response.get("candidate_1", {})
            c2_scores = judge_response.get("candidate_2", {})
            c1_norm = sum(
                c1_scores.get(k, 3)
                for k in ["correctness", "completeness", "coherence", "instruction_following"]
            ) / 20.0
            c2_norm = sum(
                c2_scores.get(k, 3)
                for k in ["correctness", "completeness", "coherence", "instruction_following"]
            ) / 20.0
        except Exception:
            c1_norm, c1_scores = _heuristic_judge_fallback(prompt, cand_1_text, ground_truth, rubric)
            c2_norm, c2_scores = _heuristic_judge_fallback(prompt, cand_2_text, ground_truth, rubric)
    else:
        # Deterministic fallback judge
        c1_norm, c1_scores = _heuristic_judge_fallback(prompt, cand_1_text, ground_truth, rubric)
        c2_norm, c2_scores = _heuristic_judge_fallback(prompt, cand_2_text, ground_truth, rubric)

    # Map back unblinded scores
    if c1_source == "router":
        router_score = c1_norm
        baseline_score = c2_norm
        router_details = c1_scores
        baseline_details = c2_scores
    else:
        router_score = c2_norm
        baseline_score = c1_norm
        router_details = c2_scores
        baseline_details = c1_scores

    details = {
        "order_flipped": order_flip,
        "candidate_1_source": c1_source,
        "candidate_2_source": c2_source,
        "router_details": router_details,
        "baseline_details": baseline_details,
    }

    return round(router_score, 4), round(baseline_score, 4), details


def evaluate_task(
    task: Dict[str, Any],
    router_output: str,
    baseline_output: str,
    judge_client: Optional[Any] = None,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Main dispatch function to evaluate a task output pair.
    Selects between exact_match, regex, math, rule_based, code, and llm_judge.
    Produces comparable quality_score (0-1) for both router and baseline pipelines.
    """
    method = task.get("scoring_method", "llm_judge")
    ground_truth = task.get("ground_truth", "")
    rubric = task.get("rubric", "")
    prompt = task.get("prompt", "")

    details: Dict[str, Any] = {"method": method}

    if method == "exact_match":
        router_q = score_exact_match(router_output, ground_truth)
        baseline_q = score_exact_match(baseline_output, ground_truth)
    elif method == "regex":
        router_q = score_regex(router_output, ground_truth)
        baseline_q = score_regex(baseline_output, ground_truth)
    elif method == "math":
        router_q = score_math(router_output, ground_truth)
        baseline_q = score_math(baseline_output, ground_truth)
    elif method == "rule_based":
        router_q = score_rule_based(router_output, ground_truth, rubric)
        baseline_q = score_rule_based(baseline_output, ground_truth, rubric)
    elif method == "code":
        router_q = score_code(router_output, ground_truth)
        baseline_q = score_code(baseline_output, ground_truth)
    elif method == "llm_judge":
        router_q, baseline_q, judge_info = score_llm_judge(
            prompt=prompt,
            router_output=router_output,
            baseline_output=baseline_output,
            ground_truth=ground_truth,
            rubric=rubric,
            judge_client=judge_client,
            seed=seed,
        )
        details.update(judge_info)
    else:
        # Default fallback
        router_q = 1.0 if router_output else 0.0
        baseline_q = 1.0 if baseline_output else 0.0

    quality_delta = round(router_q - baseline_q, 4)

    return {
        "task_id": task.get("task_id"),
        "scoring_method": method,
        "router_quality_score": round(router_q, 4),
        "baseline_quality_score": round(baseline_q, 4),
        "quality_delta": quality_delta,
        "evaluation_details": details,
    }
