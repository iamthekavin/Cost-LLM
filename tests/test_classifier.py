"""
Unit tests for Task Classifier and Complexity Scorer.
"""

import pytest
from cost_router.analyzer.task_classifier import TaskClassifier


@pytest.fixture
def classifier():
    return TaskClassifier()


def test_classify_simple_extraction(classifier):
    prompt = "Extract all dates and invoice amounts from this text: Invoice #123, dated 2026-05-01."
    analysis = classifier.analyze(prompt)
    assert analysis.primary_intent == "DATA_EXTRACTION"
    assert analysis.complexity_score < 0.35


def test_classify_formatting(classifier):
    prompt = "Convert to json: Item A (10), Item B (20)"
    analysis = classifier.analyze(prompt)
    assert analysis.primary_intent == "FORMATTING"
    assert analysis.complexity_score < 0.35


def test_classify_coding(classifier):
    prompt = "Write a python function to implement an async worker pool with retry logic: def worker():"
    analysis = classifier.analyze(prompt)
    assert analysis.primary_intent == "CODE_GENERATION"
    assert analysis.has_code is True
    assert analysis.complexity_score >= 0.50


def test_classify_multi_step_reasoning(classifier):
    prompt = (
        "Deduce why the system deadlocked by performing a causal inference step-by-step logic proof. "
        "Explain the formal reasoning and implications of the counterfactual."
    )
    analysis = classifier.analyze(prompt)
    assert analysis.primary_intent == "MULTI_STEP_REASONING"
    assert analysis.complexity_score >= 0.75


def test_complexity_hierarchy(classifier):
    p_easy = "Extract emails from this list: test@example.com"
    p_med = "Write a python script to parse CSV files and sort rows."
    p_hard = "Prove that there exists no polynomial-time algorithm for this NP-complete problem, deriving each mathematical lemma."

    a_easy = classifier.analyze(p_easy)
    a_med = classifier.analyze(p_med)
    a_hard = classifier.analyze(p_hard)

    assert a_easy.complexity_score < a_med.complexity_score < a_hard.complexity_score


def test_detect_compound_request(classifier):
    prompt = "First extract all numbers from the table, then classify them by department, and finally write an audit report."
    analysis = classifier.analyze(prompt)
    assert analysis.is_compound is True
