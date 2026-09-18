"""Tests for Benchmark Task Dataset (Member D)."""
import json
import os


def test_tasks_file_exists_and_count():
    """Verify tasks.jsonl exists and has between 60 and 100 tasks."""
    tasks_path = os.path.join(os.path.dirname(__file__), "..", "tasks", "tasks.jsonl")
    assert os.path.exists(tasks_path), f"tasks.jsonl not found at {tasks_path}"

    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    assert 60 <= len(tasks) <= 100, f"Task count {len(tasks)} outside expected 60-100 range"


def test_smoke_tasks_file():
    """Verify smoke_tasks.jsonl exists and contains around 10 tasks."""
    smoke_path = os.path.join(os.path.dirname(__file__), "..", "tasks", "smoke_tasks.jsonl")
    assert os.path.exists(smoke_path), f"smoke_tasks.jsonl not found at {smoke_path}"

    with open(smoke_path, "r", encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    assert 5 <= len(tasks) <= 15, f"Smoke task count {len(tasks)} outside expected range"


def test_task_schema_validation():
    """Verify each task satisfies required fields and valid enums."""
    tasks_path = os.path.join(os.path.dirname(__file__), "..", "tasks", "tasks.jsonl")
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    valid_tiers = {"trivial", "moderate", "deep"}
    valid_methods = {"exact_match", "regex", "math", "rule_based", "code", "llm_judge"}

    tier_counts = {"trivial": 0, "moderate": 0, "deep": 0}
    multipart_count = 0

    seen_ids = set()
    for t in tasks:
        assert "task_id" in t and t["task_id"], "Task missing task_id"
        assert t["task_id"] not in seen_ids, f"Duplicate task_id {t['task_id']}"
        seen_ids.add(t["task_id"])

        assert "prompt" in t and len(t["prompt"]) > 5, f"Invalid prompt in {t['task_id']}"
        assert "category" in t and t["category"], f"Invalid category in {t['task_id']}"
        assert t["expected_difficulty"] in valid_tiers, f"Invalid tier in {t['task_id']}"
        tier_counts[t["expected_difficulty"]] += 1

        assert t.get("scoring_method") in valid_methods, f"Invalid method in {t['task_id']}"
        assert isinstance(t.get("is_multi_part"), bool), f"is_multi_part must be boolean in {t['task_id']}"
        if t.get("is_multi_part"):
            multipart_count += 1

    # Verify distribution across tiers
    for tier, count in tier_counts.items():
        assert count >= 15, f"Tier '{tier}' has too few tasks ({count})"

    # Verify presence of multi-part prompts
    assert multipart_count >= 5, f"Too few multi-part prompts ({multipart_count})"
