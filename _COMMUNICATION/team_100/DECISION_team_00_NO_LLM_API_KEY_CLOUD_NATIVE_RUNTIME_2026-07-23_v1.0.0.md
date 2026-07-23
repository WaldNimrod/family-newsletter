---
id: DECISION_team_00_NO_LLM_API_KEY_CLOUD_NATIVE_RUNTIME_2026-07-23_v1.0.0
type: DECISION (standing architecture ruling — team_00, 2026-07-23)
from_team: team_00
to_team: team_100 (specs/plans) + team_110 (build/runtime)
subject: "NEVER a provisioned LLM API key. All LLM work = Cursor Cloud agent-native models. Runtime = Cloud routines + manual editor gate."
status: LOCKED
---

# DECISION — No LLM API key, ever. Cloud-native runtime.

## 1. The ruling (locked)
The system **NEVER requires a provisioned LLM-provider API key** (no `ANTHROPIC_API_KEY`,
no raw provider key). **All LLM work uses Cursor Cloud's native agent model access**
(Claude/Grok via the Cursor agent platform — the same access that built & validated the
pipeline, with no `api.anthropic.com`). **Runtime = a Cursor Cloud scheduled routine/agent**,
triggered by cron **and/or the mandatory weekly manual editor gate (Nimrod + Tzlil)**.

**Why:** no key to provision/secure/rotate; Cursor Cloud blocks `api.anthropic.com` anyway;
no edition time-pressure; the manual editor gate is a natural trigger; uses what we already
have. Cost becomes **flat (Cursor subscription)**, not per-token — simpler + aligned with the
"flat-cost engine" principle.

## 2. Implications — examined across every spec/plan
| Component | Built for (API) | Under this ruling | Adaptation |
|---|---|---|---|
| **WP001 `llm.py`** | anthropic HTTP driver (default) + cursor-agent driver | anthropic driver **unused at runtime** (no key + Cloud-blocked); cursor-agent binary **absent** in Cloud VM too | Runtime LLM = **agent performs the steps**; `llm.py` HTTP drivers become **build/test-only** (mock path stays for pytest). Define an "agent-native" LLM path. |
| **WP002 `token_tracker`** | per-token **Anthropic billing** + `research()` server-tools (web_search via Anthropic); sonnet-5 pricing; **$2.50/wk cap** | **No per-token cost** under Cursor-native → the cost table + $2.50/wk cap are **moot/reframed**; server web_search → **agent-native web tools** | **Reframe LOD200 §6:** cap by *agent-runs/week* (or drop $-cap); the 2026-08-31 sonnet-5 pricing deadline is **no longer relevant**. web_search → agent-native (verify). |
| **WP003 `researcher`** | `token_tracker.research()` (Anthropic + web_search) | research done by the **agent's native model + native web** | The runtime **agent** performs research; code supplies scaffolding/prompts + deterministic dedup/scoring. |
| **WP004 `editor`** | `llm.complete()` (Anthropic) | editing done by the **agent's native model** | Agent performs editorial; the manual editor gate (Tzlil) reviews. |
| **WP006 `orchestrator`** | `llm.configure()` + calls llm/editor/researcher | **agent orchestrates** the LLM steps; code runs the deterministic steps | Define the **agent runtime harness**: agent does LLM parts, calls code for scan/dedup/score/**render/teaser/publish artifacts**. |
| **Runtime / deploy (P003)** | server cron runs `orchestrator.py` (needs key) | **Cloud agent generates** (no key). **Publishing (FTP + WhatsApp + AOS) still cannot run in Cloud** (egress blocked, E3/E4) | **SPLIT runtime:** Cloud agent generates HTML+teaser → artifacts land on origin → **waldhomeserver (or a manual step) publishes** (FTP/WhatsApp). |
| **LOD200 §6 cost_cap + engine-env memory** | Anthropic $/token, sonnet-5 deadline | **subscription/flat** | Update the contract + memory. |

## 3. What does NOT change
The **entire deterministic pipeline** — scanning, dedup, scoring, Hebrew-date/weather,
`render()`, `teaser.py`, the template (13 sections + placeholders), and the publish
*mechanics* — is built, tested (382 green), and **stays as-is on `main`**. Only the
**LLM-access mechanism** changes (API-call → agent-native), plus the cost model.

## 4. Open items to verify BEFORE finalizing the agent runtime (→ Cursor research session)
1. Does the Cloud agent have **working web_search/web_fetch** (VM shell egress was unreliable; Cursor's native agent tools may proxy)? — researcher depends on it.
2. Can the agent reliably perform the **structured research/edit steps** (stable JSON out) at edition quality?
3. The **Cloud→publish handoff**: how do the generated HTML+teaser get from the Cloud agent to FTP/WhatsApp (server pull? artifact + manual publish?).

## 5. Adaptation plan (sequenced)
- **Now (done):** this ruling documented; goal #1 pipeline on `main` unaffected (it's the deterministic core + a mockable LLM layer).
- **team_100:** update LOD200 §6 (cost model → flat) + the WP001–004/006 LLM-access assumptions in the specs (I can't edit `_aos/`; routing this to team_100).
- **New WP (P003 runtime):** design the **agent runtime harness** (Cloud routine: agent LLM steps + code deterministic steps → artifacts → server/manual publish) — depends on §4 answers.
- **Memory:** update engine-env canon (build=Grok/Cursor; **runtime=Cloud-native agent, NO API key**; cost=subscription/flat; sonnet-5 pricing deadline retired).

## 6. Net effect
Edition #1's **infrastructure and preview are unaffected** (deterministic + mock). This ruling
reshapes **how real weekly content is generated at runtime** (agent-native, no key) and
**where publishing runs** (server/manual) — a P003 concern, not a blocker for the render/preview now.
