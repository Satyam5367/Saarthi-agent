<div align="center">

# 📞 Saarthi
### Voice-First Agentic AI for Dormant Account Reactivation

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E?style=flat)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-20%20passing-22C55E?style=flat)](tests/)
[![Hackathon](https://img.shields.io/badge/SBI%20AI%20Hackathon-GFF%202026-0B4F4A?style=flat)](https://gff.in)
[![Theme](https://img.shields.io/badge/Theme-Digital%20Adoption-D9791E?style=flat)]()

> *Saarthi (सारथी) — "charioteer/guide" in Sanskrit. An AI that steers dormant account holders back into the banking system, in their own language.*

**Built for the SBI AI Online Hackathon @ Global Fintech Fest 2026**

</div>

---

## 🎯 The Problem

SBI's share of inoperative Jan Dhan accounts rose from **19% → 25% in a single year** (Sept 2024 to Sept 2025).
That's roughly **~143 million dormant PMJDY accounts** across public-sector banks system-wide — customers who are
banked on paper but unbanked in practice.

**The gap isn't discovery. It's reach.**

Existing AI engagement tools — in-app push, SMS, WhatsApp, chatbots — all assume a literate, smartphone-using,
app-engaged customer. The customers behind the dormancy number are:

| Who they are | Why existing tools miss them |
|---|---|
| 🗺️ Rural & semi-urban (UP, Bihar, West Bengal) | No consistent app access |
| 📵 Feature phone or shared device users | Can't receive in-app push |
| 📚 Low literacy | Text-based nudges go unread |

**They are reachable — by voice, in their own language.**

---

## 💡 The Solution

**Saarthi** is a five-step autonomous voice agent that:

```
Finds who needs it  →  Reasons in context  →  Calls & converses  →  Knows when to stop  →  Learns from outcomes
```

1. **Flags** dormant accounts from sparse signals (no transactions 2+ yrs, unclaimed DBT, unused RuPay card)
2. **Decides** per customer — which language, which single best action, highest-priority accounts first
3. **Places** an outbound vernacular voice call (ASR → LLM → TTS) to walk through one concrete step
4. **Escalates** to a human BC/RM the moment a case needs judgment, KYC, or goes beyond the agent's scope
5. **Logs** the outcome and retrains future targeting from real conversion data

**Launch languages:** Hindi · Bengali · Telugu · Tamil · Marathi — expandable to all 22 scheduled languages via Bhashini

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRAI & RBI Compliance Wrapper                            │
│         (consent logging · audit trail · human escalation gates)            │
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌─────────────┐ │
│  │  Reasoning   │──▶│    Voice     │──▶│   Handoff    │──▶│  Feedback   │ │
│  │    Agent     │   │    Agent     │   │    Agent     │   │    Agent    │ │
│  │              │   │              │   │              │   │             │ │
│  │ Picks lang · │   │ Vernacular   │   │ Escalates to │   │ Logs outcome│ │
│  │ action ·     │   │ ASR→LLM→TTS │   │ BC/RM with   │   │ Retrains   │ │
│  │ priority     │   │ conversation │   │ full context │   │ targeting  │ │
│  └──────────────┘   └──────────────┘   └──────────────┘   └─────────────┘ │
│         ▲                                                                   │
│  ┌──────┴───────┐                                                           │
│  │ Dormancy     │  (outside wrapper — consent captured before reasoning)    │
│  │ Signal Layer │                                                           │
│  └──────────────┘                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

The reasoning layer is **model-agnostic by design** — the reference implementation uses an LLM API
but the `plan_call()` interface is a single swappable function. Any provider (Azure OpenAI,
Sarvam AI, Krutrim, or any enterprise LLM SBI standardizes on) can be dropped in without touching
the rest of the pipeline.

---

## 📁 Repo Structure

```
saarthi-agent/
│
├── agent/
│   ├── pipeline.py           # orchestrates all five steps end-to-end
│   ├── reasoning_agent.py    # decides: language, action, priority score
│   ├── voice_agent.py        # vernacular conversation (ASR/LLM/TTS stand-in)
│   ├── handoff_agent.py      # escalation logic + structured ticket generation
│   └── feedback_agent.py     # outcome logging + targeting reprioritization
│
├── data/
│   ├── mock_dormant_accounts.json   # 8 synthetic dormant accounts across 5 states
│   └── outcomes.jsonl               # written at runtime by feedback_agent
│
├── docs/
│   └── ARCHITECTURE.md       # full pipeline breakdown + compliance mapping
│
├── tests/
│   └── test_pipeline.py      # 7 tests covering all five agents
│
├── requirements.txt
├── .env.example
└── LICENSE
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/saarthi-agent.git
cd saarthi-agent
pip install -r requirements.txt
```

**Run the demo (no API key needed):**
```bash
python -m agent.pipeline --limit 8 --seed 7
```

Or just use Make:
```bash
make demo    # run the demo  (same as: python -m agent.pipeline --limit 8 --seed 7)
make test    # run all 20 tests
make clean   # remove generated files
```

The pipeline loads dormant accounts, **sorts them by priority score**, and runs each
through the full five-step flow — printing the language-appropriate opener, the full
multi-turn conversation, outcome, and whether it escalated to a human BC/RM.

See [demo_output.txt](demo_output.txt) for a complete pre-captured run — no setup needed to read it.

**Run tests:**
```bash
pytest tests/ -v
```
All 7 tests pass with zero setup.

---

## ⚙️ Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Default | Effect |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(empty)* | If set, uses a live LLM for call-plan decisions. If unset, the pipeline uses a deterministic rule-based fallback — full demo still works. |

> **To swap the LLM provider:** replace `_llm_plan()` in `agent/reasoning_agent.py` with your preferred API call. The `plan_call()` interface is the only thing the rest of the pipeline depends on.

---

## 📊 KPIs (tracked from Phase 1 pilot onward)

| Metric | Definition |
|---|---|
| **Dormancy Reactivation Rate** | % of contacted accounts that complete any action on the call |
| **UPI Activation Rate** | % of reactivated accounts that go on to register for UPI |
| **RuPay Activation Rate** | % of issued-but-unused RuPay cards activated through the call |
| **Cost per Reactivated Customer** | Pipeline cost ÷ accounts reactivated, vs. branch/BC outreach cost |

> **Illustrative scale:** against ~143M dormant PMJDY accounts system-wide, a 2% reactivation rate is ~2.9M accounts back in active digital use. Actual conversion rates to be established through the Phase 1 pilot.

---

## 🗺️ Roadmap

| Phase | Focus | Scope |
|---|---|---|
| **Phase 1** | Prove the wedge | RuPay/UPI activation calls · one state · one language |
| **Phase 2** | Expand journeys | Agri-loan EMI reminders · MSME onboarding · NRI servicing |
| **Phase 3** | Platform | License vernacular voice-agent infra to RRBs and smaller PSBs |

---

## 🔒 Compliance

- **TRAI:** explicit recorded consent at call start; DND-registry check before any outbound call
- **RBI KYC:** `re_kyc` is a hard-coded regulated action — the handoff agent *always* routes it to a human RM, never resolved autonomously
- **Audit trail:** every call plan, conversation, and outcome is logged to `data/outcomes.jsonl`

---

## 🧱 What's Real vs. Stubbed

| Component | This scaffold | Production |
|---|---|---|
| Reasoning agent | ✅ Real (rule-based fallback + LLM option) | Same, richer context from core banking |
| Voice agent | 🔁 Stubbed (text simulation of ASR→LLM→TTS) | AI4Bharat / Bhashini + Exotel/Knowlarity |
| Handoff agent | ✅ Real (escalation logic + ticket) | Wired into BC/RM ticketing system |
| Feedback agent | ✅ Real (outcome log + reprioritization) | Full online-learning loop |
| Dormancy data | 🔁 Synthetic (8 accounts, 5 states) | Consented Account Aggregator / core banking feed |
| Consent capture | 🔁 Simulated (field on call record) | Real recorded consent + TRAI DND check |

---

## 👤 Author

**Solo submission** — SBI AI Online Hackathon @ GFF 2026 · Theme: Digital Adoption

---

## 📄 License

[MIT](LICENSE)
