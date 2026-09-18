"""Control Plane FastAPI Application & Dashboard (Member C)."""
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from shared.schemas.contracts import DecisionLogEntry

app = FastAPI(
    title="Cost-LLM Control Plane",
    description="Transparency logging, policy overrides, and administrative dashboard",
    version="0.1.0",
)

# In-memory store for scaffold; Member C will back this with SQLAlchemy (SQLite/PostgreSQL)
_decision_logs: Dict[str, List[DecisionLogEntry]] = {}
_active_overrides: Dict[str, Any] = {}


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "control-plane", "version": "0.1.0"}


@app.post("/v1/logs", response_model=DecisionLogEntry)
async def log_decision(entry: DecisionLogEntry):
    """Ingest and persist a decision log entry for transparency and audit."""
    if entry.request_id not in _decision_logs:
        _decision_logs[entry.request_id] = []
    _decision_logs[entry.request_id].append(entry)
    return entry


@app.get("/v1/logs/{request_id}", response_model=List[DecisionLogEntry])
async def get_logs_for_request(request_id: str):
    """Retrieve all decision log entries for a given request."""
    if request_id not in _decision_logs:
        raise HTTPException(status_code=404, detail="Request logs not found")
    return _decision_logs[request_id]


@app.get("/v1/overrides")
async def get_overrides():
    """Retrieve active routing override policies."""
    return {"overrides": _active_overrides}


@app.post("/v1/overrides")
async def set_override(rule: Dict[str, Any]):
    """Set or update an override rule (e.g. force all queries by user X to GPT-4o)."""
    rule_id = rule.get("rule_id", "default")
    _active_overrides[rule_id] = rule
    return {"status": "override_saved", "rule_id": rule_id}


@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Lightweight dashboard placeholder for Member C to build out."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cost-LLM Control Plane Dashboard</title>
        <style>
            body { font-family: Inter, sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem; }
            h1 { color: #38bdf8; }
            .card { background: #1e293b; padding: 1.5rem; border-radius: 8px; border: 1px solid #334155; }
        </style>
    </head>
    <body>
        <h1>Cost-LLM Control Plane & Transparency Dashboard</h1>
        <div class="card">
            <p>Status: <strong>Active</strong></p>
            <p>Member C Workstream: Real-time decision stream, policy override manager, and cost tracking UI.</p>
        </div>
    </body>
    </html>
    """
