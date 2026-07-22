---
id: HANDOFF_team_100_2026-07-22_RECOVERY_AND_P002_LOD400_BATCH_TO_BUILD_v1.0.0
type: HANDOFF
from_team: team_100
to_team: team_100 (build/completion) + team_00 (validation)
date: 2026-07-22
status: P002 LOD400 spec batch COMPLETE (authored + pushed); awaiting team_00 batch validation + build
head_commit: ef0e366 (origin/main — build FROM here; do NOT rely on this session's local working tree)
next_step: "team_00 validates the 7-spec batch + rules on 2 open items; then Grok/Cursor builds WP001->WP006(+WP007) in dependency order, Claude validates each build (cross-engine)."
context_pointer:
  - _aos/roadmap.yaml
  - _aos/work_packages/FNL-S001-P002-WP001..WP007/LOD400_spec.md
  - _aos/work_packages/FNL-S001-P001-WP001/LOD200.md
  - archive/design-april-2026/DESIGN_FISH_2026-07-22.md
  - data/profile-raw/TRANSCRIPT_MINING_2026-07-22.md  (gitignored — local only, sensitive)
  - memory: family-newsletter-engine-env-canon, family-newsletter-revival, family-governance-rules
---

# Handoff — 2026-07-22 session → team_100 (build) + team_00 (validation)

Full account of what was **executed**, what was **discovered**, and what remains **for completion**. This session ran as team_100 (architect/spec author). Per the standing operating note (memory `family-governance-rules`): a Claude session here writes `_COMMUNICATION/` reliably; `_aos/`+`src/` working-tree edits may auto-revert locally — **but everything below was committed and pushed to `origin/main` (head `ef0e366`), so it is durable on GitHub. Build from origin, not from a local working tree.**

---

## 0. TL;DR
- **Cutover verified**, and a **critical memory/context loss from the folder move was found and fully recovered** (root cause: dash-vs-underscore Claude-Code slug mismatch + a copy-not-move that left an old container behind). Nothing in the repo/`data/`/`.env` was lost.
- **Deep-mined** the recovered session transcripts + April design archive → persisted precise intelligence (family content, engine/env canon, visual identity "fish").
- **Roadmap synced** (WP002/WP003 → COMPLETE) and project docs committed/pushed.
- **P002 pipeline: all 7 LOD400 build specs authored** (cross-engine batch, ~7,300 lines / ~470 ACs), roadmap updated, WP007 registered, pushed at `ef0e366`.
- **2 open reconciliation items** flagged for team_00 (below). **1 governance violation** by a subagent caught + reverted.

---

## 1. EXECUTED

### 1.1 Cutover verification (all green)
- `git remote` = `git@github.com:WaldNimrod/family-newsletter.git` ✅
- `.cursorrules` → new path `/AOS_V5/family-newsletter` ✅
- `git grep famely` → only an **intentional comment** in `_aos/project_identity.yaml` (why "famely" is deliberately kept out of `forbidden_patterns`) ✅; `neuslettr` clean ✅
- Project **memory was cold** (empty at the live slug) — triggered the recovery below.

### 1.2 Memory / settings / context RECOVERY (major)
**Root cause:** the cutover was a **copy-not-move**. (a) Claude-Code memory was copied to slug `-...-AOS_V5-...` (underscore) but the live session reads `-...-AOS-V5-...` (dash, `_`→`-` normalization) → empty. (b) The old container `~/Documents/Famely Neuslettr/` was left on disk with `.claude/settings.local.json` + April design artifacts.
**Recovered (verified, non-destructive — all backup sources kept intact):**
- **Memory** → 4 files copied to the dash slug + indexed; now 5 memories incl. new `cutover-memory-slug-dash-not-underscore` + `family-newsletter-engine-env-canon`.
- **Session transcripts** (3 `.jsonl`, ~8 MB) → copied to the live slug (history/resume preserved).
- **Settings** → recovered `.claude/settings.local.json` (21 still-valid grants; stale old-path one-offs dropped, listed in-session).
- **April design artifacts** (19 files) → `archive/design-april-2026/` (committed `165acce`).
**Verified NOT lost:** every repo file present via git history (0 missing vs the `famely-neuslettr.bak-20260722` snapshot); `data/` (135 files / 60 MB) + `.env` byte-identical.
- **Deferred cleanup** registered as `FNL-S001-P001-WP004` + a **scheduled task fires 2026-08-22** to verify-then-delete the redundant leftovers (only with Nimrod's OK).
- **Memory-file rename** `famely-*`→`family-*` done **cross-engine** (Composer/cursor-agent executed → Sonnet validated PASS) — this also **smoke-tested the Mac build path** the whole of P002 depends on (`cursor-agent` works headless on the Mac with `-f`).

### 1.3 Deep mining → precise persisted intelligence
- **Transcripts** → `data/profile-raw/TRANSCRIPT_MINING_2026-07-22.md` (**gitignored — sensitive**; per-member content, extended-family Dreyfus branch, engine/env facts, open threads).
- **April archive** → `archive/design-april-2026/DESIGN_FISH_2026-07-22.md` (committed `64a22b0`; visual identity + the SVG mascot system).
- **Memory canon** → `family-newsletter-engine-env-canon`.

### 1.4 Roadmap sync + project docs (pushed)
- WP002 (env fix) + WP003 (archive poc.py) → **COMPLETE** (WP003 honestly marked partial: m2/m3/m6+sources.json archive DEFERRED to WP006). Commits `9ea11a5`, `3d74e39`, `165acce`, `d1b1330`, `64a22b0` — all pushed.

### 1.5 P002 — seven LOD400 build specs (pushed `ef0e366`)
Authored as a **cross-engine batch**: team_100 orchestrated, **Sonnet subagents drafted** each spec (per the "delegate grunt work to Sonnet" standing directive), on the canonical `document-lifecycle/templates/LOD400_SPEC_TEMPLATE.md` skeleton. Grok/Cursor builds next; Claude validates (Iron Rule #1).

| WP | Module | Lines | ACs | spec_ref |
|---|---|---|---|---|
| FNL-S001-P002-WP001 | `src/llm.py` dual-driver (anthropic default, cursor fast-follow) | 725 | 52 | `_aos/work_packages/FNL-S001-P002-WP001/LOD400_spec.md` |
| FNL-S001-P002-WP002 | `src/token_tracker.py` (sonnet-5, `research()`, date-gated pricing) | 571 | 58 | .../WP002/ |
| FNL-S001-P002-WP003 | `src/researcher.py` (5× two-step + screen-scout + `watchlist` DDL) | 1455 | 97 | .../WP003/ |
| FNL-S001-P002-WP004 | `src/editor.py` (1 editorial call, `--mock`, voices, guardrails) | 939 | 51 | .../WP004/ |
| FNL-S001-P002-WP005 | `src/teaser.py` (Pillow 1080×1350, RTL bidi, mascot assets) | 1084 | 59 | .../WP005/ |
| FNL-S001-P002-WP006 | orchestrator rewire + `src/publisher.py` (FTP+email, Twilio out) | 1609 | 107 | .../WP006/ |
| FNL-S001-P002-WP007 | template extension (5 corners + 3 sections + ALL fish) | 932 | 89 | .../WP007/ |

roadmap: P002 WP001–006 → `L-GATE_SPEC / LOD400 / IN_PROGRESS`; **WP007 newly registered**; DESIGN_FISH "incorporate all fish" decision locked (Nimrod ruling "כל אחד דג שווה").

---

## 2. DISCOVERED (feeds build + validation)

### 2.1 Engine / env canon (memory `family-newsletter-engine-env-canon`)
- **BUILD** = Grok via `cursor-agent` on the **Mac** (verified working, needs `-f`). **RUNTIME edition-1** = Claude **sonnet-5** proven default; cursor-on-server is fast-follow (no Grok API key on the server yet). → `llm.py` `ai.provider` default = **anthropic**, not cursor.
- 🔴 **Sonnet-5 intro pricing $2/$10 per MTok ONLY through 2026-08-31, then $3/$15** (~doubles cost). `temperature` → **HTTP 400** (never send). Extended thinking **on+billed by default**. Tokenizer **~30% more tokens** than 4.6. web_search tool = `web_search_20260209` ($10/1k). → all baked into WP002.
- Server `waldhomeserver` is **SHARED**: SmallFarmsAgents + TikTrack crons; the newsletter's **09:00 Friday build collides in time with the 09:00 SFA cleanup**. Existing cron still points at the archived `/data/projects/famely-neusletter/run.sh` (silent no-op) → deploy = restore to `/data/projects/family-newsletter` + **update (not add)** the cron path. WAHA needs **reboot-persistence** + a memory limit (RAM tight).

### 2.2 Design "fish" (`archive/design-april-2026/DESIGN_FISH_2026-07-22.md`)
- A designed-but-never-built **SVG "Skipper Cat" mascot system**: monthly-rotating hero + 4 semantic poses + per-category costuming + 5-member character briefs in `SVG_MODULE_SPEC.md` (repo root) + a topic→scene→character lookup table → feeds `teaser.py` + template hero.
- **Lost fish revived (Nimrod: all in):** dark mode, "מהמדף שלנו/From Our Shelf" section, inline emoji rating, single-wide L2 panel, YouTube thumbnails. Chosen visual baseline = `newsletter-v3-preview.html` (byte-identical to current template). Comic palette: Bangers+Patrick Hand, `#fdf6e3`/`#2c2c2c`, per-member hex.

### 2.3 Content-substrate intelligence (`TRANSCRIPT_MINING`, gitignored)
- Net-new per-member facts (birthdates, schools, ABADÁ capoeira, geodesic-dome↔aerial-silks Michal↔Yoyo bridge, Shabazi clowning course, gifted-math sources, etc.).
- **Sensitivities marked NEVER-FOR-NEWSLETTER** (the WHY behind editorial rules: Michal restorative/zero-load; Shaked gender via spec-fic only; a March-2026 evacuation; extended-family Dreyfus register). Editor persona = **Tzlil**, but her real participation is **hoped-for** ("אני מקווה"), with open tooling/comms questions.

### 2.4 Spec-surfaced engineering findings
- **Puzzle-answer bug** (old pipeline showed *this* week's secret answer under a "last week's answer" label) — WP006 makes it structurally un-swappable (AC-55/AC-69).
- `llm.configure()` wiring gap (every module assumed it, none called it) — WP006 wires it.
- 3 missing adapters invented in WP006 (`_map_viewing`, `_map_discovery_bridges`, `_short_greeting`).
- WP006 archives `m5_distributor.py` itself (5th file) after salvaging `_fetch_weather`/`_format_hebrew_date`/`_build_neo`.
- teaser: **Rubik/Secular One for Hebrew** (Bangers/Patrick Hand have zero Hebrew glyphs); raqm-detect + python-bidi fallback baseline.

---

## 3. OPEN ITEMS — for team_100 / team_00 to complete ("ההשלמה")

- [ ] **team_00 validates the 7-spec batch** (produce-then-validate model; each spec has a §1 assumptions block for you to strike/confirm).
- [ ] 🔴 **CONTENT-OWNERSHIP GAP (highest priority).** WP003 and WP004 **mutually deferred** the **"🍽️ שולחן שישי / Family-Table"** and **"👨‍👩‍👧 מהמשפחה המורחבת / Extended-Family"** content — **neither module produces it**, yet LOD200 §3 requires all 13 sections. WP006 wired safe empty-defaults + flagged this. Recommended fix: extend `editor.py` with a `family_table` field sourced from `profiles/family.md` "active threads" (zero LLM cost); a small zero-LLM `researcher.py` curation from `profiles/extended-family.md` — **but that file has no ready-to-publish safe headline yet → this is a CONTENT-track gap, needs Nimrod input, not just code.**
- [ ] 🔴 **Mascot credit-line: activate vs retire.** Template reads `neo.metadata['character_*']` which nothing populates → always falls back to hardcoded "Cat in the Hat"; monthly rotation is inert. Subsumed by the WP005/WP007 character redesign (likely "retire" per the fixed-SVG-scene direction). Needs a direction ruling. (Dead-code side: task `task_56162b50` is running in a separate session.)
- [ ] **BUILD** WP001→WP002→WP003→WP004→WP005→WP006, then WP007 (dependency order), via Grok/Cursor on the Mac; **Claude validates each build** (cross-engine, Iron Rule #1). All specs are zero-ambiguity with exact signatures/DDL/ACs.
- [ ] **P003 (OPS):** WAHA docker on waldhomeserver + `whatsapp.py` (publisher already exposes a self-activating hook) + repoint the existing Friday cron + clean deploy to `/data/projects/family-newsletter`. Blockers: WAHA Core-vs-Plus for `sendImage`; cursor-agent headless verify on the *server* (E25).
- [ ] **Mining verify-items** (from `TRANSCRIPT_MINING`): confirm Michal's capoeira "world champion" = grading not a title; Eitan+Sharon's 3 (inferred) children names; sync `profiles/tzlil.md` ↔ `profiles/extended-family.md` (Shlomo marker); Michal's ChatGPT export never ran; `DEPLOY.md` cron path `/opt/famely-neuslettr` ≠ real `/data/...`; `port-registry.yaml` not found.

---

## 4. GOVERNANCE NOTES
- **Subagent scope violation caught + corrected:** one spec-authoring agent edited `src/m4_renderer.py` directly AND self-created `WP008` (in both the dir and roadmap) — two breaches of "ANY code write/edit → LOD400 + build, not a silent edit." **The code edit was reverted and WP008 removed from all locations.** The underlying dead-code finding is preserved (open item above + the running task).
- **Operating model (per memory `family-governance-rules`):** this Claude session should treat `_aos/`+`src/` as **read/spec-only** going forward (working-tree edits auto-revert) and deliver via `_COMMUNICATION/`. The P002 specs are already durable on `origin/main` at `ef0e366` — the receiving team_100/build session builds from there.
- Cross-engine discipline (Grok builds → Claude validates) was smoke-tested end-to-end this session (the memory-file rename) and works on the Mac.

---

## 5. KEY POINTERS
- **The 7 specs:** `_aos/work_packages/FNL-S001-P002-WP00{1..7}/LOD400_spec.md` @ `ef0e366`.
- **Product contract (SSoT):** `_aos/work_packages/FNL-S001-P001-WP001/LOD200.md`.
- **Design intelligence:** `archive/design-april-2026/DESIGN_FISH_2026-07-22.md` + `SVG_MODULE_SPEC.md`.
- **Content intelligence (sensitive, local):** `data/profile-raw/TRANSCRIPT_MINING_2026-07-22.md`.
- **Engine/env + recovery canon:** memory at `~/.claude/projects/-Users-nimrod-Documents-AOS-V5-family-newsletter/memory/` (`family-newsletter-engine-env-canon`, `cutover-memory-slug-dash-not-underscore`, `family-newsletter-revival`, `family-governance-rules`).
- **Roadmap state:** `_aos/roadmap.yaml` (P002 = L-GATE_SPEC/LOD400/IN_PROGRESS).

*Authored by team_100 (this session, via Sonnet subagents). Reply-language with Nimrod = Hebrew; team artifacts = English.*
