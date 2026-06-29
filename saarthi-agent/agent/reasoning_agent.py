"""
Reasoning agent: the autonomous planning core of Saarthi.

Given one dormant-account record, decides:
  - which language to call in
  - which single reactivation action to offer
  - a priority score (so the pipeline can rank who to call first)
  - a short opening line for the voice agent to use

The decision logic lives behind the public `plan_call()` interface.
The LLM provider is a swappable dependency — Azure OpenAI, Sarvam AI, Krutrim, or any
enterprise LLM SBI standardizes on only requires replacing `_llm_plan()`.
Falls back to a deterministic rule-based policy when no API key is set.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict


ACTIONS = ("rupay_activation", "upi_setup", "re_kyc")

# Language-specific warm opening lines — avoids calling a Tamil customer in Hindi
_OPENERS: dict[str, dict[str, str]] = {
    "rupay_activation": {
        "Hindi":   "Namaste, aapke bank ki taraf se ek card suvidha ke baare mein call kar rahe hain.",
        "Bengali": "Namaskar, apnar bank theke apnar card suvidhā somporkhe call korchi.",
        "Tamil":   "Vanakkam, ungal bank ilirundhu ungal card payan pattri azhaikiren.",
        "Telugu":  "Namaskaram, mee bank nunchi mee card suvidha gurinchi call chesttunnamu.",
        "Marathi": "Namaskar, tumchya bankekadun tumchya card subidhe vishayi call karat aaho.",
        "Kannada": "Namaskara, nimage bank ninda card suvidhe kurichu call maaduttiddeve.",
        "default": "Namaste, this is a call from your bank about a card benefit waiting for you.",
    },
    "upi_setup": {
        "Hindi":   "Namaste, aapke bank ki taraf se UPI suvidha shuru karne ke liye call kar rahe hain.",
        "Bengali": "Namaskar, apnar bank theke apnar UPI shuru korte call korchi.",
        "Tamil":   "Vanakkam, ungal bank ilirundhu UPI thottanguvatharkku azhaikiren.",
        "Telugu":  "Namaskaram, mee bank nunchi UPI setup cheyyadam kosam call chesttunnamu.",
        "Marathi": "Namaskar, tumchya bankekadun UPI suru karnyasathi call karat aaho.",
        "Kannada": "Namaskara, nimage UPI setup maadalu bank ninda call maaduttiddeve.",
        "default": "Namaste, this is a call from your bank to help you start using UPI.",
    },
    "re_kyc": {
        "Hindi":   "Namaste, aapke bank ki taraf se account update ke baare mein call kar rahe hain.",
        "Bengali": "Namaskar, apnar bank theke apnar account update somporkhe call korchi.",
        "Tamil":   "Vanakkam, ungal bank ilirundhu ungal account padhivaippu pattri azhaikiren.",
        "Telugu":  "Namaskaram, mee bank nunchi account update gurinchi call chesttunnamu.",
        "Marathi": "Namaskar, tumchya bankekadun account update vishayi call karat aaho.",
        "Kannada": "Namaskara, nima account update kurichu bank ninda call maaduttiddeve.",
        "default": "Namaste, this is a call from your bank about a quick account update needed.",
    },
}


def _get_opener(action: str, language: str) -> str:
    return _OPENERS[action].get(language, _OPENERS[action]["default"])


@dataclass
class CallPlan:
    account_id: str
    language: str
    action: str
    priority_score: float
    opening_line: str
    rationale: str

    def to_dict(self) -> dict:
        return asdict(self)


def _rule_based_plan(account: dict, success_rates: dict | None = None) -> CallPlan:
    """Deterministic fallback policy — no API key required."""
    language = account.get("preferred_language_hint", "Hindi")

    # Action priority: rupay > upi > re_kyc (least intrusive first)
    if account.get("rupay_status") == "issued_unused":
        action = "rupay_activation"
    elif account.get("upi_status") == "not_registered" and account.get("rupay_status") != "none":
        action = "upi_setup"
    else:
        action = "re_kyc"

    # Priority score: longer dormancy + unclaimed DBT = higher urgency
    priority = min(1.0, account.get("dormancy_days", 0) / 1500)
    if account.get("last_dbt_credit_unclaimed"):
        priority = min(1.0, priority + 0.2)
    if not account.get("phone_reachable", True):
        priority *= 0.5  # de-prioritise unreachable numbers

    # Nudge using past cluster success rate
    if success_rates:
        key = f"{language}:{action}"
        rate = success_rates.get(key)
        if rate is not None:
            priority = min(1.0, priority * (0.6 + 0.4 * rate))

    return CallPlan(
        account_id=account["account_id"],
        language=language,
        action=action,
        priority_score=round(priority, 3),
        opening_line=_get_opener(action, language),
        rationale="rule_based_fallback",
    )


def _llm_plan(account: dict, success_rates: dict | None = None) -> CallPlan:
    """LLM-powered planning — vendor-agnostic interface, Anthropic API as reference impl."""
    import anthropic

    client = anthropic.Anthropic()
    prompt = f"""You are the reasoning agent in Saarthi, a voice-first agentic AI that reactivates
dormant PMJDY bank accounts in India. Given this account record, decide the single best next action.

Account record:
{json.dumps(account, indent=2)}

Past success rates by "language:action" cluster (empty on first run):
{json.dumps(success_rates or {}, indent=2)}

Rules:
- Prefer the least-intrusive action: rupay_activation > upi_setup > re_kyc
- De-prioritise accounts where phone_reachable is false
- Opening line MUST be in the customer's preferred_language_hint (romanised transliteration)

Respond ONLY with a JSON object — no markdown, no explanation:
{{
  "language": "<customer's preferred language>",
  "action": "<rupay_activation | upi_setup | re_kyc>",
  "priority_score": <float 0.0–1.0, higher means call sooner>,
  "opening_line": "<warm single-sentence opener in the customer's language, romanised>",
  "rationale": "<one sentence explaining the choice>"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    parsed = json.loads(text)

    return CallPlan(
        account_id=account["account_id"],
        language=parsed["language"],
        action=parsed["action"],
        priority_score=float(parsed["priority_score"]),
        opening_line=parsed["opening_line"],
        rationale=parsed["rationale"],
    )


def plan_call(account: dict, success_rates: dict | None = None) -> CallPlan:
    """Public entry point — decide the call plan for one account."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _llm_plan(account, success_rates)
        except Exception as exc:  # noqa: BLE001
            print(f"[reasoning_agent] LLM call failed ({exc}), falling back to rule-based policy")
    return _rule_based_plan(account, success_rates)
