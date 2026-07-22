---
id: DECISION_REQUEST_team_00_TO_team_100_MASCOT_CREDIT_LINE_RECONCILIATION_2026-07-22_v1.0.0
type: DECISION_REQUEST
from_team: team_00
to_team: team_100
date: 2026-07-22
subject: "Mascot cover credit-line is INERT — backing detail + a correction for ef0e366's open-item (2)"
relates_to: "commit ef0e366 — flagged OPEN item (2): 'mascot credit-line activate-vs-retire (subsumed by WP005/WP007)'. This note supplies the evidence AND corrects the 'subsumed' claim."
status: "Input to team_00's batch validation of the P002 specs (WP005/WP007). Not a new WP — fold the ruling into WP005/WP007 validation."
decisions_requested:
  - "D1: rule the cover .mascot-name credit line — UPDATE it to the real mascot (Skipper Cat / monthly character) per the 'all fish' decision, i.e. wire neo.metadata (activate). Assign to WP007 (extend past its line-625 exclusion) or WP005."
  - "D2: fold the 3 dead character_* kwargs removal into WP007's existing render() edit (mechanical, zero output change)."
context_pointer: [src/m4_renderer.py, src/m3_normalizer.py, templates/newsletter.html.j2, _aos/work_packages/FNL-S001-P002-WP007/LOD400_spec.md, archive/design-april-2026/DESIGN_FISH_2026-07-22.md]
---

# Mascot cover credit-line — backing detail + correction (ef0e366 open-item 2)

## 0. Context
Found while spec'ing WP005 (`teaser.py`). The parallel P002 batch (`ef0e366`) then
registered all 7 P002 specs and flagged this as OPEN item (2) for team_00,
described as *"subsumed by WP005/WP007."* This note supplies the precise evidence
and **corrects that "subsumed" claim** — it is not, quite. No new WP; decide during
team_00's WP005/WP007 validation.

## 1. The finding (concise, evidenced)
The template's cover `.mascot-name` line (`templates/newsletter.html.j2:506`) reads
`neo.metadata.get('character_emoji'/'character_name'/'character_month')`. **Nothing
in `src/` ever writes those keys** — `neo.metadata` is built once at
`src/m3_normalizer.py:821` and carries only stats/opener/closer/weather (grep-
verified; orchestrator injects nothing M3→M4). So the line **always** renders the
hardcoded fallback **`🎩 Cat in the Hat —`**, every edition; `CHARACTER_SCHEDULE`
is inert. Separately, `render()` still passes 3 **dead** kwargs
(`character_name`/`character_emoji`/`character_style`, `m4_renderer.py:129-131`) the
template never reads at top level (grep-proven).

## 2. Correction to ef0e366: NOT actually subsumed
WP007's committed spec **line 625 + AC-47 explicitly leave the cover credit line
untouched** ("keep their existing static-emoji rendering … scope creep beyond the 4
named poses"). WP007 edits `render()` only for `settings`/`og_image_url` — it does
**not** populate `character_*` metadata and does **not** remove the 3 dead kwargs.
→ After WP005+WP007 build, the credit line **still** renders inert
`🎩 Cat in the Hat —`, and the dead kwargs survive. So the item is a **residual
gap**, not resolved by the current specs.

## 3. Direction under the "all fish" decision
"All fish" (Nimrod, 2026-07-22) **keeps and expands** the mascot system — "Skipper
Cat" mascot + 4 poses + monthly-rotating slots are REQUIRED (WP005/WP007). So the
credit line should be **UPDATED to reflect the real mascot** (Skipper Cat / the
month's character), i.e. **activate/wire it** — not retire, and not leave it stuck
on "Cat in the Hat" in a Skipper-Cat design. Concretely: populate
`neo.metadata['character_name'/'character_emoji'/'character_month']` in
`m3_normalizer._build_neo()` (mirroring the existing `opener_text`/`weather`
pattern), sourced from the WP005 mascot/character system.

## 4. Requested ruling (during WP005/WP007 validation)
- **D1** — assign the credit-line update to **WP007** (extend its scope past
  line 625 to populate + render the real mascot) or to **WP005** (as the owner of
  the character system that feeds it). Pick one so it stops being unowned.
- **D2** — fold the 3 dead-kwarg removal into WP007's existing `render()` edit
  (mechanical, zero output change) rather than a separate ad-hoc `src/` commit.

## 5. Pointers
`src/m4_renderer.py:129-131` (dead kwargs) · `src/m3_normalizer.py:821` (metadata
build) · `templates/newsletter.html.j2:506` (credit line) ·
`_aos/work_packages/FNL-S001-P002-WP007/LOD400_spec.md` (§2.1 p4, line 625, AC-47) ·
`archive/design-april-2026/DESIGN_FISH_2026-07-22.md` ("all fish" decision).
