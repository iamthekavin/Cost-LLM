"""Utility script to generate JSON schema files from Pydantic models."""

import json
from pathlib import Path

from shared.schemas.contracts import (
    BenchmarkRecord,
    DecisionLogEntry,
    FinalResponse,
    ModelCallResult,
    RoutingDecision,
    RoutingRequest,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "json"


def export_schemas():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    models = {
        "RoutingRequest": RoutingRequest,
        "RoutingDecision": RoutingDecision,
        "ModelCallResult": ModelCallResult,
        "FinalResponse": FinalResponse,
        "DecisionLogEntry": DecisionLogEntry,
        "BenchmarkRecord": BenchmarkRecord,
    }

    for name, model in models.items():
        filepath = OUTPUT_DIR / f"{name}.json"
        schema = model.model_json_schema()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)
        print(f"Exported {filepath}")


if __name__ == "__main__":
    export_schemas()
