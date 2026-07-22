---
id: RESEARCH_REQUEST_team_00_TO_team_110_CURSOR_CLOUD_CAPABILITIES_2026-07-22_v1.0.0
type: RESEARCH_REQUEST
from_team: team_00
to_team: team_110 (builder / build-phase)
orchestration_context: team_100 (P002 build handoff)
date: 2026-07-22
subject: "Verify Cursor Cloud environment requirements & capabilities BEFORE scheduling the P002 build"
next_step: "team_110 runs the §1 prompt inside a Cursor Cloud session, returns the §2 capabilities report; team_00/team_100 then decide build-vs-runtime placement and unblock the P002 build."
context_pointer:
  - _aos/work_packages/FNL-S001-P002-WP001..WP007/LOD400_spec.md   # @ origin/main ef0e366
  - _aos/work_packages/FNL-S001-P001-WP001/LOD200.md
  - _COMMUNICATION/team_100/HANDOFF_team_100_2026-07-22_RECOVERY_AND_P002_LOD400_BATCH_TO_BUILD_v1.0.0.md
  - memory: family-newsletter-engine-env-canon (build=Grok/cursor-agent on Mac; runtime=sonnet-5; shared waldhomeserver; Tailscale server 100.125.98.56)
---

# Research Request — Cursor Cloud: requirements & capabilities (pre-P002-build)

## 0. Why this exists (for team_00 / team_100 — not part of the paste)

We are about to schedule the **P002 build** (7 WPs, a Python pipeline: `llm.py`,
`token_tracker`, `researcher.py`, `editor.py`, `teaser.py`, orchestrator+`publisher.py`,
template extension) via **Cursor Cloud scheduled sessions**, building from
`origin/main @ ef0e366`. Before we commit the build path, we must confirm what
Cursor Cloud can and cannot do — because several **build-blockers already found in
validation are environment-dependent**:
- `pytest` + `pytest-mock` are **not installed** in the repo venv, yet every code WP's ACs need them.
- Two token_tracker defects (`pause_turn` accumulation; a possibly-fabricated `allowed_callers` API field) can only be settled by a **live Anthropic API smoke test**.
- `teaser.py` needs **Pillow + libraqm** for correct Hebrew RTL shaping.
- Runtime edition-1 needs the Anthropic API + **uPress FTP** + **WhatsApp/WAHA on waldhomeserver (Tailscale)** — some of which a cloud env may not reach.

The §1 block below is **self-contained** — Nimrod routes it into a Cursor Cloud
session; that session probes its own environment empirically + consults Cursor's
docs, and returns the §2 report.

---

## 1. THE PROMPT — paste this into a Cursor Cloud session

> **Role.** You are **team_110 (builder)** for the *Family Newsletter* project (an AOS L0 spoke; repo `git@github.com:WaldNimrod/family-newsletter.git`, build from `origin/main @ ef0e366`). We are evaluating whether to run this project's build — and possibly its weekly runtime — inside **Cursor Cloud scheduled sessions**. Before we commit, we need a **verified capabilities report** of THIS environment.
>
> **What we will build here (context).** A Python 3 pipeline of 7 work packages (LOD400 specs at `_aos/work_packages/FNL-S001-P002-WP00{1..7}/LOD400_spec.md`): a dual-driver LLM layer, a token/cost tracker, a researcher, an editor, a Pillow teaser-image generator with **Hebrew RTL**, an orchestrator + FTP/email publisher, and a Jinja2 template. Runtime model = **claude-sonnet-5** via the Anthropic API. Build engine = **Grok via `cursor-agent`**. Cross-engine rule: Grok builds → Claude validates.
>
> **Your task.** Answer EVERY question in the checklist below. **Verify empirically** — run real commands in this session and paste the exact command + its output; do **not** guess. Where a fact comes from Cursor's documentation rather than a command, say so and link it. Tag each answer: `[VERIFIED: <cmd>]`, `[DOCS: <url>]`, or `[UNKNOWN]`. Finish with an overall verdict.
>
> ### Checklist
>
> **A. Runtime & packages**
> A1. OS, arch, and Python version(s) available (`uname -a`, `python3 --version`). Is `pip` present? Can you create and use a `venv`?
> A2. Can you `pip install` arbitrary PyPI packages? Install-test these and report success/failure: `pytest`, `pytest-mock`, `Pillow`, `feedparser`, `requests`, `jinja2`, `anthropic`, `python-bidi`. Any allowlist/blocklist, proxy, or offline restriction?
> A3. **Hebrew RTL:** does Pillow have **libraqm**? Run `python3 -c "from PIL import features; print('raqm', features.check('raqm'))"`. If False, can libraqm be installed (system pkg)? Is `python-bidi` an acceptable fallback here?
> A4. Pre-installed tooling: `git`, `node`, compilers/build tools? Versions.
>
> **B. Git / repo integration**
> B1. How does a session obtain the repo — does it clone `origin/main` from GitHub? What auth (GitHub App / deploy key / PAT)? Confirm you can `git clone` / see `ef0e366`.
> B2. Can a session **commit and push**, and **open a PR**? What branch model is expected (build on a branch → PR → merge to main)?
> B3. If several scheduled sessions run, how is **concurrent-write collision** avoided? (We have already lost uncommitted work to a parallel session's commit — this is a hard requirement.)
>
> **C. Build engine (Grok / cursor-agent)**
> C1. Is the **`cursor-agent` / Grok** builder available here? Which model ids (is `grok-4` valid)? Run whatever reveals the available agent/models.
> C2. Can it run **headless / non-interactive** (the Mac uses `cursor-agent -f`)? Show the invocation.
> C3. Can a single session run **both** a Grok build **and** a **Claude (Anthropic API) validation** pass (cross-engine), or do we need two linked sessions?
>
> **D. Secrets / env vars**
> D1. How do you supply **secrets** to a session — encrypted env vars, a secrets manager, `.env`? Which of these are available to **unattended scheduled** runs (no human present)?
> D2. Confirm whether an `ANTHROPIC_API_KEY` (and later: uPress FTP creds, WAHA token, `AOS_API_BASE`/`AOS_ACTOR_API_KEY`) can be injected securely.
>
> **E. Network / external reachability** (test each with a real request)
> E1. Can you reach **`api.anthropic.com`**? (Needed for live-API smoke tests + runtime.)
> E2. Can you reach the public internet for **web_search / web_fetch** and general HTTP?
> E3. Can you reach **uPress FTP** (host under `nimrod.bio`) for the teaser upload test?
> E4. Can you reach a **Tailscale** network or the AOS v5 server at `100.125.98.56:8092`, and **waldhomeserver / WAHA**? (Expected: NO from a cloud env — please confirm, because it decides whether WhatsApp send + AOS messaging can run here.)
>
> **F. Scheduling**
> F1. How are **scheduled sessions** configured (cadence/cron, triggers)? Show the config surface.
> F2. Concurrency limits? Can sessions **chain** (build WP001 → WP002 → …) and **report results** to a known sink (PR, a committed file, a webhook)?
> F3. **Max session duration** and **resource limits** (RAM/CPU/disk)? (WP006 is ~1600 spec lines / 107 ACs — a long build+test cycle.)
>
> **G. Build vs. runtime placement** (the key architectural question)
> G1. Is Cursor Cloud intended for **BUILD only**, or can it also host the **weekly RUNTIME** (Friday: sonnet-5 generation → teaser.png → FTP upload → WhatsApp send)? Given E4, runtime-in-cloud may be blocked for WhatsApp/AOS — state clearly what runtime steps CAN and CANNOT run here.
>
> ### Output format
> A single structured report: one section per group A–G, every answer tagged `[VERIFIED]`/`[DOCS]`/`[UNKNOWN]` with the command+output or doc link. End with:
> - **BUILD verdict:** GO / GO-WITH-CONSTRAINTS / NO-GO for running the P002 build in Cursor Cloud (list any constraints, e.g. "pytest installable ✅ but no Tailscale ❌").
> - **RUNTIME verdict:** can the weekly edition run here, fully or partially? What must stay on waldhomeserver?
> - **Top 3 blockers/risks** for our specific pipeline.

---

## 2. Why each group matters (for team_00 / team_100 — not part of the paste)

| Group | Ties to our build |
|---|---|
| A2/A3 | Validators flagged `pytest`/`pytest-mock` missing + `Pillow+libraqm` for RTL — if uninstallable here, the AC-based build model breaks. |
| B3 | We already lost work to a parallel-session clobber; unattended scheduled builds must not repeat it. |
| C | Confirms the Grok build engine + cross-engine validation actually run in-cloud (Mac path was verified; cloud is unconfirmed). |
| D/E1 | Live-API smoke tests are the ONLY way to settle the two token_tracker build-blockers (pause_turn accumulation; `allowed_callers`) and the cost-cap accuracy. |
| E4 | Decides whether WhatsApp send (WAHA on Tailscale) + AOS messaging can live in-cloud — likely NOT → runtime split. |
| G | The architectural fork: baseline is **build in Cursor Cloud, runtime on waldhomeserver cron** — this research confirms or revises it. |

## 3. Sequencing note
This is **parallel to** the 7-spec validation already in flight (does not block it).
Order: validation + this Cursor-Cloud research complete → team_00/team_100 fix the
spec defects + decide build/runtime placement → schedule the Cursor Grok build.
