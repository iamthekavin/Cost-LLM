"""Response Normalization Engine for Cost-LLM Model Gateway.

Strips provider wrapper text, markdown enclosures, and standardizes raw text responses
into clean ModelCallResult payloads for Router Core's merger.
"""

import re
from typing import Optional

from shared.schemas.contracts import ModelCallResult

CONVERSATIONAL_PREFIXES = [
    r"^(?:Sure(?: thing)?|Certainly|Of course|Here is|Here's|Below is)[^:\n]*:\s*",
    r"^As an AI language model,[^:\n]*:\s*",
    r"^Here is the (?:information|code|summary|answer|result)[^:\n]*:\s*",
]

CONVERSATIONAL_SUFFIXES = [
    r"(?:\n\s*)?I hope this helps!?",
    r"(?:\n\s*)?Let me know if you (?:need|have)[^.\n]*\.?",
    r"(?:\n\s*)?Feel free to ask[^.\n]*\.?",
    r"(?:\n\s*)?Please let me know if you need anything else\.?",
]


def strip_markdown_fences(text: str) -> str:
    """Strip markdown code fence blocks (e.g. ```json ... ```) when raw payload is required."""
    trimmed = text.strip()
    match = re.match(r"^```[a-zA-Z0-9_-]*\s*\n([\s\S]*?)\n```$", trimmed)
    if match:
        return match.group(1).strip()
    # Also handle single-line fenced blocks e.g. ```print('hello')```
    match_inline = re.match(r"^```[a-zA-Z0-9_-]*\s*([\s\S]*?)\s*```$", trimmed)
    if match_inline:
        return match_inline.group(1).strip()
    return trimmed


def strip_conversational_chatter(text: str) -> str:
    """Remove boilerplate assistant preambles and polite sign-offs iteratively."""
    cleaned = text.strip()
    for pattern in CONVERSATIONAL_PREFIXES:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Iteratively strip suffixes from the tail
    changed = True
    while changed:
        prev = cleaned
        for pattern in CONVERSATIONAL_SUFFIXES:
            cleaned = re.sub(pattern + r"\s*$", "", cleaned, flags=re.IGNORECASE)
        changed = (cleaned != prev)

    return cleaned.strip()


def normalize_output_text(raw_text: Optional[str], strip_fences: bool = False) -> str:
    """Normalize raw provider output by cleaning whitespace and extraneous provider text."""
    if not raw_text:
        return ""

    normalized = raw_text.strip()
    # First strip conversational prefixes/suffixes
    normalized = strip_conversational_chatter(normalized)

    # If requested, strip markdown fences that wrap the remaining content
    if strip_fences:
        normalized = strip_markdown_fences(normalized)

    return normalized.strip()


def normalize_error_message(err: Exception) -> str:
    """Normalize various Python / HTTP exceptions into a clean diagnostic error string."""
    msg = str(err).strip()
    if not msg:
        return err.__class__.__name__
    return f"{err.__class__.__name__}: {msg}"


def build_normalized_result(
    subtask_id: str,
    model_used: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: float,
    cost_usd: float,
    raw_output: str,
    error: Optional[str] = None,
    strip_fences: bool = False,
) -> ModelCallResult:
    """Create a strictly validated ModelCallResult with normalized text content."""
    clean_output = normalize_output_text(raw_output, strip_fences=strip_fences) if not error else ""

    return ModelCallResult(
        subtask_id=subtask_id,
        model_used=model_used,
        tokens_in=max(0, tokens_in),
        tokens_out=max(0, tokens_out),
        latency_ms=round(max(0.0, latency_ms), 2),
        cost_usd=round(max(0.0, cost_usd), 6),
        raw_output=clean_output,
        error=error,
    )
