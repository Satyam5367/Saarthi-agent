# Architecture

## Pipeline

```
 ┌────────────────────────┐
 │ 1. Dormancy signal      │  Flags inactive accounts from sparse status signals
 │    & consent            │  (no transactions 2+ years, unclaimed DBT, unused RuPay card)
 └────────────┬─────────────┘
              │
 ┌────────────▼─────────────┐
 │ 2. Reasoning agent       │  Picks: language, channel, single best action, priority score
 └────────────┬─────────────┘
              │
 ┌────────────▼─────────────┐
 │ 3. Voice agent           │  Vernacular ASR → LLM → TTS conversation (stubbed in this repo)
 └────────────┬─────────────┘
              │
 ┌────────────▼─────────────┐
 │ 4. Handoff agent         │  Escalates to a human BC/RM if regulated, confused, or declined
 └────────────┬─────────────┘
              │
 ┌────────────▼─────────────┐
 │ 5. Feedback agent        │  Logs outcome, reprioritizes future targeting
 └───────────────────────────┘

 (Steps 1–5 all run inside a compliance wrapper: consent logging, audit trail,
  and human-escalation gates for any regulated decision.)
```

## Why this is "agentic" and not a scripted IVR

A scripted IVR has a fixed call list, one menu for everyone, a region-coded language, and a
keypress-based escalation rule that never improves. Saarthi's pipeline makes each of those a
live decision:

| Decision point | Scripted IVR | Saarthi |
|---|---|---|
| Who gets called | Static list | Continuously re-prioritized from live signal data |
| What's offered | One fixed menu | Per-customer choice (RuPay activation / UPI setup / re-KYC) |
| Which language | Pre-set by region code | Inferred and adapted per customer profile |
| When to escalate | Fixed keypress rule | Recognized mid-conversation from context |
| How it improves | Doesn't | Feedback agent reprioritizes from real outcomes |

## Compliance notes

- **TRAI**: outbound calling must respect the national Do-Not-Disturb registry and capture
  explicit consent before any call. This repo logs a `consent` field per record as a placeholder
  for that check — a production build would call the actual DND registry API first.
- **RBI**: any action that changes account/KYC status must route to a human RM. The
  `handoff_agent` enforces this as a hard rule, not a model judgment call — see
  `REGULATED_ACTIONS` in `agent/handoff_agent.py`.

## Data model

See `data/mock_dormant_accounts.json` for the synthetic input schema. Each record represents one
dormant account with the sparse signals the reasoning agent uses to decide the call plan.

## Extending this scaffold

- Swap `agent/voice_agent.py`'s simulated conversation for a real ASR/TTS integration
  (e.g. AI4Bharat/Bhashini) behind the same function signature — `pipeline.py` doesn't need to
  change.
- Swap the synthetic `data/mock_dormant_accounts.json` for a real consented data feed
  (Account Aggregator / core banking export) behind the same record schema.
- `agent/feedback_agent.py`'s reprioritization is currently a simple heuristic
  (success-rate by language+action cluster) — replace with a proper online-learning loop
  for production use.
