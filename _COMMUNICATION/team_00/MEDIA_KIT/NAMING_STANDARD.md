# MEDIA ASSET NAMING & ORGANIZATION STANDARD (v1.0, 2026-07-23)

## Why
Editions are numbered (#1, #2, …), each with its own media. Every filename must state
**which edition** and **what the asset is**, so nothing is confused across editions.

## 1. Master library (source of truth — team_00 keeps originals here)
```
media/
  edition-01/
    ed01_hero-scene.png              # landscape cover hero (16:9), opaque
    ed01_hero-scene-teaser.png       # portrait teaser hero (4:5), opaque   [optional]
    ed01_mascot_hero-greeting.png    # waving at the wheel        (transparent)
    ed01_mascot_thinking.png         # puzzle                     (transparent)
    ed01_mascot_pointing.png         # discovery                  (transparent)
    ed01_mascot_reading.png          # from-our-shelf             (transparent)
    ed01_mascot_goodbye.png          # closer                     (transparent)
  edition-02/
    ed02_...
```

## 2. Filename grammar
`ed<NN>_<category>_<slot>[_<variant>].<ext>`
- **ed\<NN\>** — zero-padded edition number (`ed01`, `ed02`). Always first, so the file is self-identifying even when moved.
- **category** — `hero` | `mascot` | `member` | `section`. (For `hero` the category may be the slot itself → `ed01_hero-scene`.)
- **slot** — canonical name from the fixed vocabulary below.
- **variant** *(optional)* — `v2`, `alt`, `sailorhat`, …
- **ext** — `png` (transparent for mascots, opaque for scenes).

## 3. Canonical slot vocabulary (fixed — do not invent ad-hoc names)
- **mascot poses:** `hero-greeting` · `thinking` · `pointing` · `reading` · `goodbye`
- **hero scenes:** `hero-scene` (landscape) · `hero-scene-teaser` (portrait)
- **future:** member → `member_<name>_<pose>` · costume → `mascot_<pose>_<category>`

## 4. Runtime mapping (what the CODE reads)
The pipeline currently reads `assets/characters/<YYYY-MM>/<slot>.png` (month-keyed, legacy).
For **edition-01** (built in 2026-07), copy master → runtime, dropping the `edNN_`/category prefix:
| master | → runtime |
|---|---|
| `media/edition-01/ed01_mascot_hero-greeting.png` | `assets/characters/2026-07/hero-greeting.png` (+ `assets/characters/_placeholder/hero-greeting.png`) |
| `…ed01_mascot_thinking.png` (etc.) | `assets/characters/2026-07/thinking.png` (+ `_placeholder/`) |
| `media/edition-01/ed01_hero-scene.png` | `assets/hero/hero-scene.png` |

**Recommendation (post-build feedback for WP005/WP007 — NOT a mid-build change):** move the
runtime convention from **month-keyed** to **edition-keyed** — `assets/characters/ed01/<slot>.png`
with a `_default/` fallback — to match the product's edition model so future editions stay
clean. Until then, the master→month copy above is the standard.

## 5. Rename the current 6 assets to
| current image | master filename |
|---|---|
| landscape sea scene (cat at wheel) | `media/edition-01/ed01_hero-scene.png` |
| cat at wheel, waving (transparent) | `media/edition-01/ed01_mascot_hero-greeting.png` |
| paw-to-chin + "?" | `media/edition-01/ed01_mascot_thinking.png` |
| pointing right | `media/edition-01/ed01_mascot_pointing.png` |
| reading blue book | `media/edition-01/ed01_mascot_reading.png` |
| tipping hat / waving bye | `media/edition-01/ed01_mascot_goodbye.png` |

Then copy into the runtime paths (§4) and commit. `media/` is the archive; `assets/` is
what ships.
