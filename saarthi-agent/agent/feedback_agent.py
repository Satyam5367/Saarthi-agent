"""
Feedback agent: logs each call's outcome and derives a simple success-rate-by-cluster
table that the reasoning agent can use to reprioritize future targeting.

This is intentionally a simple heuristic (not a real online-learning loop) — see
docs/ARCHITECTURE.md for what a production version would replace it with.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agent.reasoning_agent import CallPlan
from agent.voice_agent import CallOutcome

OUTCOMES_PATH = Path(__file__).resolve().parent.parent / "data" / "outcomes.jsonl"


def log_outcome(plan: CallPlan, outcome: CallOutcome) -> None:
    """Append one call's plan + outcome to the outcomes log."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "account_id": plan.account_id,
        "language": plan.language,
        "action": plan.action,
        "priority_score": plan.priority_score,
        "outcome": outcome.outcome,
    }
    OUTCOMES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTCOMES_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")


def compute_success_rates() -> dict:
    """Read the outcomes log and compute a success rate per 'language:action' cluster.

    Returns a dict like {"Hindi:rupay_activation": 0.62, ...}. Used by the reasoning agent
    to nudge priority scores toward clusters that have historically converted well.
    """
    if not OUTCOMES_PATH.exists():
        return {}

    totals: dict[str, int] = {}
    completed: dict[str, int] = {}

    with OUTCOMES_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            key = f"{record['language']}:{record['action']}"
            totals[key] = totals.get(key, 0) + 1
            if record["outcome"] == "completed":
                completed[key] = completed.get(key, 0) + 1

    return {key: completed.get(key, 0) / total for key, total in totals.items()}
