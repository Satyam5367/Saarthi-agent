"""
Pipeline: orchestrates the full five-step Saarthi flow.

Run with:  python -m agent.pipeline [--limit N] [--seed N] [--no-color]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.reasoning_agent import plan_call
from agent.voice_agent import run_call
from agent.handoff_agent import maybe_escalate
from agent.feedback_agent import log_outcome, compute_success_rates

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_dormant_accounts.json"

# ANSI colour codes — disabled automatically when --no-color is passed
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_CYAN   = "\033[96m"
_DIM    = "\033[2m"
_ORANGE = "\033[38;5;208m"

_USE_COLOR = True


def _c(code: str, text: str) -> str:
    return f"{code}{text}{_RESET}" if _USE_COLOR else text


def load_accounts(limit: int | None = None) -> list[dict]:
    with DATA_PATH.open() as f:
        accounts = json.load(f)
    return accounts[:limit] if limit else accounts


def run_pipeline(limit: int | None = None, seed: int | None = None) -> None:
    accounts = load_accounts(limit)
    success_rates = compute_success_rates()

    print()
    print(_c(_BOLD, "╔══════════════════════════════════════════════════════════════╗"))
    print(_c(_BOLD, "║          SAARTHI — Dormant Account Reactivation Agent        ║"))
    print(_c(_BOLD, "╚══════════════════════════════════════════════════════════════╝"))
    print(_c(_DIM, f"  Accounts loaded : {len(accounts)}"))
    print(_c(_DIM, f"  Success-rate clusters from prior runs : {len(success_rates)}"))
    print()

    # ── Step 1: Dormancy signal — each record is a consented, pre-flagged account ──
    # ── Step 2: Reasoning agent — build call plans, then sort by priority ──────────
    plans = [plan_call(account, success_rates) for account in accounts]
    account_map = {a["account_id"]: a for a in accounts}
    plans.sort(key=lambda p: p.priority_score, reverse=True)   # highest priority first

    # counters for summary
    counts = {"completed": 0, "declined": 0, "needs_human": 0, "no_answer": 0}
    escalations = 0

    for plan in plans:
        account = account_map[plan.account_id]

        # ── Step 3: Voice agent ──────────────────────────────────────────────────
        outcome = run_call(plan, seed=seed)

        # ── Step 4: Handoff agent ────────────────────────────────────────────────
        ticket = maybe_escalate(plan, outcome)

        # ── Step 5: Feedback agent ───────────────────────────────────────────────
        log_outcome(plan, outcome)

        counts[outcome.outcome] += 1
        if ticket:
            escalations += 1

        # ── Print call record ────────────────────────────────────────────────────
        state_tag = f"({account['state']})"
        print(_c(_BOLD + _CYAN, f"  ▶  {plan.account_id}") + _c(_DIM, f"  {state_tag}"))
        print(f"     Language : {_c(_CYAN, plan.language)}   "
              f"Action : {_c(_YELLOW, plan.action)}   "
              f"Priority : {_c(_BOLD, str(plan.priority_score))}")
        print(_c(_DIM, f"     Rationale : {plan.rationale}"))
        print()

        for line in outcome.transcript:
            if line.startswith("[agent"):
                print(_c(_CYAN,  f"     {line}"))
            elif line.startswith("[customer"):
                print(           f"     {line}")
            elif line.startswith("[system]"):
                print(_c(_DIM,   f"     {line}"))
            else:
                print(           f"     {line}")

        print()
        outcome_label = {
            "completed":   _c(_GREEN,  "✔  completed"),
            "declined":    _c(_YELLOW, "✘  declined"),
            "needs_human": _c(_ORANGE, "⚑  needs human"),
            "no_answer":   _c(_DIM,    "○  no answer"),
        }[outcome.outcome]
        print(f"     Outcome : {outcome_label}")

        if ticket:
            print(_c(_RED, f"     ↳ ESCALATED → human BC/RM  (reason: {ticket.reason})"))

        print(_c(_DIM, "  " + "─" * 62))
        print()

    # ── Summary ──────────────────────────────────────────────────────────────────
    print(_c(_BOLD, "  SUMMARY"))
    print(f"  {_c(_GREEN,  '✔  Completed')}    : {counts['completed']}")
    print(f"  {_c(_ORANGE, '⚑  Needs human')} : {counts['needs_human']}  ({escalations} escalated to BC/RM)")
    print(f"  {_c(_YELLOW, '✘  Declined')}     : {counts['declined']}")
    print(f"  {_c(_DIM,    '○  No answer')}    : {counts['no_answer']}")
    print()
    print(_c(_DIM, f"  Outcomes appended → data/outcomes.jsonl"))
    print()


def main() -> None:
    global _USE_COLOR
    parser = argparse.ArgumentParser(description="Saarthi reactivation pipeline (synthetic data demo).")
    parser.add_argument("--limit",    type=int, default=5,    help="Accounts to process (default: 5)")
    parser.add_argument("--seed",     type=int, default=None, help="Random seed for reproducible outcomes")
    parser.add_argument("--no-color", action="store_true",    help="Disable ANSI colour output")
    args = parser.parse_args()
    if args.no_color:
        _USE_COLOR = False
    run_pipeline(limit=args.limit, seed=args.seed)


if __name__ == "__main__":
    main()
