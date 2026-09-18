"""Tests for Quality Scoring Engine (Member D)."""

from benchmark.quality import (
    evaluate_task,
    score_code,
    score_exact_match,
    score_llm_judge,
    score_math,
    score_regex,
    score_rule_based,
    strip_identifying_artifacts,
)


def test_score_exact_match():
    """Verify exact match scoring with normalization."""
    assert score_exact_match("Paris", "Paris") == 1.0
    assert score_exact_match("  paris  ", "Paris") == 1.0
    assert score_exact_match('"Paris"', "Paris") == 1.0
    assert score_exact_match("London", "Paris") == 0.0
    assert score_exact_match("", "Paris") == 0.0


def test_score_regex():
    """Verify regex scoring."""
    assert score_regex("Order ID: ORD-12345 confirmed", r"ORD-\d+") == 1.0
    assert score_regex("No order number here", r"ORD-\d+") == 0.0


def test_score_math():
    """Verify GSM8K numerical scoring."""
    assert score_math("The final amount is #### 126", "#### 126") == 1.0
    assert score_math("Calculated 126.000 dollars", "#### 126") == 1.0
    assert score_math("Result is 42", "#### 126") == 0.0
    assert score_math("The answer is $4,250.00", "$4,250.00") == 1.0


def test_score_rule_based_json():
    """Verify structured JSON scoring."""
    gt = '{"order_id": "ORD-98214", "tracking_number": "794928104821"}'
    valid_pred = '```json\n{"order_id": "ORD-98214", "tracking_number": "794928104821"}\n```'
    partial_pred = '{"order_id": "ORD-98214", "tracking_number": "WRONG"}'
    invalid_pred = "Not a json"

    assert score_rule_based(valid_pred, gt) == 1.0
    assert score_rule_based(partial_pred, gt) == 0.5
    assert score_rule_based(invalid_pred, gt) == 0.0


def test_score_code_execution():
    """Verify Python code execution and assertion validation."""
    code = """def add(a: int, b: int) -> int:
    return a + b
"""
    gt = """assert add(1, 2) == 3
assert add(0, 0) == 0
"""
    assert score_code(code, gt) == 1.0

    bad_code = """def add(a: int, b: int) -> int:
    return a - b
"""
    assert score_code(bad_code, gt) < 1.0

    syntax_err = "def add(a, b) return a + b"
    assert score_code(syntax_err, gt) == 0.0


def test_strip_identifying_artifacts():
    """Verify provider artifact stripping for unbiased judging."""
    text1 = "Model Gateway scaffolding response for [subtask_0]. Here is the answer."
    text2 = "Router Core scaffolding response placeholder. Actual content."
    text3 = "As an AI language model, water boils at 100 degrees Celsius."

    assert "scaffolding" not in strip_identifying_artifacts(text1).lower()
    assert "placeholder" not in strip_identifying_artifacts(text2).lower()
    assert not strip_identifying_artifacts(text3).startswith("As an AI language model")


def test_blind_llm_judge_order_randomization():
    """Verify that presentation order is randomized to prevent position bias."""
    prompt = "Summarize the report"
    r_out = "Router summary version"
    b_out = "Baseline summary version"

    orders = []
    for s in range(30):
        _, _, details = score_llm_judge(prompt, r_out, b_out, seed=s)
        orders.append(details["order_flipped"])

    # Both True and False should occur across 30 distinct seeds
    assert True in orders
    assert False in orders


def test_evaluate_task_dispatcher():
    """Verify evaluate_task dispatches to the correct scoring method."""
    math_task = {
        "task_id": "m1",
        "scoring_method": "math",
        "ground_truth": "#### 42",
        "prompt": "Compute 40 + 2",
    }
    res = evaluate_task(math_task, "#### 42", "#### 42")
    assert res["router_quality_score"] == 1.0
    assert res["baseline_quality_score"] == 1.0
    assert res["quality_delta"] == 0.0

    judge_task = {
        "task_id": "j1",
        "scoring_method": "llm_judge",
        "ground_truth": "Standard summary",
        "prompt": "Summarize this article",
    }
    j_res = evaluate_task(judge_task, "A comprehensive summary of the article.", "A good summary.")
    assert 0.0 <= j_res["router_quality_score"] <= 1.0
    assert 0.0 <= j_res["baseline_quality_score"] <= 1.0
    assert "router_details" in j_res["evaluation_details"]
