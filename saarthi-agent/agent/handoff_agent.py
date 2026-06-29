"""
Handoff agent: decides whether a case needs to escalate to a human Business Correspondent
or Relationship Manager, and produces a structured ticket with full context.

Escalation happens for two distinct reasons, kept separate deliberately:
  1. REGULATED_ACTIONS — a hard rule. The agent never completes a KYC change on its own,
     regardless of how the conversation went. This is a compliance gate, not a model judgment.
  2. Conversational signal — the voice agent's outcome was "needs_human", meaning the
     customer asked for something the agent isn't equipped to resolve.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

from agent.reasoning_agent import CallPlan
from agent.voice_agent import CallOutcome

# Hard compliance rule: these actions always require human sign-off, never decided by the model.
REGULATED_ACTIONS = {"re_kyc"}


@dataclass
class HandoffTicket:
    account_id: str
    reason: str
    action: str
    language: str
    transcript: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def maybe_escalate(plan: CallPlan, outcome: CallOutcome) -> HandoffTicket | None:
    """Return a HandoffTicket if this case should go to a human, else None."""
    if plan.action in REGULATED_ACTIONS:
        return HandoffTicket(
            account_id=plan.account_id,
            reason="regulated_action",
            action=plan.action,
            language=plan.language,
            transcript=outcome.transcript,
        )

    if outcome.outcome == "needs_human":
        return HandoffTicket(
            account_id=plan.account_id,
            reason="conversational_escalation",
            action=plan.action,
            language=plan.language,
            transcript=outcome.transcript,
        )

    return None
