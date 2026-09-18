"""Unit tests for response normalization."""

from model_gateway.normalize import (
    build_normalized_result,
    strip_conversational_chatter,
    strip_markdown_fences,
)


def test_strip_markdown_fences():
    fenced_json = "```json\n{\"status\": \"active\", \"score\": 0.95}\n```"
    stripped = strip_markdown_fences(fenced_json)
    assert stripped == "{\"status\": \"active\", \"score\": 0.95}"

    fenced_text = "```\nPure plain text inside fence\n```"
    assert strip_markdown_fences(fenced_text) == "Pure plain text inside fence"

    plain_text = "Just normal text without fences"
    assert strip_markdown_fences(plain_text) == plain_text


def test_strip_conversational_chatter():
    prefix_sample = "Sure! Here is the summary:\nRevenue grew 15% year-over-year."
    cleaned = strip_conversational_chatter(prefix_sample)
    assert cleaned == "Revenue grew 15% year-over-year."

    suffix_sample = "The answer is 42.\n\nI hope this helps! Feel free to ask if you need anything else."
    cleaned_suffix = strip_conversational_chatter(suffix_sample)
    assert cleaned_suffix == "The answer is 42."


def test_build_normalized_result():
    res = build_normalized_result(
        subtask_id="sub-test",
        model_used="llama3.1:8b",
        tokens_in=20,
        tokens_out=50,
        latency_ms=145.6789,
        cost_usd=0.000000,
        raw_output="Certainly! Here is the python code:\n```python\nprint('hello')\n```\nLet me know if you need help!",
        strip_fences=True,
    )
    assert res.subtask_id == "sub-test"
    assert res.latency_ms == 145.68
    assert res.raw_output == "print('hello')"
    assert res.error is None
