"""
Voice agent: conducts the (simulated) vernacular call.

In production this wraps real ASR → LLM → TTS calls over a telephony API
(e.g. Exotel/Knowlarity) using open Indic speech models (AI4Bharat / Bhashini).

This scaffold stubs ASR/TTS with a multi-turn text simulation so the decision logic
can be inspected and tested without live infrastructure.

To go to production: replace `_simulate_conversation()` with a real call loop.
The public interface `run_call(plan) -> CallOutcome` stays unchanged.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, asdict

from agent.reasoning_agent import CallPlan

OUTCOMES = ("completed", "declined", "needs_human", "no_answer")

# Outcome probability weights per action.
# re_kyc is intentionally weighted toward needs_human — it is a regulated action
# and the handoff_agent enforces escalation as a hard rule regardless of this outcome.
_OUTCOME_WEIGHTS: dict[str, dict[str, float]] = {
    "rupay_activation": {"completed": 0.55, "declined": 0.15, "needs_human": 0.15, "no_answer": 0.15},
    "upi_setup":        {"completed": 0.40, "declined": 0.20, "needs_human": 0.25, "no_answer": 0.15},
    "re_kyc":           {"completed": 0.10, "declined": 0.10, "needs_human": 0.65, "no_answer": 0.15},
}

# Realistic multi-turn conversation templates per action × outcome
_CONVERSATIONS: dict[str, dict[str, list[str]]] = {
    "rupay_activation": {
        "completed": [
            "[customer] Haan, kya karna hoga? (Yes, what do I need to do?)",
            "[agent] Please visit your nearest SBI ATM and enter your card PIN to activate it. I can also send an SMS with the steps.",
            "[customer] ATM pe jaana padega kya? (Do I need to go to ATM?)",
            "[agent] Yes, just once — it takes under 2 minutes. Shall I send the nearest ATM address to your number?",
            "[customer] Theek hai, bhej dijiye. (Okay, please send it.)",
            "[system] RuPay activation steps sent via SMS. Call completed.",
        ],
        "declined": [
            "[customer] Abhi nahi chahiye, baad mein dekhenge. (Not needed now, will see later.)",
            "[agent] Understood. The card benefit remains available — we will not call again. Thank you.",
        ],
        "needs_human": [
            "[customer] Mujhe samajh nahi aa raha. Koi branch mein aa sakta hai? (I don't understand. Can someone come to the branch?)",
            "[agent] Of course — I am connecting you with your nearest branch representative right now.",
        ],
        "no_answer": [
            "[system] No answer after 3 rings — call ended. Scheduled for retry in 48 hours.",
        ],
    },
    "upi_setup": {
        "completed": [
            "[customer] UPI kya hota hai? (What is UPI?)",
            "[agent] It lets you send and receive money instantly using your phone — no cash needed.",
            "[customer] Phone mein karna hoga? (Do I do it on the phone?)",
            "[agent] Yes, I will guide you step by step through the YONO SBI app. Do you have it installed?",
            "[customer] Haan hai. (Yes I have it.)",
            "[system] UPI setup walkthrough initiated. Call completed.",
        ],
        "declined": [
            "[customer] Mujhe phone se paisa nahi bhejana. (I don't want to send money from phone.)",
            "[agent] That is completely fine. Your account remains active. Thank you for your time.",
        ],
        "needs_human": [
            "[customer] Mera phone naya hai, setup nahi aata. (My phone is new, I can't set it up.)",
            "[agent] No problem — I am connecting you with a customer care representative who will assist you personally.",
        ],
        "no_answer": [
            "[system] No answer after 3 rings — call ended. Scheduled for retry in 48 hours.",
        ],
    },
    "re_kyc": {
        "completed": [
            "[customer] Kya documents chahiye? (What documents are needed?)",
            "[agent] Just your Aadhaar number and a selfie — it takes about 5 minutes online.",
            "[customer] Online nahi aata mujhe. (I can't do it online.)",
            "[agent] Connecting you with a Business Correspondent who can visit your location.",
        ],
        "declined": [
            "[customer] Mujhe nahi karwana abhi. (I don't want to do it right now.)",
            "[agent] Understood. Please note your account may be restricted until KYC is complete. We will follow up.",
        ],
        "needs_human": [
            "[customer] Yeh sab mujhe nahi pata. Koi aa sakta hai ghar? (I don't know all this. Can someone come home?)",
            "[agent] Absolutely — I am escalating to a Business Correspondent who will arrange a doorstep visit.",
        ],
        "no_answer": [
            "[system] No answer after 3 rings — call ended. Scheduled for retry in 48 hours.",
        ],
    },
}


@dataclass
class CallOutcome:
    account_id: str
    action: str
    outcome: str
    transcript: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def run_call(plan: CallPlan, seed: int | None = None) -> CallOutcome:
    """Simulate placing the vernacular call and return the outcome."""
    rng = random.Random(seed)
    weights = _OUTCOME_WEIGHTS[plan.action]
    outcome = rng.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]

    transcript = [f"[agent, {plan.language}] {plan.opening_line}"]
    transcript += _CONVERSATIONS[plan.action][outcome]

    return CallOutcome(
        account_id=plan.account_id,
        action=plan.action,
        outcome=outcome,
        transcript=transcript,
    )
