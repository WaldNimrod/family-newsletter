---
id: MEDIA_BRIEF_team_100_TO_team_00_SKIPPER_CAT_ASSETS_EDITION1_2026-07-23_v1.0.0
type: MEDIA_BRIEF
rev: "1.1 (2026-07-23) — CORRECTED SCOPE: all graphics ship in edition-1; only the SOURCE changes (hand-made, delivered ready — not engine-generated). Nothing graphic is deferred to edition-2."
from_team: team_100 (spec) → for team_00 (Nimrod, manual generation)
date: 2026-07-23
subject: "Edition-1 graphic assets — precise, self-contained generation prompts for an online image engine (Nano Banana / GPT)"
decision_of_record: "ALL edition-1 graphics are hand-made by team_00 and delivered as ready PNGs; the pipeline consumes pre-made files. The SVG *generation engine* (auto-drawing) is what's replaced by manual delivery — the graphics themselves are NOT deferred. Supersedes any 'Skipper Cat / SVG → edition-2' wording in prior docs (VALIDATION_REPORT §4, DECISION_REQUEST)."
context_pointer: [archive/design-april-2026/DESIGN_FISH_2026-07-22.md, SVG_MODULE_SPEC.md, src/m4_renderer.py, _aos/work_packages/FNL-S001-P002-WP005/LOD400_spec.md, _aos/work_packages/FNL-S001-P002-WP007/LOD400_spec.md]
---

# Media Brief — Edition-1 graphics (manual generation), CORRECTED

## 0. Decision of record (corrects all prior docs)
**All edition-1 graphics ship in edition-1.** The only change from the original
design: instead of an SVG engine drawing them at runtime, **team_00 generates them by
hand and delivers finished PNGs**; the built pipeline just places the files. Nothing
graphic is pushed to edition-2. (The deferred item is only the *auto-generation engine*,
which manual delivery replaces.)

## 1. How the pipeline uses these
The build (WP005 teaser + WP007 template) reads pre-made images from
`assets/characters/<dir>/<pose>.png` and the cover hero. Drop the files at §4 paths →
they render automatically. Missing file → emoji fallback (so partial delivery is safe).

## 2. Asset inventory for edition-1
**Tranche A — core mascot (6 assets, spec'd with full prompts in §5, do these first):**
| # | file | used in | type |
|---|------|---------|------|
| 1 | `hero-greeting.png` | cover mascot + teaser | transparent character, 3:4 |
| 2 | `thinking.png` | puzzle | transparent character, 1:1 |
| 3 | `pointing.png` | discovery | transparent character, 1:1 |
| 4 | `reading.png` | From-Our-Shelf | transparent character, 1:1 |
| 5 | `goodbye.png` | closer | transparent character, 1:1 |
| 6 | `hero-scene.png` | cover banner / teaser background | full illustrated scene, 16:9, opaque |

**Tranche B — extended DESIGN_FISH library (CONFIRM if edition-1 includes it):** per-member
characters ×5 (נימרוד/מיכל/שקד/יויו/צליל) + per-category costumed cats ×~10 (architect-cat,
circus-cat…). **These also require pipeline *selection logic* (topic→character→costume) to
be USED — a real build addition.** Tell me if edition-1 needs Tranche B and I'll spec every
one with the same precision (≈15 prompts) + flag the build work; otherwise edition-1 = Tranche A.

## 3. One-time consistency note
Each prompt below is fully self-contained (all character/style/palette inline), so any
engine produces the same cat. For extra consistency you MAY also attach asset #1's output
as a reference to #2–#5 — optional, the text alone is sufficient.

## 4. Exact output paths & format
Deliver as **PNG-24 with alpha (transparent)** for #1–#5, **opaque PNG** for #6. Exact
lowercase-hyphen filenames. Place #1–#5 in **both**:
```
assets/characters/2026-07/<pose>.png
assets/characters/_placeholder/<pose>.png
```
Hero scene → `assets/hero/hero-scene.png`. (Build note, team_110: add a `_placeholder/`
fallback to `get_character_html()` — it currently checks only the month dir; fold into WP007.)

## 5. PRECISE, SELF-CONTAINED PROMPTS (each is a complete standalone prompt)

### #1 — hero-greeting.png
```
A single children's-book mascot character on a FULLY TRANSPARENT background (PNG with alpha; NO background, NO scenery, NO frame, NO text).
CHARACTER — "Skipper Cat" (draw exactly, identically): a friendly cartoon domestic CAT standing upright on two legs, FULL BODY head-to-feet. Fur WHITE (#ffffff) with a few warm-red (#c0392b) stripe accents on the tail. He wears a TALL stovepipe hat with horizontal RED (#c0392b) and WHITE stripes (Cat-in-the-Hat hat). Large round friendly eyes, small pink triangular nose, whiskers, warm closed-mouth smile; cute child-friendly proportions (big head, small rounded body).
STYLE: hand-drawn INK illustration — Quentin Blake's loose energetic ink lines meets Hergé's clean flat "ligne claire" fills. BOLD uneven black ink outlines (#2c2c2c). FLAT solid colors ONLY — no gradients, no soft shading, no airbrush, no 3D, no photorealism, no gloss.
PALETTE (only these): ink #2c2c2c · red #c0392b · white #ffffff · wood #8B4513. No other colors.
POSE: standing behind a large brown wooden ship's wheel (#8B4513), one front paw raised waving hello, big welcoming smile, looking at the viewer.
FRAMING: character centered, portrait 3:4, generous transparent margin.
OUTPUT: transparent PNG, at least 1080×1440, high resolution, crisp clean edges.
```

### #2 — thinking.png
```
A single children's-book mascot character on a FULLY TRANSPARENT background (PNG with alpha; NO background, NO scenery, NO frame, NO text).
CHARACTER — "Skipper Cat": friendly cartoon domestic CAT standing upright, FULL BODY. Fur WHITE (#ffffff) with a few red (#c0392b) stripe accents on the tail. TALL red-and-white horizontally-striped stovepipe hat. Round friendly eyes, small pink nose, whiskers, warm smile; cute child-friendly proportions.
STYLE: hand-drawn INK illustration, Quentin Blake meets Hergé; BOLD uneven black ink outlines (#2c2c2c); FLAT solid colors only — no gradients/shading/3D/photorealism.
PALETTE (only these): ink #2c2c2c · red #c0392b · white #ffffff. No other colors.
POSE: one front paw raised to his chin, head tilted slightly, eyes looking upward, a small red "?" floating just above the hat — thinking/pondering.
FRAMING: character centered, square 1:1, generous transparent margin.
OUTPUT: transparent PNG, at least 512×512, high resolution, crisp clean edges.
```

### #3 — pointing.png
```
A single children's-book mascot character on a FULLY TRANSPARENT background (PNG with alpha; NO background, NO scenery, NO frame, NO text).
CHARACTER — "Skipper Cat": friendly cartoon WHITE (#ffffff) domestic CAT standing upright, FULL BODY, red (#c0392b) tail-stripe accents, TALL red-and-white striped stovepipe hat, round friendly eyes, pink nose, warm smile, cute proportions.
STYLE: hand-drawn INK illustration, Quentin Blake meets Hergé; BOLD uneven black ink outlines (#2c2c2c); FLAT solid colors only — no gradients/shading/3D/photorealism.
PALETTE (only these): ink #2c2c2c · red #c0392b · white #ffffff. No other colors.
POSE: one front arm extended, pointing a paw clearly to the RIGHT; other paw on hip; cheerful, inviting the viewer to "look here".
FRAMING: character centered, square 1:1, generous transparent margin.
OUTPUT: transparent PNG, at least 512×512, high resolution, crisp clean edges.
```

### #4 — reading.png
```
A single children's-book mascot character on a FULLY TRANSPARENT background (PNG with alpha; NO background, NO scenery, NO frame, NO text).
CHARACTER — "Skipper Cat": friendly cartoon WHITE (#ffffff) domestic CAT standing upright, FULL BODY, red (#c0392b) tail-stripe accents, TALL red-and-white striped stovepipe hat, round friendly eyes, pink nose, warm smile, cute proportions.
STYLE: hand-drawn INK illustration, Quentin Blake meets Hergé; BOLD uneven black ink outlines (#2c2c2c); FLAT solid colors only — no gradients/shading/3D/photorealism.
PALETTE (only these): ink #2c2c2c · red #c0392b · white #ffffff · book cover blue #2471a3. No other colors.
POSE: holding an open book with both front paws, looking down at the pages, content and absorbed in reading.
FRAMING: character centered, square 1:1, generous transparent margin.
OUTPUT: transparent PNG, at least 512×512, high resolution, crisp clean edges.
```

### #5 — goodbye.png
```
A single children's-book mascot character on a FULLY TRANSPARENT background (PNG with alpha; NO background, NO scenery, NO frame, NO text).
CHARACTER — "Skipper Cat": friendly cartoon WHITE (#ffffff) domestic CAT standing upright, FULL BODY, red (#c0392b) tail-stripe accents, TALL red-and-white striped stovepipe hat, round friendly eyes, pink nose, warm smile, cute proportions.
STYLE: hand-drawn INK illustration, Quentin Blake meets Hergé; BOLD uneven black ink outlines (#2c2c2c); FLAT solid colors only — no gradients/shading/3D/photorealism.
PALETTE (only these): ink #2c2c2c · red #c0392b · white #ffffff. No other colors.
POSE: tipping the striped stovepipe hat with one front paw while waving the other paw goodbye; warm farewell smile.
FRAMING: character centered, square 1:1, generous transparent margin.
OUTPUT: transparent PNG, at least 512×512, high resolution, crisp clean edges.
```

### #6 — hero-scene.png (full cover banner, OPAQUE)
```
A wide illustrated cover banner in a children's-book comic style. NO text anywhere (leave open sky for a headline to be added later).
STYLE: Quentin Blake's loose energetic ink lines meets Hergé's clean flat "ligne claire"; BOLD black ink outlines (#2c2c2c); FLAT solid color fills in clean bands — NO smooth gradients, no 3D, no photorealism.
SCENE: a bright seaside. Sky in flat blue bands (#2471a3 upper, lighter blue lower), a round yellow (#f39c12) sun, two or three simple white clouds. Blue sea below with flat white-capped waves; a small distant sailboat; a red (#e74c3c) diamond kite high in the sky; one or two cartoon fish leaping from the water.
FOREGROUND CENTER: "Skipper Cat" — a friendly cartoon WHITE (#ffffff) cat standing at a large brown wooden ship's wheel (#8B4513), wearing a TALL red-and-white (#c0392b) striped stovepipe hat, waving hello with one paw, big warm smile.
COMPOSITION: leave clear open sky in the UPPER portion for a text overlay (add none yourself). Warm, playful, family-friendly.
OUTPUT: opaque PNG, landscape 16:9, at least 1280×720, high resolution.
```

## 6. Return
Deliver the 6 files at the §4 paths (or hand them back and we place them) → commit to
origin so the Cloud build/runtime sees them. Then the cover, teaser, and all 5 mascot
slots render the real Skipper Cat. Confirm Tranche B (§2) if edition-1 needs the extended library.
