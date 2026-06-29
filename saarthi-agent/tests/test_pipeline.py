"""
Tests for the Saarthi agent pipeline.

Run:  pytest tests/ -v
"""

import json
from pathlib import Path

import pytest

from agent.reasoning_agent import plan_call, CallPlan, ACTIONS
from agent.voice_agent import run_call, CallOutcome, OUTCOMES
from agent.handoff_agent import maybe_escalate, REGULATED_ACTIONS
from agent.feedback_agent import compute_success_rates


# ── Fixtures ──────────────────────────────────────────────────────────────────

RUPAY_ACCOUNT = {
    "account_id": "TEST-0001",
    "state": "Uttar Pradesh",
    "preferred_language_hint": "Hindi",
    "dormancy_days": 900,
    "last_dbt_credit_unclaimed": True,
    "rupay_status": "issued_unused",
    "upi_status": "not_registered",
    "age_bracket": "31-45",
    "phone_reachable": True,
}

KYC_ACCOUNT = {
    **RUPAY_ACCOUNT,
    "account_id": "TEST-0002",
    "rupay_status": "none",
    "upi_status": "active",
}

UPI_ACCOUNT = {
    **RUPAY_ACCOUNT,
    "account_id": "TEST-0003",
    "rupay_status": "active",
    "upi_status": "not_registered",
}

UNREACHABLE_ACCOUNT = {
    **RUPAY_ACCOUNT,
    "account_id": "TEST-0004",
    "phone_reachable": False,
}

TAMIL_ACCOUNT = {
    **RUPAY_ACCOUNT,
    "account_id": "TEST-0005",
    "state": "Tamil Nadu",
    "preferred_language_hint": "Tamil",
}


# ── Reasoning agent tests ─────────────────────────────────────────────────────

def test_plan_returns_valid_dataclass():
    plan = plan_call(RUPAY_ACCOUNT)
    assert isinstance(plan, CallPlan)
    assert plan.account_id == "TEST-0001"
    assert plan.action in ACTIONS
    assert 0.0 <= plan.priority_score <= 1.0
    assert len(plan.opening_line) > 0
    assert len(plan.rationale) > 0


def test_rupay_unused_triggers_rupay_activation():
    plan = plan_call(RUPAY_ACCOUNT)
    assert plan.action == "rupay_activation"


def test_active_rupay_triggers_upi_setup():
    plan = plan_call(UPI_ACCOUNT)
    assert plan.action == "upi_setup"


def test_no_rupay_no_upi_triggers_re_kyc():
    plan = plan_call(KYC_ACCOUNT)
    assert plan.action == "re_kyc"


def test_unreachable_account_has_lower_priority():
    plan_reachable = plan_call(RUPAY_ACCOUNT)
    plan_unreachable = plan_call(UNREACHABLE_ACCOUNT)
    assert plan_unreachable.priority_score < plan_reachable.priority_score


def test_unclaimed_dbt_raises_priority():
    base = {**RUPAY_ACCOUNT, "last_dbt_credit_unclaimed": False}
    plan_no_dbt = plan_call(base)
    plan_dbt    = plan_call(RUPAY_ACCOUNT)
    assert plan_dbt.priority_score > plan_no_dbt.priority_score


def test_language_specific_opener_for_tamil():
    plan = plan_call(TAMIL_ACCOUNT)
    assert plan.language == "Tamil"
    assert "Namaste" not in plan.opening_line  # should NOT be the Hindi default


def test_language_specific_opener_for_hindi():
    plan = plan_call(RUPAY_ACCOUNT)
    assert "Namaste" in plan.opening_line or "bank" in plan.opening_line.lower()


def test_priority_score_in_range():
    for _ in range(10):
        plan = plan_call(RUPAY_ACCOUNT)
        assert 0.0 <= plan.priority_score <= 1.0


# ── Voice agent tests ─────────────────────────────────────────────────────────

def test_run_call_returns_valid_outcome():
    plan = plan_call(RUPAY_ACCOUNT)
    outcome = run_call(plan, seed=42)
    assert isinstance(outcome, CallOutcome)
    assert outcome.outcome in OUTCOMES
    assert len(outcome.transcript) >= 1
    assert outcome.account_id == plan.account_id


def test_run_call_reproducible_with_seed():
    plan = plan_call(RUPAY_ACCOUNT)
    assert run_call(plan, seed=7).outcome == run_call(plan, seed=7).outcome


def test_transcript_starts_with_agent_opener():
    plan = plan_call(RUPAY_ACCOUNT)
    outcome = run_call(plan, seed=42)
    assert outcome.transcript[0].startswith("[agent,")


def test_transcript_has_multiple_turns_on_completed():
    plan = plan_call(RUPAY_ACCOUNT)
    # Try seeds until we get a completed outcome
    for seed in range(50):
        outcome = run_call(plan, seed=seed)
        if outcome.outcome == "completed":
            assert len(outcome.transcript) > 2  # opener + at least 2 more turns
            return
    pytest.skip("No completed outcome found in 50 seeds — check weights")


# ── Handoff agent tests ───────────────────────────────────────────────────────

def test_re_kyc_always_escalates_regardless_of_outcome():
    """Hard compliance rule: re_kyc is always a regulated action."""
    forced_plan = CallPlan(
        account_id="TEST-REG", language="Hindi", action="re_kyc",
        priority_score=0.5, opening_line="test", rationale="test",
    )
    for seed in range(5):
        outcome = run_call(forced_plan, seed=seed)
        ticket = maybe_escalate(forced_plan, outcome)
        assert ticket is not None, f"re_kyc did not escalate on seed={seed}"
        assert ticket.reason == "regulated_action"


def test_needs_human_outcome_escalates():
    plan = CallPlan(
        account_id="TEST-NH", language="Hindi", action="rupay_activation",
        priority_score=0.5, opening_line="test", rationale="test",
    )
    outcome = CallOutcome(account_id="TEST-NH", action="rupay_activation",
                          outcome="needs_human", transcript=["[agent] ..."])
    ticket = maybe_escalate(plan, outcome)
    assert ticket is not None
    assert ticket.reason == "conversational_escalation"


def test_completed_non_regulated_does_not_escalate():
    plan = CallPlan(
        account_id="TEST-COMP", language="Hindi", action="rupay_activation",
        priority_score=0.5, opening_line="test", rationale="test",
    )
    outcome = CallOutcome(account_id="TEST-COMP", action="rupay_activation",
                          outcome="completed", transcript=["[system] done"])
    assert maybe_escalate(plan, outcome) is None


def test_declined_does_not_escalate():
    plan = CallPlan(
        account_id="TEST-DEC", language="Hindi", action="upi_setup",
        priority_score=0.5, opening_line="test", rationale="test",
    )
    outcome = CallOutcome(account_id="TEST-DEC", action="upi_setup",
                          outcome="declined", transcript=["[customer] no thanks"])
    assert maybe_escalate(plan, outcome) is None


# ── Feedback agent tests ──────────────────────────────────────────────────────

def test_success_rates_returns_empty_on_missing_file(tmp_path, monkeypatch):
    import agent.feedback_agent as fa
    monkeypatch.setattr(fa, "OUTCOMES_PATH", tmp_path / "missing.jsonl")
    assert compute_success_rates() == {}


def test_success_rates_computed_correctly(tmp_path, monkeypatch):
    import agent.feedback_agent as fa
    log_path = tmp_path / "outcomes.jsonl"
    monkeypatch.setattr(fa, "OUTCOMES_PATH", log_path)
    records = [
        {"account_id": "A", "language": "Hindi", "action": "rupay_activation", "priority_score": 0.8, "outcome": "completed"},
        {"account_id": "B", "language": "Hindi", "action": "rupay_activation", "priority_score": 0.7, "outcome": "completed"},
        {"account_id": "C", "language": "Hindi", "action": "rupay_activation", "priority_score": 0.6, "outcome": "declined"},
    ]
    with log_path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    rates = compute_success_rates()
    assert rates["Hindi:rupay_activation"] == pytest.approx(2 / 3)


# ── Data integrity test ───────────────────────────────────────────────────────

def test_mock_data_schema():
    """All accounts in mock_dormant_accounts.json must have required fields."""
    data_path = Path(__file__).resolve().parent.parent / "data" / "mock_dormant_accounts.json"
    required = {"account_id", "state", "preferred_language_hint", "dormancy_days",
                "rupay_status", "upi_status", "phone_reachable"}
    with data_path.open() as f:
        accounts = json.load(f)
    assert len(accounts) > 0
    for account in accounts:
        missing = required - account.keys()
        assert not missing, f"{account['account_id']} missing fields: {missing}"
