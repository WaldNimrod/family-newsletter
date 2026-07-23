---
id: VALIDATION_DIRECTIVE_team_00_TO_team_110_P002_BUILD_PRS_2026-07-23_v1.0.0
type: VALIDATION_DIRECTIVE
from_team: team_00 / team_100
to_team: team_110 (Cursor Cloud — CLAUDE model agent)
date: 2026-07-23
engine: "A CLAUDE Cursor model (cross-engine vs the Grok builder — Iron Rule #1). NOT Grok. Do NOT call api.anthropic.com (blocked from Cloud) — use the in-cloud Claude model; tests stay mocked."
run_when: "AFTER the Grok build completes ALL P002 WP PRs (per team_00: wait for the Cloud build's process to finish, then validate + absorb)."
inputs:
  - _COMMUNICATION/team_100/VALIDATION_REPORT_team_00_2026-07-22_P002_7SPEC_BATCH_v1.0.0.md   # the fix-list
  - _COMMUNICATION/team_110/BUILD_DIRECTIVE_team_00_TO_team_110_P002_PIPELINE_2026-07-23_v1.0.0.md
  - _aos/work_packages/FNL-S001-P002-WP001..WP007/LOD400_spec.md
---

# Validation Directive — P002 build PRs (cross-engine)

One Claude-model Cloud agent per PR (or serialized). For each WP PR, validate the diff
against three sources and post a PR review.

## For each PR, confirm:
1. **Spec ACs** — the WP's `LOD400_spec.md` acceptance criteria are met by the diff (the
   corrected ACs, not the self-certifying wrong ones).
2. **The fix-list applied** (VALIDATION_REPORT §3/§5) — spot each P0/P1:
   - **WP001:** empty-`provider_fallback` guard reachable (AC-09); mock AC-10 fixed; `provider` default = **anthropic**; `cursor_model` = **`cursor-grok-4.5-high`** (not `grok-4`).
   - **WP002:** `pause_turn` **REPLACES** message state (not append); AC-25 rewritten; `allowed_callers` handled. *(Live-API items can't be settled in Cloud — see §Escalate.)*
   - **WP003:** `watchlist` DDL = **14** columns; AC-15 bookshelf logic resolved.
   - **WP004:** **unconditional** "Shaked → English" rule present; AC-04 rescoped.
   - **WP005:** `_load_font` forces `raqm_available=False` for the fallback font (no `KeyError`); Rubik font source fixed + `curl -f`.
   - **WP006:** `neo.metadata['editor_name']` set; render(settings=) preflight/build-order guard.
   - **WP007-part2:** AC-47 expects −3; duplicate-string edits target the right element.
3. **Cross-cutting rules** (BUILD_DIRECTIVE §4) — missing content → **visible marked
   placeholder** (not silent-empty); character assets consumed from `assets/…` with
   `_placeholder/` fallback; Anthropic **mocked** in all tests; correct branch/PR.

## Output (per PR)
Verdict **APPROVE** / **CHANGES-NEEDED** + specific `file:line` issues, as a PR review
comment. Then a one-line roll-up per PR to team_00.

## Escalate to team_00 (do NOT approve past these)
- Any **P0 not applied** or **AC regression**.
- **WP002 live-API items** (`pause_turn` real behavior, cost-cap accuracy, `allowed_callers`) — CANNOT be settled in Cloud (Anthropic egress blocked); flag for a **Mac/waldhomeserver** live smoke, not a Cloud approval.
- End-to-end: `weekly-build --mock` must produce HTML **≥30 KB** with all 13 sections present (real or marked-placeholder), and `teaser.py` must render RTL **without crashing**.

## team_00 / Opus spot-check (out of this directive)
Opus will personally review the WP002 (cost-cap / self-certifying ACs) and WP006
(build-order / editor_name) outcomes once the build completes.
