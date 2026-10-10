"""
Decomposer: Splits complex multi-part requests into discrete, optimizable sub-tasks.
Enables fine-grained routing where cheap tasks route locally and complex tasks route to frontier models.
"""

import re
from typing import List
from cost_router.config import ModelTier, RoutingPolicy, TIER_DEFAULT_MODELS, POLICY_THRESHOLDS
from cost_router.models.base import SubTaskPlan
from cost_router.analyzer.task_classifier import TaskClassifier


class PromptDecomposer:
    """Detects multi-part requests, breaks them down into subtasks, and assigns sub-complexity."""

    def __init__(self, classifier: TaskClassifier):
        self.classifier = classifier

    def can_decompose(self, prompt: str, analysis) -> bool:
        """Determines if the prompt contains distinct, separable tasks."""
        if not analysis.is_compound:
            return False
        # Avoid decomposing trivial short snippets where overhead exceeds benefit
        if len(prompt.split()) < 8:
            return False
        return True

    def decompose(
        self, prompt: str, policy: RoutingPolicy = RoutingPolicy.BALANCED
    ) -> List[SubTaskPlan]:
        """Splits compound prompt into discrete SubTaskPlan objects."""
        raw_parts = self._split_prompt_clauses(prompt)

        # If splitting resulted in only 1 meaningful chunk, return single task
        if len(raw_parts) <= 1:
            analysis = self.classifier.analyze(prompt)
            tier, model, reason = self._select_tier_and_model(analysis.complexity_score, policy)
            return [
                SubTaskPlan(
                    id=1,
                    title="Complete Request Execution",
                    prompt_chunk=prompt,
                    intent=analysis.primary_intent,
                    complexity_score=analysis.complexity_score,
                    selected_tier=tier,
                    selected_model=model,
                    reasoning=f"Handled as unified task: {reason}",
                    dependencies=[],
                )
            ]

        subtasks: List[SubTaskPlan] = []
        for idx, part in enumerate(raw_parts, start=1):
            analysis = self.classifier.analyze(part)
            tier, model, reason = self._select_tier_and_model(analysis.complexity_score, policy)

            title = self._derive_subtask_title(part, analysis.primary_intent, idx)
            dependencies = [idx - 1] if idx > 1 else []

            subtasks.append(
                SubTaskPlan(
                    id=idx,
                    title=title,
                    prompt_chunk=part.strip(),
                    intent=analysis.primary_intent,
                    complexity_score=analysis.complexity_score,
                    selected_tier=tier,
                    selected_model=model,
                    reasoning=reason,
                    dependencies=dependencies,
                )
            )

        return subtasks

    def _split_prompt_clauses(self, prompt: str) -> List[str]:
        """Splits prompt using sequential cues and numbered lists."""
        # 1. Numbered list: e.g. "1. Extract... 2. Classify... 3. Write..."
        numbered_matches = re.split(r"(?:^|\s+)\d+[\.\)]\s+", prompt)
        filtered_numbered = [p.strip() for p in numbered_matches if p.strip()]
        if len(filtered_numbered) >= 2:
            return filtered_numbered

        # 2. Step / Part pattern: e.g. "Step 1: ... Step 2: ..."
        step_matches = re.split(r"(?:^|\s+)(?:step|part)\s+\d+[:\.\-]\s*", prompt, flags=re.IGNORECASE)
        filtered_steps = [p.strip() for p in step_matches if p.strip()]
        if len(filtered_steps) >= 2:
            return filtered_steps

        # 3. First ... then ... (optionally: finally ...)
        first_match = re.match(
            r"^(?:first[\s,:]+)(.*?)(?:,?\s+then\s+|,?\s+next\s+)(.*?)(?:,?\s+finally\s+(.*)|,?\s+lastly\s+(.*))?$",
            prompt.strip(),
            re.IGNORECASE | re.DOTALL,
        )
        if first_match:
            parts = [g.strip() for g in first_match.groups() if g and g.strip()]
            if len(parts) >= 2:
                return parts

        # 4. Explicit conjunction delimiters: ", and then ", "; then ", etc.
        parts = re.split(
            r",?\s+(?:and\s+)?then\s+|;\s*(?:then\s+)?|,\s*(?:and\s+)?after\s+that\s+|,\s*(?:and\s+)?finally\s+",
            prompt.strip(),
            flags=re.IGNORECASE,
        )
        parts = [p.strip().lstrip(",;").strip() for p in parts if len(p.strip()) > 8]
        if len(parts) >= 2:
            parts[0] = re.sub(r"^first[\s,:]+", "", parts[0], flags=re.IGNORECASE).strip()
            return parts

        return [prompt]

    def _derive_subtask_title(self, chunk: str, intent: str, step: int) -> str:
        intent_titles = {
            "DATA_EXTRACTION": "Entity & Data Extraction",
            "FORMATTING": "Structural Standardization & Formatting",
            "CLASSIFICATION": "Classification & Intent Tagging",
            "SUMMARIZATION": "Information Condensation & Summarization",
            "GENERAL_WRITING": "Drafting & Presentation",
            "CODE_GENERATION": "Algorithmic Code Generation",
            "MULTI_STEP_REASONING": "Deep Reasoning & Impact Analysis",
            "MATHEMATICAL_PROOF": "Formal Mathematical Deduction",
        }
        name = intent_titles.get(intent, f"Processing Phase {step}")
        return f"Part {step}: {name}"

    def _select_tier_and_model(
        self, complexity: float, policy: RoutingPolicy
    ) -> tuple[ModelTier, str, str]:
        """Maps complexity score to appropriate tier and model under policy."""
        thresholds = POLICY_THRESHOLDS.get(policy, POLICY_THRESHOLDS[RoutingPolicy.BALANCED])

        if policy == RoutingPolicy.LOCAL_ONLY or complexity < thresholds["local_max"]:
            tier = ModelTier.LOCAL
            model = TIER_DEFAULT_MODELS[tier]
            reason = f"Complexity {complexity:.2f} <= {thresholds['local_max']:.2f}. Handled on local zero-cost model ({model})."
        elif complexity < thresholds["cheap_max"]:
            tier = ModelTier.CHEAP
            model = TIER_DEFAULT_MODELS[tier]
            reason = f"Complexity {complexity:.2f} <= {thresholds['cheap_max']:.2f}. Routed to high-throughput low-cost tier ({model})."
        elif complexity < thresholds["balanced_max"]:
            tier = ModelTier.BALANCED
            model = TIER_DEFAULT_MODELS[tier]
            reason = f"Complexity {complexity:.2f} <= {thresholds['balanced_max']:.2f}. Routed to balanced intelligence tier ({model})."
        else:
            tier = ModelTier.FRONTIER
            model = TIER_DEFAULT_MODELS[tier]
            reason = f"Complexity {complexity:.2f} > {thresholds['balanced_max']:.2f}. Requires frontier reasoning tier ({model})."

        return tier, model, reason
