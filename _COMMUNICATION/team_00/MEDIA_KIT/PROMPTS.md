# GENERATION PROMPTS

These are **compact** — they rely on **STYLE_BIBLE.md being loaded in context**. Prefix
every generation with:

> "Draw the 'Skipper Cat' mascot and the visual style EXACTLY per the Style Bible in
> context (same white cat, tall red-and-white striped stovepipe hat, flat ink comic
> style, locked palette). [POSE]. [BACKGROUND]. [FRAMING]. High resolution, crisp clean
> edges, no text."

*(If a tool ignores project context, use the fully-expanded standalone prompts in the
repo's `MEDIA_BRIEF_…SKIPPER_CAT…` instead — same assets, every definition inline.)*

## Tranche A — core assets (generate first)
| file | POSE | background | aspect | min size |
|------|------|-----------|--------|----------|
| `hero-greeting.png` | at the wooden ship's wheel, one paw waving hello, big smile, facing the viewer | TRANSPARENT | 3:4 portrait | 1080×1440 |
| `thinking.png` | one paw to chin, head tilted, a small red "?" above the hat | TRANSPARENT | 1:1 square | 512×512 |
| `pointing.png` | one arm extended, pointing a paw to the RIGHT, other paw on hip, inviting | TRANSPARENT | 1:1 square | 512×512 |
| `reading.png` | holding an open book with both paws, looking down, absorbed | TRANSPARENT | 1:1 square | 512×512 |
| `goodbye.png` | tipping the striped hat with one paw, waving goodbye with the other | TRANSPARENT | 1:1 square | 512×512 |
| `hero-scene.png` | Skipper Cat at the wheel in a flat seaside scene — flat blue sky bands, yellow sun, white clouds, blue sea with white-cap waves, small distant sailboat, red diamond kite, 1–2 leaping fish; leave open sky at the top for a headline (add NO text) | OPAQUE scene | 16:9 | 1280×720 |

## Delivery — exact format & paths
- **#1–#5:** transparent **PNG-24 (alpha)**, filenames exactly as above. Place in **BOTH**:
  `assets/characters/2026-07/` **and** `assets/characters/_placeholder/`
- **#6:** opaque PNG → `assets/hero/hero-scene.png`
- Then **commit to origin** so the build + runtime see them. Until they arrive, the
  pipeline shows emoji placeholders (safe).

## Consistency tip
Generate `hero-greeting.png` first, add it to context as the anchor, THEN do the rest.

## Tranche B (only if team_00 confirms) — per-member + per-category
See `FAMILY_CHARACTERS.md`. Same bible, same lock. These also need pipeline **selection
logic** to be used — confirm scope before generating the ~15 variants.
