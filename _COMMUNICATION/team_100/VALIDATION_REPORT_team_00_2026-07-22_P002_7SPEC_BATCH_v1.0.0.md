---
id: VALIDATION_REPORT_team_00_2026-07-22_P002_7SPEC_BATCH_v1.0.0
type: VALIDATION_REPORT
from_team: team_00 (validation gate — Claude Opus synthesis over 7 Sonnet spec-validators)
to_team: team_110 (build) + team_100 (spec-fix) + team_00 (decisions)
date: 2026-07-22
head_commit: ef0e366 (origin/main — specs validated AS COMMITTED here)
verdict: "BATCH = GO-WITH-FIXES. NO-GO for an immediate Grok build until the P0 fixes below land + 1 content decision + Cursor Cloud confirmation."
next_step: "Apply P0 spec-fixes (§5); team_00 rules the content-ownership gap + Skipper-Cat scope (§7); team_110 confirms Cursor Cloud (separate RESEARCH_REQUEST); then Grok builds in the corrected order (§6)."
context_pointer:
  - _aos/work_packages/FNL-S001-P002-WP001..WP007/LOD400_spec.md
  - _aos/work_packages/FNL-S001-P001-WP001/LOD200.md
  - _COMMUNICATION/team_100/HANDOFF_team_100_2026-07-22_RECOVERY_AND_P002_LOD400_BATCH_TO_BUILD_v1.0.0.md
  - _COMMUNICATION/team_110/RESEARCH_REQUEST_team_00_TO_team_110_CURSOR_CLOUD_CAPABILITIES_2026-07-22_v1.0.0.md
---

# Consolidated Validation — P002 7-spec LOD400 batch (@ ef0e366)

**Method:** 7 independent Sonnet validators (one per spec), each checking build-
readiness against the LOD200 contract + the *live* code, then an Opus cross-spec
synthesis. Every spec is **rigorous and well-ground-truthed** — the defects below
are narrow and mechanical, not architectural. But several are **self-certifying**
(a wrong AC that a corner-cutting Grok build would satisfy by corrupting correct
code), so they MUST be fixed in the specs before Grok touches them.

## 0. Verdict
**BATCH = GO-WITH-FIXES.** All 7 WPs are individually GO-WITH-FIXES (zero NO-GO).
**But NO-GO for an immediate build** until: (A) the P0 spec-fixes in §5 land, (B)
team_00 rules the content-ownership gap (§7 D1), (C) Cursor Cloud capabilities are
confirmed (the separate team_110 research request).

## 1. Per-WP verdicts

| WP | Module | Verdict | P0 must-fix (before Grok) |
|---|---|---|---|
| WP001 | llm.py | GO-WITH-FIXES | AC-09 guard unreachable; AC-10 mock+JSON path actually raises |
| WP002 | token_tracker | GO-WITH-FIXES | 🔴 `pause_turn` appends vs replaces → O(N²) cost + **AC-25 codifies the bug**; `allowed_callers` likely-invalid API field |
| WP003 | researcher.py | GO-WITH-FIXES | AC-83 counts 13 vs **14** watchlist cols (Grok may drop a column); AC-15 bookshelf-fallback logic bug |
| WP004 | editor.py | GO-WITH-FIXES | Shaked "English-only" enforced only in fallback path → ships Hebrew; AC-04 unsatisfiable (schema `{}` vs "no `{}`") |
| WP005 | teaser.py | GO-WITH-FIXES | 🔴 RTL raqm + font-fallback → **KeyError crashes whole build**; Rubik font URLs **404** |
| WP006 | orchestrator+publisher | GO-WITH-FIXES | 🔴 build-order crash: calls `render(settings=)` that only exists post-WP007; `editor_name`≠`editor_credit` silent-drop |
| WP007 | template | GO-WITH-FIXES | AC-47 miscount (−3 not −2); sections 7/8/10 unpopulated |

## 2. Cross-spec findings (what no single validator saw)

**2.1 🔴 BUILD-ORDER CRASH + file-ownership collision (WP006 ↔ WP007).** WP006 calls
`render(neo, …, settings=settings)`, but the `settings=` param only exists after
**WP007** patches `m4_renderer.py`. The HANDOFF's stated order (…→WP006, *then* WP007)
is therefore **wrong** — building WP006 first crashes its own first smoke test
(`TypeError: render() got an unexpected keyword argument 'settings'`). Worse, WP007's
"companion edits" to `orchestrator.py` (1 line) + `m3_normalizer.py` (4 lines) target
files WP006 **fully rewrites/archives** → double-edit collision.
**Resolution (fold into the manifest, §6):** assign each file's final state to ONE WP —
(a) build WP007's `m4_renderer.py render(settings=)/og_image_url` + `models.py` fields
FIRST (the interface WP006 calls); (b) WP006 then owns the *final* `orchestrator.py`
+ `m3_normalizer.py` (including the settings-threading + the 4 `neo.metadata` fields —
WP006 must NOT rely on WP007's companion edits); (c) WP007's `template.j2` builds LAST.

**2.2 🔴 `editor_name` vs `editor_credit` mismatch (WP006 ↔ WP007) — silent wrong output.**
WP006 writes `neo.metadata['editor_credit']`; the WP007 footer reads
`neo.metadata.get('editor_name', 'צליל')`. Keys never meet → the footer **always**
renders the hardcoded `'צליל'`, never `editor.py`'s real output. Invisible for
edition-1 (default = LOD200's literal text), so no AC catches it. **Fix:** pick ONE
key name in both specs.

**2.3 ✅ teaser.png chain — VERIFIED CLEAN (3-way).** WP005 writes local
`data/archive/teasers/{date}.png` → WP006 FTP-uploads it as remote `teaser.png` →
WP007 `og_image_url` reads `…/{date}/teaser.png`. Cross-checked by the WP005, WP006 AND
WP007 validators — consistent, no drift. (Cosmetic: WP007's prose calls this an
open gap; it isn't — WP006 owns the rename. Update WP007's wording.)

**2.4 ✅ llm.py + token_tracker contracts — verified match.** `llm.configure()`/
`complete()` signatures match every caller (WP004, WP006); WP003 correctly bypasses
`llm.py` and calls `token_tracker.research()` directly, whose signature matches WP002.
One dormant note: `complete(tools=…)` raises bare `NotImplementedError` (not an
`LLMError` subclass) — inert today (no caller passes tools).

**2.5 🔴 CONTENT-OWNERSHIP GAP — top program risk (confirmed by 4 validators).**
Sections **8 (שולחן שישי / Family-Table)** and **10 (מהמשפחה המורחבת / Extended-Family)**
have **NO producer** anywhere in WP001–WP007: WP003 defers both to WP004, WP004 defers
both back to WP003; WP006 wires safe empty-defaults; WP007 renders empty. → Edition-1
**cannot** meet LOD200 §3's "all 13 sections present." **This is a CONTENT decision for
team_00, not just code** (Extended-Family has no publish-ready safe headline yet).
WP006's recommended fix: `family_table_text` from `profiles/family.md` "active threads"
(zero-LLM, via editor.py); a small zero-LLM researcher curation for Extended-Family
from `profiles/extended-family.md` — **once you supply a safe item.**

**2.6 Unenforced LOD200 "hard rules" (cross-cutting).**
- **"Every member ≥1 item"** (LOD200 hard rule) — enforced NOWHERE; a member with an
  empty scored pool renders as a silent missing corner. No escalation (unlike cost-cap).
- **Shaked "English only"** — only in editor.py's fallback path (§2.1 above).
- **"HTML ≥ 30KB"** (LOD200 §3 acceptance) — no WP tests it end-to-end post-rewire.

## 3. Systemic risks (batch-level)

**3.1 🔴 Self-certifying wrong ACs — correct BEFORE Grok.** Grok chases green checkmarks
and trusts ACs over judgment, so a wrong AC gets "satisfied" by breaking correct code.
Confirmed instances: WP001 AC-09/AC-10 · WP002 **AC-25** (codifies the cost bug) · WP003
**AC-83** (13 vs 14 cols → may drop a `watchlist` column) / AC-07 / AC-15 · WP004 AC-04 ·
WP007 AC-47. **A spec-AC correction pass is a hard gate before build.**

**3.2 `pytest` + `pytest-mock` not installed; no spec authorizes adding them** (WP001,
WP002, WP004, WP006 share this). → Either zero automated AC verification, or Grok
silently `pip install`s undeclared deps. Needs explicit authorization + Cursor Cloud A2.

**3.3 Env-dependent blockers → the Cursor Cloud research (team_110).** WP005 raqm/libraqm
+ Pillow (A3); WP002 live-API smoke test for `pause_turn`/`allowed_callers` (E1);
pytest install (A2). These CANNOT be settled until the Cursor Cloud capabilities report
lands.

## 4. Scope ruling applied — Skipper Cat → edition #2
Per team_00 (2026-07-22): the SVG "Skipper Cat" mascot system is **deferred to edition
#2**. Independently corroborated by validation — no character art exists (only
`.gitkeep`), `CHARACTER_SCHEDULE` stops at May, and no caller supplies `hero_category`,
so the mascot would be invisible anyway. **Carve-out:** WP005 = teaser image (RTL) only;
WP007 = sections/corners/dark-mode/footer, **no mascot slots**. The inert
`neo.metadata['character_*']` credit-line is **deferred, not fixed** (dead-kwarg cleanup
tracked separately).

## 5. Prioritized fix-list (spec edits before build)

**P0 — block the build (crash / corruption / cost-cap / policy):**
1. WP002: fix `pause_turn` to **replace** (not append) message state; rewrite AC-25.
2. WP005: `_load_font` fallback must force `raqm_available=False` for that draw (stop the KeyError crash); fix the Rubik font source + add `curl -f`.
3. WP006: resolve build-order (§2.1) with a preflight + the file-ownership split; add `editor_name` (§2.2).
4. WP003: AC-83 → 14 columns; resolve AC-15 bookshelf logic.
5. WP004: add unconditional "Shaked → English"; rescope AC-04.
6. WP001: fix AC-09 guard + AC-10 mock op.
7. WP007: AC-47 → −3.
8. Batch: the §3.1 AC-correction pass; authorize `pytest`/`pytest-mock` (§3.2).

**P1 — fix before ship (silent-wrong / coverage):** WP002 cost-under-report + 6-keys;
WP003 AC-07 + retry "(see above)"; WP004 Nimrod "no-farm-business"; WP005 Shaked name
→ English; WP006 add 30KB + member≥1 checks; WP007 duplicate-string targeting.

**P2 — hygiene:** Twilio docs still in README/.env.example; `GeneratedContent` now dead
post-rewire (rename/annotate); `editors_choice` unowned.

## 6. Build manifest (corrected dependency order — for the Cursor Grok session)
0. **Preflight:** `pip install pytest pytest-mock` (pending Cursor Cloud A2); confirm Pillow raqm (A3).
1. **WP001** llm.py → validate.
2. **WP002** token_tracker (with P0 fixes) → validate incl. **live-API smoke** (pause_turn, allowed_callers).
3. **WP003** researcher.py → validate (+ WP002→WP003 integration smoke: real items returned).
4. **WP004** editor.py → validate.
5. **WP005** teaser.py (with raqm/font P0 fixes) → validate + **human RTL eyeball** (not automatable).
6. **WP007-part-1**: `m4_renderer.py render(settings=)/og_image_url` + `models.py` fields → validate.
7. **WP006** orchestrator+publisher (owns final orchestrator.py + m3_normalizer.py) → validate end-to-end (build→HTML≥30KB→FTP 200).
8. **WP007-part-2**: `template.j2` → validate (dark-mode needs a real headless browser).
Each step: Grok builds → Claude validates (cross-engine, Iron Rule #1).

## 7. Decisions needed from team_00
- **D1 (gates edition-1): content-ownership gap.** Approve WP006's fix (family_table_text from profiles/family.md; researcher curation for extended-family) AND **supply a safe extended-family headline** (or explicitly drop section 10 from edition-1). Without this, edition-1 fails "13 sections."
- **D2: AC-correction pass ownership** — who edits the specs' P0 ACs (a Sonnet session), before Grok?
- **D3: pytest/pytest-mock** — authorize adding to requirements/dev-deps?
- **D4: Skipper-Cat carve-out** — confirm §4 (and: keep the 4 static emoji poses in edition-1, or drop all mascot wiring? default = drop).

## 8. Gates before build starts
1. P0 fixes (§5) applied to the specs on origin.  2. D1 content decision.  3. Cursor
Cloud capabilities report (team_110) = BUILD-GO.  Then: schedule the Cursor Grok build per §6.
