"""
Unit tests for Multi-Part Prompt Decomposer and Aggregation.
"""

import pytest
from cost_router.config import RoutingPolicy, ModelTier
from cost_router.analyzer.task_classifier import TaskClassifier
from cost_router.analyzer.decomposer import PromptDecomposer
from cost_router.router.engine import RoutingEngine


def test_decomposer_splits_multi_step():
    classifier = TaskClassifier()
    decomposer = PromptDecomposer(classifier)

    prompt = (
        "1. Extract all invoice numbers and dates from the file. "
        "2. Classify if the transaction exceeds the departmental authorization limits. "
        "3. Conduct a formal fiscal risk analysis on potential compliance liabilities under corporate GAAP rules."
    )

    analysis = classifier.analyze(prompt)
    assert decomposer.can_decompose(prompt, analysis) is True

    subtasks = decomposer.decompose(prompt, RoutingPolicy.BALANCED)
    assert len(subtasks) == 3

    # Check that subtask 1 is extraction/formatting
    assert subtasks[0].intent in ["DATA_EXTRACTION", "FORMATTING"]
    # Check that subtask 3 is reasoning
    assert subtasks[2].intent in ["MULTI_STEP_REASONING", "GENERAL_WRITING"]
    # Subtask 1 should have lower complexity than subtask 3
    assert subtasks[0].complexity_score < subtasks[2].complexity_score


@pytest.mark.asyncio
async def test_end_to_end_multi_part_routing():
    engine = RoutingEngine()
    compound_prompt = (
        "1. Extract all names and emails from: John Doe (john@acme.com), Sarah Smith (sarah@corp.com). "
        "2. Classify whether this belongs to sales or engineering. "
        "3. Deduce and write an in-depth audit assessment on corporate data privacy compliance."
    )

    response = await engine.route(prompt=compound_prompt, policy=RoutingPolicy.BALANCED)

    assert response.trace.is_decomposed is True
    assert len(response.subtask_results) >= 2
    assert "Synthesized Solution" in response.final_output
    assert response.cost_summary.baseline_cost_usd > response.cost_summary.total_cost_usd
    assert response.cost_summary.reduction_percentage > 0.0
