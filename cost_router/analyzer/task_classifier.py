"""
Task Classifier & Complexity Scorer.
Evaluates prompt complexity, semantic intent, structural signals, and reasoning requirements.
"""

import re
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class TaskAnalysis(BaseModel):
    complexity_score: float = Field(..., ge=0.0, le=1.0)
    primary_intent: str
    intent_confidence: float
    reasoning_signals: List[str] = Field(default_factory=list)
    has_code: bool = False
    has_math: bool = False
    has_pii: bool = False
    is_compound: bool = False
    feature_breakdown: Dict[str, float] = Field(default_factory=dict)
    summary: str


class TaskClassifier:
    """Analyzes prompt text to assess reasoning complexity and classify intent."""

    # Intent signature patterns
    INTENT_PATTERNS = {
        "DATA_EXTRACTION": [
            r"\bextract\b", r"\bpull out\b", r"\bfind all\b", r"\bparse\b", r"\bscrape\b",
            r"\bgrep\b", r"\bdetect entities\b", r"\blist of dates\b", r"\bphone numbers\b"
        ],
        "FORMATTING": [
            r"\bformat\b", r"\bconvert to json\b", r"\bconvert to markdown\b", r"\btable format\b",
            r"\brestructure\b", r"\bclean up\b", r"\bcsv format\b", r"\bstandardize\b"
        ],
        "CLASSIFICATION": [
            r"\bclassify\b", r"\bcategorize\b", r"\bsentiment\b", r"\btag this\b",
            r"\bspam or ham\b", r"\bintent\b", r"\blabel\b", r"\btriage\b"
        ],
        "SUMMARIZATION": [
            r"\bsummarize\b", r"\bsummary\b", r"\btldr\b", r"\bbrief overview\b",
            r"\bcondense\b", r"\bkey takeaways\b", r"\bmain points\b"
        ],
        "GENERAL_WRITING": [
            r"\bwrite an email\b", r"\bdraft a response\b", r"\brephrase\b", r"\bproofread\b",
            r"\bmake it sound\b", r"\bpolite\b", r"\bcreative story\b"
        ],
        "CODE_GENERATION": [
            r"\bpython\b", r"\bjavascript\b", r"\btypescript\b", r"\bcode\b", r"\bfunction\b",
            r"\bwrite a python\b", r"\bcode a function\b", r"\bdebug\b", r"\brefactor\b",
            r"\balgorithm\b", r"\bunit test\b", r"\bfastapi\b", r"\bsql query\b",
            r"```[a-zA-Z]*", r"\bdef \w+\(.*\):"
        ],
        "MULTI_STEP_REASONING": [
            r"\bdeduce\b", r"\bprove\b", r"\bstep-by-step logic\b", r"\brisk analysis\b",
            r"\bformal reasoning\b", r"\bgaap rules\b", r"\bgame theory\b", r"\broot cause\b",
            r"\bcausal inference\b", r"\bconsequences of\b", r"\bcounterfactual\b", r"\btheorem\b",
            r"\bbyzantine\b", r"\bconsensus algorithm\b", r"\bliveness\b", r"\bsecurity implications\b",
            r"\bmonopolist\b", r"\bdeadweight loss\b", r"\bconsumer surplus\b", r"\beconomic scenario\b"
        ],
        "MATHEMATICAL_PROOF": [
            r"\bcalculate eigenvalues\b", r"\bintegral\b", r"\bderivative\b", r"\blagrangian\b",
            r"\bmatrix inversion\b", r"\bcombinatorics\b", r"\bprobability distribution\b",
            r"\b\\int\b", r"\b\\sum\b", r"\btheorem\b", r"\blemma\b", r"\bproof\b",
            r"\b[A-Z]\s*=\s*\d+[\s\+\-\*\/]+[A-Za-z0-9]", r"\bcalculate the exact\b",
            r"\b[a-z]\s*<\s*[a-z]\/\d\b"
        ]
    }

    # Base baseline complexity per intent
    BASE_INTENT_COMPLEXITY = {
        "DATA_EXTRACTION": 0.12,
        "FORMATTING": 0.15,
        "CLASSIFICATION": 0.22,
        "SUMMARIZATION": 0.35,
        "GENERAL_WRITING": 0.42,
        "CODE_GENERATION": 0.65,
        "MULTI_STEP_REASONING": 0.88,
        "MATHEMATICAL_PROOF": 0.92,
    }

    # PII / Sensitive data detection
    PII_PATTERNS = [
        r"\b\d{3}-\d{2}-\d{4}\b",                 # SSN
        r"\b(?:\d{4}-){3}\d{4}\b",               # Credit Card
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", # Email
        r"\b(?:api_key|secret_key|bearer\s+[A-Za-z0-9_\-\.]+)\b", # Credentials
        r"\bconfidential\b|\bnda protected\b|\binternal only\b"
    ]

    # Multi-part conjunctions indicating decomposition candidates
    ACTION_VERBS = r"(?:extract|classify|summarize|write|calculate|convert|analyze|deduce|prove|conduct|verify|evaluate|format)"
    COMPOUND_MARKERS = [
        r"\bfirst\b.*\bthen\b",
        r"\band then\b",
        r"\bpart 1\b|\bstep 1\b",
        r"\bafter that\b",
        r"\bextract.*and classify.*and write\b",
        rf"(?:^|\s)\d+[\.\)]\s+{ACTION_VERBS}\b.*?(?:^|\s)\d+[\.\)]\s+{ACTION_VERBS}\b",
    ]

    def analyze(self, prompt: str) -> TaskAnalysis:
        lower_prompt = prompt.lower()
        signals = []
        feature_breakdown = {}

        # 1. Intent Detection
        detected_intents = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            matches = sum(len(re.findall(p, lower_prompt)) for p in patterns)
            if matches > 0:
                detected_intents[intent] = matches

        if detected_intents:
            primary_intent = max(detected_intents, key=detected_intents.get)
            intent_confidence = min(0.95, 0.5 + 0.15 * detected_intents[primary_intent])
        else:
            primary_intent = "GENERAL_WRITING"
            intent_confidence = 0.40

        base_complexity = self.BASE_INTENT_COMPLEXITY.get(primary_intent, 0.40)
        feature_breakdown["base_intent"] = base_complexity

        # 2. Structural & Syntactic Signals
        has_code = bool(re.search(r"```|def\s+\w+|import\s+\w+|function\s*\(|SELECT\s+.*FROM", prompt))
        if has_code:
            signals.append("code_syntax_present")
            feature_breakdown["code_bonus"] = 0.15

        has_math = bool(re.search(r"\\int|\\sum|\bderive\b|\bequation\b|\bpolynomial\b|\beigenvalues\b|\blagrangian\b", prompt, re.IGNORECASE))
        if has_math:
            signals.append("math_formalism_present")
            feature_breakdown["math_bonus"] = 0.18

        # 3. Reasoning Cues
        reasoning_count = len(re.findall(
            r"\b(why|explain why|implications|compare and contrast|evaluate|trade-off|deduce|audit)\b",
            lower_prompt
        ))
        if reasoning_count > 0:
            cue_weight = min(0.25, reasoning_count * 0.08)
            signals.append(f"reasoning_cues_found ({reasoning_count})")
            feature_breakdown["reasoning_cues"] = cue_weight

        # 4. Length / Token Load Adjustment
        word_count = len(prompt.split())
        length_penalty = 0.0
        if word_count > 400:
            length_penalty = 0.10
            signals.append("large_context_window")
        elif word_count < 15:
            length_penalty = -0.05
            signals.append("very_short_prompt")
        feature_breakdown["length_adjustment"] = length_penalty

        # 5. Compound / Multi-part Detection
        is_compound = any(bool(re.search(pattern, lower_prompt, re.IGNORECASE)) for pattern in self.COMPOUND_MARKERS)

        if is_compound:
            signals.append("compound_multi_part_request")
            feature_breakdown["multi_part_complexity"] = 0.12

        # 6. PII / Sensitivity Check
        has_pii = any(bool(re.search(p, prompt, re.IGNORECASE)) for p in self.PII_PATTERNS)
        if has_pii:
            signals.append("sensitive_pii_detected")

        # Sum and bound complexity score in [0.05, 0.99]
        total_score = sum(feature_breakdown.values())
        final_score = round(max(0.05, min(0.99, total_score)), 3)

        summary = (
            f"Detected {primary_intent} with score {final_score} "
            f"({len(signals)} key signals identified)"
        )

        return TaskAnalysis(
            complexity_score=final_score,
            primary_intent=primary_intent,
            intent_confidence=round(intent_confidence, 2),
            reasoning_signals=signals,
            has_code=has_code,
            has_math=has_math,
            has_pii=has_pii,
            is_compound=is_compound,
            feature_breakdown=feature_breakdown,
            summary=summary,
        )


# Global singleton classifier
global_classifier = TaskClassifier()
