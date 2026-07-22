---
lod_target: LOD400
lod_status: DRAFT
track: A
authoring_team: "team_100 (familynewsletter_arch)"
consuming_team: familynewsletter_build
date: 2026-07-22
version: v1.0.0
supersedes: null
---

# teaser.py — WhatsApp Teaser Card Generator (Pillow, Hebrew RTL, Skipper Cat Mascot) — LOD400 Implementation Spec

**work_package_id:** FNL-S001-P002-WP005
**parent_lod200:** _aos/work_packages/FNL-S001-P001-WP001/LOD200.md
**parent_lod300:** N/A — Track A only
**approved_by:** [PENDING — familynewsletter_build sign-off at L-GATE_SPEC]
**approved_at:** [PENDING]

## 1. Scope reminder

This WP creates **`src/teaser.py`** (new file, does not exist yet) — a pure-Python, Pillow-based raster renderer that produces **`teaser.png`**, a **1080×1350 portrait WhatsApp cover card**, from one edition's `NEO` object. Per **REVIVAL_PLAN_2026-07-22.md §3** (pipeline sketch): *"teaser.png: כרטיס שער 1080×1350 ב-Pillow (פלטת הקומיקס, כותרת לכל בן משפחה)"* — a 1080×1350 cover card in Pillow, comic palette, a headline per family member. And **§4, Phase A step 4:** *"`teaser.py` (Pillow, לוודא עברית RTL — raqm/bidi)"*.

The card carries: the edition masthead (English wordmark + Hebrew family name + date/edition badge, in the exact comic visual language of `templates/newsletter.html.j2`'s `.cover`), the monthly-rotating **Skipper Cat mascot** (or whichever character is scheduled — a pre-rendered PNG asset, selected by pose and optionally by topic-costume) with a short greeting speech bubble, and **one headline row per family member** (all 5, always, colored/labelled per the project's canonical member palette). Hebrew text is shaped via a libraqm-enabled Pillow build when available, with a `python-bidi` + `arabic-reshaper` fallback path that is treated as the **dependably-correct baseline**, not a rare edge case (see §1 Assumption 2).

**This composition is a new, purpose-built portrait card — not a pixel-for-pixel derivation of the HTML `.cover` block.** It reuses, verbatim, the exact color tokens, the flat-offset-shadow/thick-ink-border/halftone-texture visual *grammar*, and the exact masthead/edition-badge/footer *copy conventions* already shipping in `templates/newsletter.html.j2` (ground-truthed by reading that file directly — see citations throughout §2). The concrete pixel geometry in §2 is new layout work for the 1080×1350 portrait format; it is not derived by a mechanical scale factor from the 640px-wide HTML layout.

**Design sources (read in full before implementing):**
- `REVIVAL_PLAN_2026-07-22.md` §3 (pipeline sketch, keep/archive table, cost model) and §4 Phase A step 4 (quoted above).
- `archive/design-april-2026/DESIGN_FISH_2026-07-22.md` — the ✅ DECISION block (this WP is explicitly assigned the SVG hero + mascot system as **required**, not optional) and §1 (exact palette/fonts/comic mechanics) + §2 (Skipper Cat, 4 poses, per-category costuming, topic table).
- `SVG_MODULE_SPEC.md` (repo root) — §3.3 (5-member character briefs), §4 (Hero Composition Rules + the topic→scene→character→decoration lookup table), §5 (art-direction one-liner).
- `STYLE_GUIDE.md` — the **declared SSOT** for member id/name/emoji/color (§8, "This table is the source of truth for family member data across all systems") and the binding footer requirement (§1, "by AgentsOS @ nimrod.bio").
- `templates/newsletter.html.j2` — ground truth for exact hex values, gradient stops, shadow offsets, halftone parameters, and masthead/footer copy (grepped and read directly for this spec; DESIGN_FISH's summary of these values is corroborated, not just trusted secondhand).
- `data/profile-raw/TRANSCRIPT_MINING_2026-07-22.md` → "Pipeline / engine / env" section (this is the accessible, filesystem-readable record of the `family-newsletter-engine-env-canon` memory entry referenced in the task brief — the memory entry itself is not a repo file; this transcript section explicitly cross-references it and contains the same facts): *"Teaser tech: Pillow needs libraqm build for Hebrew RTL (fallback python-bidi); fonts Rubik/Secular One; Playwright deferred (Chromium too heavy)."*
- `src/models.py` (`NEO` dataclass), `src/m4_renderer.py` (existing character-asset convention and `save_html()`'s output-path convention, both reused/mirrored below), `_aos/work_packages/FNL-S001-P002-WP001/LOD400_spec.md` and `.../WP004/LOD400_spec.md` (sibling specs — cited for precedent and for confirming what this WP does *not* need to depend on; see Assumption 1).

### Assumptions (where the brief was silent — flag these at L-GATE_VALIDATE if wrong)

1. **The exact shape of `neo.member_sections[i]` is not pinned by any approved LOD400 at spec-authoring time, and this is a verified, not speculative, finding.** `researcher.py` (WP003) has no LOD400 spec yet (its work-package directory is empty). `editor.py` (WP004, LOD400 exists) does **not** produce `member_sections` either — its own §3 mapping table explicitly lists `teaser_caption`/`editors_choice`/`editor_credit` as new fields with *"(none)"* existing-field mapping, and never mentions `member_sections` at all; WP004 §6 explicitly scopes "researcher.py / item selection" as WP003's territory, not its own. The current `templates/newsletter.html.j2` (read directly for this spec, line 519–528) is the only concrete evidence of an assumed shape, and it implies `member_sections[i] = {"member_id": str, "items": list[...]}` (`section['items']|length` is called) — a list of items per member, not a single headline string. Since teaser.py needs exactly **one** headline per member (a compact card, not a digest), §2.7 defines the minimal read contract: `member_sections[i]["items"][0]` (first/highest-priority item) is read for a `"headline"` string, falling back to `"title"` (NCI's raw-article-title field name) if `"headline"` is absent, falling back to a neutral placeholder string if neither exists or `items` is empty. This is a defensive, multi-tier fallback — not a hard dependency on any one upstream shape. Flag at L-GATE_VALIDATE if WP003 lands with a genuinely different shape; only `_member_headline()` (§2.7) would need updating.
2. **libraqm is not assumed to be present on either the Mac (dev/build) or waldhomeserver (Linux, runtime) host, and this WP does not attempt to force-install a raqm-enabled Pillow build** (e.g. `brew install raqm` + compiling Pillow from source with `--enable-raqm`). That is heavy, fragile setup work out of proportion to this project's L0/Lean profile. Instead: `python-bidi` + `arabic-reshaper` is the **dependably-correct baseline path**, always present and always exercised when raqm isn't detected; raqm (detected at runtime via `PIL.features.check("raqm")`, confirmed the correct, documented API — see §2.2) is an opportunistic quality enhancement, not a hard requirement. This directly satisfies the task brief's explicit instruction to concretely spec "how to detect libraqm; the fallback" (§2.2, §2.3).
3. **Rubik + Secular One (not Bangers/Patrick Hand) are used for all Hebrew text**, because Bangers and Patrick Hand — both used by `templates/newsletter.html.j2` for the *English/Latin* comic look — are Latin-only Google Fonts with **zero Hebrew glyph coverage**. This is not a stylistic preference; it is a hard technical fact confirmed while researching this spec (Google Fonts' `google/fonts` OFL repository lists only Latin/Cyrillic/Greek glyph ranges for both families). Passing Hebrew text through them in Pillow (unlike a browser, which silently substitutes a fallback system font per CSS `font-family` list semantics) would render blank boxes ("tofu") or raise, since Pillow has no automatic cross-font glyph fallback. Bangers is still used for the one pure-Latin string on the card (the "Family Newsletter!" wordmark, matching the template exactly); Secular One (a Hebrew+Latin humanist display face, single weight) stands in for Bangers' comic-display *role* on Hebrew strings; Rubik (multi-weight, excellent Hebrew coverage) is used for smaller Hebrew body/label text, standing in for Patrick Hand's role. Both are real, freely-licensed (SIL OFL) Google Fonts with confirmed download URLs (§3).
4. **`assets/og-images/` (pre-existing, currently-empty `.gitkeep` placeholder directory) is deliberately NOT used as the teaser output location.** Its intended purpose is undocumented and ambiguous (possibly a future static/fallback OG image, unrelated to the weekly-regenerated teaser). Instead, `generate_teaser()`'s default output directory mirrors `m4_renderer.save_html()`'s existing, working convention exactly: `data/archive/{type}/{date}.{ext}` → `data/archive/teasers/{date}.png` (a build artifact under the already-gitignored `data/` tree, auto-created via `Path.mkdir(parents=True, exist_ok=True)`, same as `save_html()`). If WP006/WP007 need a different path, it is a one-line change to `generate_teaser()`'s `output_dir` default — flag at L-GATE_VALIDATE.
5. **`hero_category` (the topic that drives the mascot's optional costumed variant, §2.6) is accepted as a plain, caller-supplied `Optional[str]` parameter, not derived internally.** `SVG_MODULE_SPEC.md §4`'s `select_hero_topic()` is pseudocode over the OLD, now-discarded scored-content architecture (per-member `relevance_score` on curated items) that REVIVAL_PLAN §3's keep/archive table retires. Re-implementing an equivalent scoring function inside teaser.py would silently duplicate editorial-selection logic that belongs upstream (in whichever future WP assembles `NEO` — orchestrator or editor.py) and risks disagreeing with it. `generate_teaser()` therefore accepts `hero_category: Optional[str] = None`; if `None` or unrecognized, the mascot renders in its plain base pose with no costume (§2.6) — never an error.
6. **`STYLE_GUIDE.md`'s member table (§8: "the source of truth for family member data across all systems") is this WP's SSOT for member id/Hebrew name/emoji/primary hex color** — not `config/family.json` (which has no `color`/`emoji` fields at all) and not the Jinja `{% set %}` blocks inside `templates/newsletter.html.j2` (which duplicate the same values inline, confirmed identical by direct read, but are template-local, not an importable/citable module). The per-member **light tint** background colors (used for each headline row's chip background, §2.7) are not part of STYLE_GUIDE's table; those are taken from `templates/newsletter.html.j2`'s own `{% set member_bg = ... %}` line (read directly, line 491), corroborated by DESIGN_FISH §1.
7. **This WP deliberately deviates from `STYLE_GUIDE.md §1`'s generic character-asset fallback rule** ("Fallback: If asset unavailable, use emoji placeholder matching character theme"). Pillow cannot reliably render color/bitmap emoji glyphs across platforms (Mac dev vs. Linux runtime) without a bundled color-emoji font and non-trivial size/engine constraints — unlike a browser, which resolves emoji via the OS's own color-emoji font automatically. Per-member markers therefore use a **plain filled color circle** (the member's primary hex) instead of an emoji glyph — this exact "colored dot, no emoji" pattern is already established, working precedent inside `templates/newsletter.html.j2` itself (its `.dot` spans, e.g. line 524), so this is a deviation from STYLE_GUIDE's *generic* fallback prose in favor of a *more specific, already-shipping* pattern from the same design system — not an invented new style. Flagged explicitly per STYLE_GUIDE's own rule ("Any deviation requires Team 00 approval") for team_00's end-of-batch review.
8. **`teaser.py` has no database access and makes no `llm.py`/`editor.py` calls.** It is a pure function of `(NEO, options) → file path`. `edition_number` is accepted as a plain optional caller-supplied `int` (the orchestrator computes it once — the same `SELECT COUNT(*) FROM newsletters ...` query `m4_renderer.render()` already runs — and passes the identical value to both `m4_renderer.render()` and `generate_teaser()` so the two artifacts never disagree). `editor.py`'s `teaser_caption` field (WP004 §3: *"consumed directly by a future publisher.py/whatsapp.py/teaser.py... not by GeneratedContent"*) is the **WhatsApp message text** sent alongside the image — a separate string, not drawn onto the PNG. `teaser.py` does not read or depend on it; that consumption, if any, belongs to `publisher.py`/`whatsapp.py` (WP006, out of scope — §6). `neo.greeting`'s future population source is itself flagged as unresolved by WP004 (§3: *"looks superseded by the new architecture's richer opener... noted, not resolved"*); teaser.py reads `neo.greeting` defensively (§2.6) and degrades gracefully to no-bubble if it is empty, so this WP is correct regardless of how that upstream question resolves.
9. **`src/teaser.py` does not import from `src/m4_renderer.py`.** The two modules share the **asset directory/filename scheme** (`assets/characters/{YYYY-MM}/{pose}.png`, per `STYLE_GUIDE.md §1` and `m4_renderer.get_character_html()`), extended here with an optional `{pose}__{topic}.png` costumed variant — that is a filesystem convention, not a Python API, and WP007's HTML template only ever needs an `<img src="...">` path string. Keeping teaser.py import-free of `m4_renderer.py` keeps it independently buildable/testable and avoids coupling two otherwise-unrelated rendering paths.

## 2. Technical specification

This WP creates one new file, `src/teaser.py`. Implement the following components **in this exact order within that one file** — later components call functions/reference constants defined earlier.

### 2.1 Module foundations — imports, exceptions, constants

**What to implement:**

1. Module docstring + imports:

```python
"""
Family Newsletter — Teaser Card Generator
Renders teaser.png, a 1080x1350 portrait WhatsApp cover card, from one
edition's NEO object: comic-palette masthead, monthly-rotating mascot
(pose + optional topic costume), and one headline row per family member.
Hebrew RTL text shapes via a libraqm-enabled Pillow build when available,
falling back to python-bidi + arabic-reshaper (the dependably-correct
baseline — see LOD400 FNL-S001-P002-WP005 §1 Assumption 2) otherwise.
Per LOD400 FNL-S001-P002-WP005.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont, features

from .models import NEO

logger = logging.getLogger('family.teaser')
```

2. Exception hierarchy — deliberately small. Every *other* failure mode in this module degrades gracefully (§5); these two are the only conditions that abort the render entirely:

```python
class TeaserError(Exception):
    """Base class for all teaser.py errors."""


class TeaserRenderError(TeaserError):
    """Raised only for unrecoverable failures: neo is None, neo.date is
    missing/empty (there is no filename to write), or the output PNG
    could not be written to disk (wraps the underlying OSError). Every
    other defect (missing font, missing character asset, missing/short
    headline data, libraqm absent, an unrecognized hero_category, an
    oversized string) is handled by graceful degradation elsewhere in
    this module and never raises."""
```

3. Canvas geometry constants:

```python
TEASER_WIDTH = 1080
TEASER_HEIGHT = 1350
TEASER_OUTPUT_DIR_DEFAULT = "data/archive/teasers/"  # mirrors
    # m4_renderer.save_html()'s data/archive/html/ convention — §1 Assumption 4

CARD_BOX = (40, 40, 1040, 1310)      # (x0, y0, x1, y1) — outer white card
CARD_RADIUS = 48
CARD_BORDER_WIDTH = 8
CARD_SHADOW_OFFSET = 14              # flat offset shadow, zero blur —
    # same technique as templates/newsletter.html.j2's `box-shadow: 6px 6px 0`

MASTHEAD_BOX = (48, 48, 1032, 400)   # inset CARD_BORDER_WIDTH inside CARD_BOX
                                       # so the card's outer border (drawn
                                       # LAST, §2.8) is never painted over
MASTHEAD_RADIUS = CARD_RADIUS - CARD_BORDER_WIDTH  # 40 — nests inside CARD_RADIUS

MASCOT_ZONE_BOX = (40, 420, 1040, 700)
MASCOT_IMG_BOX = (96, 430, 336, 670)         # 240x240, left-aligned
GREETING_BUBBLE_WITH_MASCOT = (372, 430, 984, 670)   # 612x240
GREETING_BUBBLE_NO_MASCOT = (96, 430, 984, 670)      # 888x240, full width

CONTENT_LEFT = 96
CONTENT_RIGHT = 984

ROWS_TOP = 720
ROW_HEIGHT = 88
ROW_STEP = 104           # ROW_HEIGHT + 16px gap
ROW_COUNT = 5
ROW_RADIUS = 20
ROW_DOT_RADIUS = 18
ROW_DOT_MARGIN_RIGHT = 944   # dot CENTER x — rightmost, RTL leading edge
ROW_TEXT_RIGHT = 916         # text right edge, anchor='rm' — 12px left of the dot's left edge

FOOTER_LINE1_Y = 1258
FOOTER_LINE2_Y = 1286
```

4. Color palette — **hex values ground-truthed by directly reading `templates/newsletter.html.j2`'s `:root` block (lines 9–24) and its `{% set member_bg %}` line (line 491), corroborated by `STYLE_GUIDE.md §8`'s member table**:

```python
COLOR_BG = "#fdf6e3"
COLOR_INK = "#2c2c2c"
COLOR_HALFTONE = "#e8dcc8"
COLOR_WHITE = "#ffffff"
COLOR_YELLOW = "#f39c12"
COLOR_RED = "#c0392b"
COLOR_ORANGE_MID = "#e74c3c"   # the CSS gradient's 50% stop color
COLOR_ORANGE = "#e67e22"
COLOR_FOOTER_GREY = "#999999"
COLOR_FOOTER_GREY_LIGHT = "#bbbbbb"

HALFTONE_SPACING = 24   # px grid pitch on the 1080x1350 canvas (CSS reference:
HALFTONE_RADIUS = 2     # `radial-gradient(circle,#e8dcc8 1px,transparent 1px) 16px 16px`
                         # — scaled up for the larger raster canvas, not a literal 1:1 port)

MASTHEAD_GRADIENT_STOPS = [
    (0.0, (192, 57, 43)),    # COLOR_RED
    (0.5, (231, 76, 60)),    # COLOR_ORANGE_MID
    (1.0, (230, 126, 34)),   # COLOR_ORANGE
]  # matches `linear-gradient(135deg, var(--red) 0%, #e74c3c 50%, var(--orange) 100%)`
   # exactly (template line 48) — approximated as a top-left -> bottom-right
   # diagonal (§2.5), not a literal 135deg CSS-angle port.

MASTHEAD_TITLE_EN = "Family Newsletter!"   # verbatim from template line 498
```

5. **Member SSOT table** — per §1 Assumption 6, transcribed verbatim from `STYLE_GUIDE.md §8`'s "source of truth" table (primary color/emoji/name) plus `templates/newsletter.html.j2` line 491 (light tint):

```python
MEMBER_ORDER = ["nimrod", "michal", "shaked", "maayan", "tzlil"]

MEMBER_NAMES_HE = {
    "nimrod": "נימרוד", "michal": "מיכל", "shaked": "שקד",
    "maayan": "יויו", "tzlil": "צליל",
}

MEMBER_COLORS = {   # primary hex — STYLE_GUIDE.md §8
    "nimrod": "#2471a3", "michal": "#27ae60", "shaked": "#7d3c98",
    "maayan": "#c0392b", "tzlil": "#e67e22",
}

MEMBER_BG = {   # light tint hex — templates/newsletter.html.j2 line 491
    "nimrod": "#e6f0fa", "michal": "#e6f5ed", "shaked": "#ece6f5",
    "maayan": "#fce8ec", "tzlil": "#fef3e2",
}

MEMBER_EMOJI = {   # STYLE_GUIDE.md §8 — reference/documentation only.
    "nimrod": "⛵", "michal": "🌿", "shaked": "⚗️",   # NEVER rendered as
    "maayan": "🎪", "tzlil": "🧮",                    # Pillow text glyphs
}                                                       # — see §1 Assumption 7.
```

6. **Font vendoring constants** (files fetched by §3's setup step, not shipped with this WP):

```python
FONT_DIR_DEFAULT = "assets/fonts/"

FONT_FILES = {
    "bangers": "Bangers-Regular.ttf",           # English wordmark only
    "rubik_regular": "Rubik-Regular.ttf",       # Hebrew body/footer text
    "rubik_bold": "Rubik-Bold.ttf",             # Hebrew emphasized labels
    "secular_one": "SecularOne-Regular.ttf",    # Hebrew display/headline text
}


def _font_path(fonts_dir: str, key: str) -> str:
    """key must be one of FONT_FILES' keys. Raises KeyError for an unknown
    key (a programmer error inside this module, not a runtime/data
    condition) — never called with anything but a literal constant."""
    return str(Path(fonts_dir) / FONT_FILES[key])
```

7. **Topic → scene → character → decoration lookup table** — transcribed from `SVG_MODULE_SPEC.md §4`'s Hebrew table (10 rows, verbatim content, English keys for code use). Drives the mascot's optional costumed variant (§2.6). `member_id` is carried for documentation/traceability to the source table only; it is **not** read by any selection logic in this WP (the costume always applies to *this month's* mascot character, never swaps to a different character — see §2.6):

```python
TOPIC_LOOKUP = {
    "sailing":      {"scene": "sea, horizon, waves",       "member_id": "nimrod", "decorations": "sails, seabirds"},
    "kite":         {"scene": "beach, wind",                "member_id": "nimrod", "decorations": "waves, sun, wind"},
    "architecture": {"scene": "natural home, nature",       "member_id": "michal", "decorations": "leaves, tree, window"},
    "capoeira":     {"scene": "roda circle",                "member_id": "michal", "decorations": "berimbau, pandeiro"},
    "circus":       {"scene": "circus tent, stage",         "member_id": "maayan", "decorations": "stars, spotlight"},
    "chemistry":    {"scene": "lab",                        "member_id": "shaked", "decorations": "molecules, atoms"},
    "math":         {"scene": "chalkboard, formulas",       "member_id": "tzlil",  "decorations": "numbers, symbols"},
    "family":       {"scene": "living room, garden",        "member_id": None,     "decorations": "board games, food"},
    "gardening":    {"scene": "garden, vegetables",         "member_id": "nimrod", "decorations": "plants, butterflies"},
    "books":        {"scene": "library, bookshelf",         "member_id": None,     "decorations": "open books"},
}
```

8. **Reference-only documentation constant** — the 5-member character brief from `SVG_MODULE_SPEC.md §3.3`, plus its art-direction one-liner. Not consumed by any code path in this WP (there is no character-art *generation* here — see §6); included so whoever produces the actual PNG assets (a separate, non-code effort) has the brief in the one file that defines how those assets get selected and placed:

```python
# Character art-direction brief (SVG_MODULE_SPEC.md §3.3, §5) — for the
# artist/asset producer, not consumed by any function in this module.
CHARACTER_ART_DIRECTION = (
    "editorial illustration meets comic strip: flat colors, 2-3px bold "
    "outlines, rounded forms, minimal halftone texture, no photorealism, "
    "no 3D, no complex shadows. \"Quentin Blake meets Herge.\""
)
CHARACTER_BRIEFS_HE = {
    "nimrod": "גבר עם זקן קצר, כובע סקיפר — הגה ספינה / עפיפון קייט / לפטופ",
    "michal": "אישה עם שיער חום ארוך, בגדי עבודה — סרגל T / עציץ / ברימבאו",
    "shaked": "נער גבוה, שיער בהיר, אוזניות — ספר / מבחנה / Switch",
    "maayan": "נערה אנרגטית, שיער אסוף, בגדי ספורט — חישוק אוויר / טרפז / אינסטגרם",
    "tzlil":  "ילדה עם משקפיים, שיער חום, חיוך חכם — מספרים/חידות / תנור / VR",
}
```

**Acceptance criteria:**
- [ ] AC-01: `from src import teaser` (or `import src.teaser as teaser`) succeeds with no import-time errors and performs no file I/O, no network call, and no `PIL.features.check(...)` call at import time (detection happens lazily inside `generate_teaser()`, §2.8 — see AC-38).
- [ ] AC-02: `TeaserError` is defined at module level; `TeaserRenderError` subclasses `TeaserError`.
- [ ] AC-03: `MEMBER_ORDER == ["nimrod", "michal", "shaked", "maayan", "tzlil"]`; `MEMBER_NAMES_HE`, `MEMBER_COLORS`, `MEMBER_BG`, `MEMBER_EMOJI` each have exactly these 5 keys, no more, no fewer.
- [ ] AC-04: `TOPIC_LOOKUP` has exactly 10 keys; every value is a `dict` containing the keys `"scene"`, `"member_id"`, `"decorations"`.
- [ ] AC-05: `TEASER_WIDTH == 1080` and `TEASER_HEIGHT == 1350`.

### 2.2 Font loading + libraqm detection

**What to implement:**

```python
def _raqm_available() -> bool:
    """Detects libraqm support. MUST be called (and its result threaded
    through as raqm_available) before ANY draw.text()/draw.textbbox() call
    is allowed to pass direction=/language=/features= — Pillow raises
    "setting text direction, language or font features is not supported
    without libraqm" if those kwargs are passed without it (confirmed
    against Pillow's own issue tracker while researching this spec). Never
    assume raqm is present on either the Mac (dev/build) or waldhomeserver
    (Linux, runtime) host — see §1 Assumption 2. PIL.features.check(feature)
    is Pillow's documented general-purpose feature-detection entry point
    (PIL.features.check_feature("raqm") is an equivalent, lower-level
    alternative that raises ValueError for an unregistered feature name;
    check() never raises for an unknown name, returning False/None
    instead, which is the safer choice here)."""
    try:
        return bool(features.check("raqm"))
    except Exception as e:
        logger.warning(f"[teaser] PIL.features.check('raqm') raised {e!r}; "
                        f"assuming raqm is NOT available.")
        return False


def _load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    """Loads a TrueType font at the given pixel size. NEVER raises — falls
    back to Pillow's built-in bitmap font (no Hebrew glyph coverage, but
    always renders SOMETHING) if font_path is missing or fails to load.
    A missing font file is a setup/install defect (§3), not an expected
    runtime condition, so the fallback always logs a warning."""
    try:
        return ImageFont.truetype(font_path, size)
    except (OSError, IOError) as e:
        logger.warning(
            f"[teaser] Failed to load font '{font_path}' at size {size}: "
            f"{e!r}. Falling back to Pillow's built-in default font "
            f"(Hebrew text will not render correctly with this fallback; "
            f"see §3 for the required font-vendoring setup step)."
        )
        try:
            return ImageFont.load_default(size=size)   # Pillow >= 10.1.0
        except TypeError:
            return ImageFont.load_default()   # older Pillow: no size kwarg
```

**Acceptance criteria:**
- [ ] AC-06: With a fake `PIL.features.check` mocked to return `True`, `_raqm_available()` returns `True`. Mocked to return `False`, returns `False`. Mocked to raise an arbitrary `Exception`, `_raqm_available()` returns `False` (never raises) and a `logger.warning` call is observed.
- [ ] AC-07: `_load_font("<a real, valid .ttf path in a tmp dir>", 40)` returns an `ImageFont.FreeTypeFont` instance (not the fallback), with no warning logged.
- [ ] AC-08: `_load_font("/definitely/does/not/exist.ttf", 40)` does not raise, returns a usable font object (an object with a `.getbbox`-compatible interface — concretely, `ImageDraw.textbbox` can be called with it without raising), and exactly one `logger.warning` call is observed.
- [ ] AC-09: If `ImageFont.load_default` is mocked to raise `TypeError` when called with `size=40` but succeed when called with no arguments, `_load_font` for a missing path still returns successfully (exercises the `except TypeError` fallback branch).

### 2.3 RTL text engine — shaping, drawing, measuring, fitting, wrapping

**What to implement:**

```python
def _bidi_shape(text: str) -> str:
    """Fallback-path text shaping (used only when raqm is unavailable).
    arabic_reshaper.reshape() is a defensive no-op on pure Hebrew text —
    it only transforms Arabic-block codepoints (Hebrew has no positional
    letterforms, unlike Arabic) — included per this WP's brief for
    robustness against mixed Hebrew/Arabic content. get_display() performs
    the actual visual-order RTL reordering Hebrew needs (transforms
    logical-order "שלום" into visual-order "םולש"). The returned string
    must be drawn WITHOUT direction=/language= kwargs — see
    _draw_rtl_text below; passing both the bidi-reordered string AND
    direction='rtl' would double-transform the text."""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def _draw_rtl_text(draw: ImageDraw.ImageDraw, xy: tuple, text: str,
                    font: ImageFont.FreeTypeFont, fill: str,
                    raqm_available: bool, anchor: str = "mm") -> None:
    """THE single place Hebrew/mixed-RTL text is drawn in this module —
    every other drawing function calls this, never draw.text() directly,
    for Hebrew content. When raqm is available: draws the raw
    logical-order string with direction='rtl', language='he' — Pillow/raqm
    perform shaping AND reordering internally. When unavailable: pre-shapes
    via _bidi_shape() into a visual-order string and draws it with NO
    direction/language/features kwargs (passing them without raqm raises —
    see _raqm_available's docstring). `anchor` behaves identically on both
    paths, since it operates on the final rendered glyph-run's bounding
    box regardless of the internal shaping direction used to produce it."""
    if raqm_available:
        draw.text(xy, text, fill=fill, font=font, anchor=anchor,
                   direction="rtl", language="he")
    else:
        draw.text(xy, _bidi_shape(text), fill=fill, font=font, anchor=anchor)


def _measure_rtl_text(draw: ImageDraw.ImageDraw, text: str,
                       font: ImageFont.FreeTypeFont,
                       raqm_available: bool) -> tuple:
    """Returns (width, height) in pixels for `text` as it would actually
    be drawn by _draw_rtl_text with the same raqm_available value — the
    measurement path MUST mirror the draw path exactly (same shaping
    decision) or fit/wrap calculations would silently disagree with what
    gets rendered."""
    if raqm_available:
        bbox = draw.textbbox((0, 0), text, font=font, direction="rtl", language="he")
    else:
        bbox = draw.textbbox((0, 0), _bidi_shape(text), font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font_path: str,
              max_width: int, start_size: int, min_size: int,
              raqm_available: bool) -> tuple:
    """'Oversized text' handling. Shrinks font size in 2px steps from
    start_size down to min_size until the shaped text's measured width
    fits max_width. If STILL too wide at min_size, truncates the text one
    character at a time from the end (keeping a trailing '…', re-measured
    after every cut) until it fits. Never raises. An empty-string input
    returns ("", <font at min_size>). Returns (text_to_draw, loaded_font)."""
    size = start_size
    font = _load_font(font_path, size)
    if not text:
        return "", _load_font(font_path, min_size)
    while size > min_size:
        w, _h = _measure_rtl_text(draw, text, font, raqm_available)
        if w <= max_width:
            return text, font
        size -= 2
        font = _load_font(font_path, size)

    working = text
    while working:
        candidate = working + "…"
        w, _h = _measure_rtl_text(draw, candidate, font, raqm_available)
        if w <= max_width or len(working) <= 1:
            return candidate, font
        working = working[:-1].rstrip()
    return "…", font


def _wrap_text(draw: ImageDraw.ImageDraw, text: str,
               font: ImageFont.FreeTypeFont, max_width: int,
               raqm_available: bool, max_lines: int) -> list:
    """Greedy word-wrap into at most max_lines lines, each <= max_width.
    If words remain unconsumed after max_lines lines are filled, the last
    line is shortened (character-by-character) and a trailing '…' is
    appended. Never raises; an empty string returns []."""
    words = text.split()
    if not words:
        return []

    lines = []
    current = ""
    i = 0
    while i < len(words):
        word = words[i]
        trial = (current + " " + word).strip()
        w, _h = _measure_rtl_text(draw, trial, font, raqm_available)
        if w <= max_width or not current:
            current = trial
            i += 1
        else:
            lines.append(current)
            current = ""
            if len(lines) == max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
        i = len(words)

    if i < len(words) or len(lines) > max_lines:
        lines = lines[:max_lines] if lines else [""]
        last = lines[-1]
        while last:
            w, _h = _measure_rtl_text(draw, last + "…", font, raqm_available)
            if w <= max_width:
                break
            last = last[:-1].rstrip()
        lines[-1] = (last + "…") if last else "…"
    return lines
```

**Acceptance criteria:**
- [ ] AC-10: `_bidi_shape("שלום")` returns a string with the characters in reverse order relative to `"שלום"` (visual-order reordering occurred) and does not raise.
- [ ] AC-11: `_bidi_shape("שלום world 123")` does not raise (mixed Hebrew/Latin/digit content — confirms the bidi algorithm's mixed-run handling is exercised without error).
- [ ] AC-12: With `raqm_available=True`, `_draw_rtl_text(...)` is verified (via a mocked `draw.text`) to be called with `direction="rtl", language="he"` and the ORIGINAL (non-bidi-shaped) text string. With `raqm_available=False`, verified to be called with neither `direction` nor `language` kwargs present at all, and the text argument equal to `_bidi_shape(original_text)`.
- [ ] AC-13: `_measure_rtl_text` and `_draw_rtl_text`, given the same `raqm_available` value and the same text/font, are shown (by construction/code inspection at review time, and by AC-12's mock assertions) to make the identical shaping decision — no code path exists where one uses raqm and the other doesn't for the same call.
- [ ] AC-14: `_fit_text(draw, "short", font_path, max_width=10000, start_size=30, min_size=16, raqm_available=False)` returns the text unchanged at `start_size` (fits immediately, no shrinking needed).
- [ ] AC-15: `_fit_text` with a `max_width` too narrow for the text even at `min_size` returns a string ending in `"…"` that is `<= max_width` when measured (or, if even a single character + ellipsis cannot fit, returns exactly `"…"`), and never raises.
- [ ] AC-16: `_fit_text(draw, "", font_path, max_width=500, start_size=30, min_size=16, raqm_available=False)` returns `("", <font>)` without raising or entering the shrink/truncate loops.
- [ ] AC-17: `_wrap_text` given text that fits entirely on one line returns a single-element list equal to the input's whitespace-normalized form.
- [ ] AC-18: `_wrap_text` given text long enough to need exactly 2 of `max_lines=3` returns a 2-element list, neither line exceeding `max_width` when measured, and neither line ending in `"…"` (nothing was dropped).
- [ ] AC-19: `_wrap_text` given text long enough to overflow `max_lines=3` returns exactly 3 elements, the last ending in `"…"`, and no element exceeding `max_width` when measured.
- [ ] AC-20: `_wrap_text(draw, "", font, 500, False, 3)` returns `[]`.

### 2.4 Halftone texture + rounded-corner masking primitives

**What to implement:**

```python
def _draw_halftone(img: Image.Image, box: tuple,
                    spacing: int = HALFTONE_SPACING,
                    radius: int = HALFTONE_RADIUS,
                    color: str = COLOR_HALFTONE) -> None:
    """Draws a flat grid of small filled dots across the given (x0,y0,x1,y1)
    box on img, in place. Raster equivalent of the template's CSS
    `radial-gradient(circle,#e8dcc8 1px,transparent 1px) 16px 16px` page
    texture (templates/newsletter.html.j2 lines 32-33) — same visual
    grammar, new pixel values for the larger canvas (§1's framing note)."""
    draw = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    y = y0
    while y < y1:
        x = x0
        while x < x1:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
            x += spacing
        y += spacing


def _rounded_mask(size: tuple, radius: int,
                   corners: tuple = (True, True, True, True)) -> Image.Image:
    """Returns a single-channel 'L' mode mask (255=opaque, 0=transparent)
    with rounded corners per `corners` = (top_left, top_right, bottom_right,
    bottom_left) — identical order/semantics to
    ImageDraw.rounded_rectangle's own `corners` parameter. Used to paste a
    rectangular source image (e.g. the masthead gradient band) onto the
    canvas so only some corners appear rounded (§2.5)."""
    mask = Image.new("L", size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius,
                             fill=255, corners=corners)
    return mask
```

**Acceptance criteria:**
- [ ] AC-21: `_draw_halftone(img, (0, 0, 100, 100), spacing=24, radius=2)` produces at least one non-background-colored pixel in the target `img` (confirms dots were actually drawn, not a no-op).
- [ ] AC-22: `_rounded_mask((200, 100), radius=20, corners=(True, True, False, False))` returns an `"L"`-mode image of size `(200, 100)` whose pixel at `(0, 0)` (extreme top-left corner) is `0` (masked out, rounded) and whose pixel at `(0, 99)` (extreme bottom-left corner) is `255` (opaque, square — `bottom_left=False` means NOT rounded).

### 2.5 Diagonal gradient + candy-stripe overlay + masthead band

**What to implement:**

```python
def _lerp_color(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient_color_at(t: float, stops: list) -> tuple:
    """stops: list of (position 0..1, (r,g,b)) sorted ascending by
    position. Returns the linearly-interpolated RGB color at t, clamped
    to the first/last stop's color outside [0,1]."""
    if t <= stops[0][0]:
        return stops[0][1]
    if t >= stops[-1][0]:
        return stops[-1][1]
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if p0 <= t <= p1:
            local_t = (t - p0) / (p1 - p0) if p1 > p0 else 0.0
            return _lerp_color(c0, c1, local_t)
    return stops[-1][1]


def _diagonal_gradient(width: int, height: int, stops: list) -> Image.Image:
    """Top-left -> bottom-right diagonal gradient, approximating the CSS
    `linear-gradient(135deg, ...)` used by templates/newsletter.html.j2's
    .cover-top (line 48). Runs once per build (not perf-sensitive for a
    weekly cron job)."""
    img = Image.new("RGB", (width, height))
    max_t = max(width + height - 2, 1)
    pixels = [None] * (width * height)
    for y in range(height):
        row_base = y * width
        for x in range(width):
            t = (x + y) / max_t
            pixels[row_base + x] = _gradient_color_at(t, stops)
    img.putdata(pixels)
    return img


def _add_candy_stripe(band_img: Image.Image, opacity: int = 20,
                       stripe_width: int = 10, period: int = 20) -> None:
    """Overlays a diagonal repeating low-opacity white stripe pattern onto
    band_img IN PLACE. Approximates
    `repeating-linear-gradient(-45deg, transparent, transparent 10px,
    rgba(255,255,255,0.08) 10px, rgba(255,255,255,0.08) 20px)` (template
    line 52; 0.08 * 255 ~= 20, matching the default opacity here)."""
    w, h = band_img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    diag = w + h
    x = -h
    while x < diag:
        odraw.line([(x, 0), (x + h, h)], fill=(255, 255, 255, opacity), width=stripe_width)
        x += period
    band_img.paste(overlay, (0, 0), overlay)


def _draw_masthead(img: Image.Image, draw: ImageDraw.ImageDraw, neo: NEO,
                    edition_number: Optional[int], raqm_available: bool,
                    fonts_dir: str) -> None:
    """Draws the gradient band (rounded top corners only, via a
    _rounded_mask paste), the candy-stripe overlay, the English wordmark,
    the Hebrew family-name subtitle, and the edition badge pill — all
    within MASTHEAD_BOX. Copy conventions verbatim from
    templates/newsletter.html.j2 lines 498-500."""
    band_w = MASTHEAD_BOX[2] - MASTHEAD_BOX[0]
    band_h = MASTHEAD_BOX[3] - MASTHEAD_BOX[1]
    band_img = _diagonal_gradient(band_w, band_h, MASTHEAD_GRADIENT_STOPS)
    _add_candy_stripe(band_img)
    mask = _rounded_mask((band_w, band_h), MASTHEAD_RADIUS, corners=(True, True, False, False))
    img.paste(band_img, (MASTHEAD_BOX[0], MASTHEAD_BOX[1]), mask)

    cx = (MASTHEAD_BOX[0] + MASTHEAD_BOX[2]) // 2   # 540

    # English wordmark — Bangers, hard ink shadow offset, matching the
    # template's `text-shadow: 3px 3px 0 var(--ink), -1px -1px 0 var(--ink)`
    # (approximated here as one offset copy — see AC-25).
    wordmark_font_path = _font_path(fonts_dir, "bangers")
    wordmark_text, wordmark_font = _fit_text(
        draw, MASTHEAD_TITLE_EN, wordmark_font_path,
        max_width=band_w - 80, start_size=84, min_size=48, raqm_available=False,
    )
    shadow_xy = (cx + 4, 130 + 4)
    draw.text(shadow_xy, wordmark_text, fill=COLOR_INK, font=wordmark_font, anchor="mm")
    draw.text((cx, 130), wordmark_text, fill=COLOR_WHITE, font=wordmark_font, anchor="mm")

    # Hebrew subtitle — neo.family_name, falling back to the literal
    # brand name if empty (STYLE_GUIDE.md §1: "בית ולד").
    family_name = getattr(neo, "family_name", None) or "בית ולד"
    subtitle_text, subtitle_font = _fit_text(
        draw, family_name, _font_path(fonts_dir, "secular_one"),
        max_width=band_w - 120, start_size=40, min_size=26, raqm_available=raqm_available,
    )
    _draw_rtl_text(draw, (cx, 215), subtitle_text, subtitle_font, COLOR_WHITE, raqm_available)

    # Edition badge — "{date_formatted or date} • #{edition_number or 1}",
    # verbatim format from template line 500.
    date_str = getattr(neo, "date_formatted", None) or getattr(neo, "date", "") or ""
    edition_str = str(edition_number) if edition_number else "1"
    badge_text = f"{date_str} • #{edition_str}"
    badge_text, badge_font = _fit_text(
        draw, badge_text, _font_path(fonts_dir, "rubik_bold"),
        max_width=320, start_size=26, min_size=18, raqm_available=raqm_available,
    )
    badge_box = (cx - 180, 288, cx + 180, 352)
    draw.rounded_rectangle(badge_box, radius=32, fill=COLOR_YELLOW, outline=COLOR_INK, width=3)
    _draw_rtl_text(draw, (cx, 320), badge_text, badge_font, COLOR_INK, raqm_available)
```

**Acceptance criteria:**
- [ ] AC-23: `_gradient_color_at(0.0, MASTHEAD_GRADIENT_STOPS) == (192, 57, 43)`; `_gradient_color_at(1.0, MASTHEAD_GRADIENT_STOPS) == (230, 126, 34)`; `_gradient_color_at(0.5, MASTHEAD_GRADIENT_STOPS) == (231, 76, 60)` (exact stop values, no interpolation error at exact stop positions).
- [ ] AC-24: `_diagonal_gradient(100, 50, MASTHEAD_GRADIENT_STOPS)` returns an `Image` of size `(100, 50)` whose pixel at `(0, 0)` equals `MASTHEAD_GRADIENT_STOPS[0][1]` and whose pixel at `(99, 49)` equals `MASTHEAD_GRADIENT_STOPS[-1][1]` (the two extreme corners match the first/last stop exactly).
- [ ] AC-25: `_add_candy_stripe` mutates `band_img` in place — a pixel-difference check between a copy of `band_img` taken before the call and `band_img` after the call shows at least one changed pixel.
- [ ] AC-26: `_draw_masthead(...)` called with a `neo` whose `family_name` is `""` (falsy) draws the literal fallback string `"בית ולד"` (verified via a mocked `_draw_rtl_text`/`draw.text` call inspecting its text argument after bidi-shaping, or via `_bidi_shape("בית ולד")` appearing in the call for the non-raqm path).
- [ ] AC-27: `_draw_masthead(...)` called with `edition_number=None` produces a badge string containing `"#1"`; called with `edition_number=7` produces a badge string containing `"#7"`.

### 2.6 Character/mascot asset resolution + placement

**What to implement:**

```python
CHARACTER_ASSETS_DIR_DEFAULT = "assets/characters/"
MASCOT_POSE = "hero-greeting"   # fixed for this WP — the teaser is
    # fundamentally a greeting/cover artifact. Matches the existing pose
    # vocabulary already used by src/m4_renderer.py's POSE_EMOJI_MAP and
    # STYLE_GUIDE.md's assets/characters/{YYYY-MM}/{pose}.png convention
    # (this WP does not import m4_renderer.py — see §1 Assumption 9 — but
    # deliberately reuses its exact pose-key spelling for asset-scheme
    # compatibility).


def _resolve_character_asset(assets_dir: str, month: str, pose: str,
                              hero_category: Optional[str]) -> Optional[Path]:
    """Resolves the character PNG to place on the card, in strict priority
    order, returning the first that exists on disk:
      1. assets/characters/{month}/{pose}__{hero_category}.png  (costumed
         variant for this edition's topic, if hero_category was given)
      2. assets/characters/{month}/{pose}.png                   (this
         month's base pose — existing convention, STYLE_GUIDE.md §1)
      3. assets/characters/_placeholder/{pose}.png               (generic
         fallback used when the current month has no dedicated art yet)
      4. None (caller must handle: skip drawing a mascot entirely — §5)
    An unrecognized hero_category (not a TOPIC_LOOKUP key) is logged and
    treated identically to hero_category=None (tier 1 is simply skipped) —
    never an error."""
    if hero_category and hero_category not in TOPIC_LOOKUP:
        logger.warning(f"[teaser] Unrecognized hero_category '{hero_category}' "
                        f"(not in TOPIC_LOOKUP) — ignoring, no costume applied.")
        hero_category = None

    candidates = []
    if hero_category:
        candidates.append(Path(assets_dir) / month / f"{pose}__{hero_category}.png")
    candidates.append(Path(assets_dir) / month / f"{pose}.png")
    candidates.append(Path(assets_dir) / "_placeholder" / f"{pose}.png")

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    logger.warning(f"[teaser] No character asset found for pose='{pose}' "
                    f"month='{month}' hero_category='{hero_category}' "
                    f"(checked {[str(c) for c in candidates]}) — "
                    f"rendering without a mascot image.")
    return None


def _draw_mascot_and_greeting(img: Image.Image, draw: ImageDraw.ImageDraw,
                               neo: NEO, assets_dir: str,
                               hero_category: Optional[str],
                               raqm_available: bool, fonts_dir: str) -> None:
    """Places the mascot PNG (if resolved) at MASCOT_IMG_BOX, and a
    greeting speech bubble (neo.greeting, word-wrapped up to 3 lines) at
    GREETING_BUBBLE_WITH_MASCOT — or, if no mascot asset was found, an
    expanded bubble at GREETING_BUBBLE_NO_MASCOT covering the full content
    width. neo.greeting missing/empty is handled gracefully: the bubble is
    simply not drawn (masthead + rows still render a complete card)."""
    month = datetime.now().strftime('%Y-%m')
    asset_path = _resolve_character_asset(assets_dir, month, MASCOT_POSE, hero_category)

    if asset_path is not None:
        try:
            mascot_img = Image.open(asset_path).convert("RGBA")
            mw = MASCOT_IMG_BOX[2] - MASCOT_IMG_BOX[0]
            mh = MASCOT_IMG_BOX[3] - MASCOT_IMG_BOX[1]
            mascot_img = mascot_img.resize((mw, mh), Image.LANCZOS)
            img.paste(mascot_img, (MASCOT_IMG_BOX[0], MASCOT_IMG_BOX[1]), mascot_img)
            bubble_box = GREETING_BUBBLE_WITH_MASCOT
        except Exception as e:
            logger.warning(f"[teaser] Failed to load/place character asset "
                            f"'{asset_path}': {e!r} — rendering without a mascot image.")
            bubble_box = GREETING_BUBBLE_NO_MASCOT
    else:
        bubble_box = GREETING_BUBBLE_NO_MASCOT

    greeting = (getattr(neo, "greeting", None) or "").strip()
    if not greeting:
        logger.info("[teaser] neo.greeting is empty — skipping greeting bubble.")
        return

    draw.rounded_rectangle(bubble_box, radius=28, fill=COLOR_WHITE,
                            outline=COLOR_INK, width=3)
    bubble_font = _load_font(_font_path(fonts_dir, "secular_one"), 30)
    inner_w = (bubble_box[2] - bubble_box[0]) - 48
    lines = _wrap_text(draw, greeting, bubble_font, inner_w, raqm_available, max_lines=3)
    line_h = 40
    start_y = (bubble_box[1] + bubble_box[3]) // 2 - (len(lines) - 1) * line_h // 2
    text_right_x = bubble_box[2] - 24
    for i, line in enumerate(lines):
        _draw_rtl_text(draw, (text_right_x, start_y + i * line_h), line,
                        bubble_font, COLOR_INK, raqm_available, anchor="rm")
```

**Acceptance criteria:**
- [ ] AC-28: `_resolve_character_asset` given a temp `assets_dir` where ONLY `{month}/{pose}__foo.png` exists (and `hero_category="foo"`, a key temporarily added to a test double or monkeypatched into `TOPIC_LOOKUP`) returns that exact path — tier 1 wins over lower tiers when present.
- [ ] AC-29: Given a temp `assets_dir` where `{month}/{pose}__foo.png` does NOT exist but `{month}/{pose}.png` does, with `hero_category="foo"`, returns the tier-2 path.
- [ ] AC-30: Given a temp `assets_dir` where only `_placeholder/{pose}.png` exists, returns that tier-3 path.
- [ ] AC-31: Given a temp `assets_dir` with none of the three files present, returns `None` and a `logger.warning` call is observed.
- [ ] AC-32: `hero_category="not_a_real_topic"` (not a `TOPIC_LOOKUP` key) causes `_resolve_character_asset` to behave identically to `hero_category=None` (tier-1 lookup is skipped entirely — verified by confirming the tier-1 candidate path is never checked/never appears in the log's "checked" list) and logs a warning distinct from the "no asset found at all" warning.
- [ ] AC-33: `_draw_mascot_and_greeting` with `neo.greeting = ""` returns without drawing any bubble (verified via a mocked `draw.rounded_rectangle` asserted never called for the bubble) regardless of whether a mascot asset was found.
- [ ] AC-34: `_draw_mascot_and_greeting` with a mascot asset resolved successfully draws the bubble at `GREETING_BUBBLE_WITH_MASCOT`'s coordinates; with no asset resolved (or asset load raising inside the `try`), draws it at `GREETING_BUBBLE_NO_MASCOT`'s coordinates instead (verified via the `rounded_rectangle` call's `xy` argument in each case).

### 2.7 Member headline rows

**What to implement:**

```python
def _member_headline(neo: NEO, member_id: str) -> str:
    """Reads this member's single teaser headline from neo.member_sections
    per §1 Assumption 1's documented, defensive, multi-tier contract:
      1. Find the dict in neo.member_sections whose "member_id" matches.
      2. Take items[0] (first/highest-priority item) from its "items" list.
      3. Read "headline" from that item; if absent/empty, fall back to
         "title" (NCI's raw-article-title field name).
      4. If neo.member_sections is missing/empty/malformed, no dict
         matches this member_id, "items" is missing/empty, or neither
         "headline" nor "title" is present/non-empty — return a neutral
         placeholder. NEVER raises, and NEVER omits a member (LOD200 §2's
         hard rule: every member appears, even with a placeholder)."""
    sections = getattr(neo, "member_sections", None) or []
    for section in sections:
        if not isinstance(section, dict) or section.get("member_id") != member_id:
            continue
        items = section.get("items") or []
        if not items or not isinstance(items[0], dict):
            break
        item = items[0]
        headline = (item.get("headline") or "").strip()
        if headline:
            return headline
        title = (item.get("title") or "").strip()
        if title:
            return title
        break
    return "עוד השבוע..."   # neutral placeholder — "more this week..."


def _draw_member_rows(draw: ImageDraw.ImageDraw, neo: NEO,
                       raqm_available: bool, fonts_dir: str) -> None:
    """Draws exactly ROW_COUNT (5) rows, one per MEMBER_ORDER entry, always
    — regardless of what neo.member_sections actually contains (LOD200 §2
    hard rule: every member appears)."""
    row_font_path = _font_path(fonts_dir, "secular_one")
    for i, member_id in enumerate(MEMBER_ORDER):
        row_top = ROWS_TOP + i * ROW_STEP
        row_box = (CONTENT_LEFT, row_top, CONTENT_RIGHT, row_top + ROW_HEIGHT)
        row_center_y = row_top + ROW_HEIGHT // 2

        draw.rounded_rectangle(row_box, radius=ROW_RADIUS,
                                fill=MEMBER_BG.get(member_id, "#f0f0f0"))

        dot_r = ROW_DOT_RADIUS
        dot_cx, dot_cy = ROW_DOT_MARGIN_RIGHT, row_center_y
        draw.ellipse((dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r),
                     fill=MEMBER_COLORS.get(member_id, COLOR_INK))

        name = MEMBER_NAMES_HE.get(member_id, member_id)
        headline = _member_headline(neo, member_id)
        row_text = f"{name}  —  {headline}"
        max_width = ROW_TEXT_RIGHT - CONTENT_LEFT - 14   # 14px clearance past the dot
        fitted_text, fitted_font = _fit_text(
            draw, row_text, row_font_path, max_width=max_width,
            start_size=30, min_size=18, raqm_available=raqm_available,
        )
        _draw_rtl_text(draw, (ROW_TEXT_RIGHT, row_center_y), fitted_text,
                        fitted_font, COLOR_INK, raqm_available, anchor="rm")
```

**Acceptance criteria:**
- [ ] AC-35: `_member_headline(neo, "tzlil")` given `neo.member_sections = [{"member_id": "tzlil", "items": [{"headline": "H", "title": "T"}]}]` returns `"H"` (headline preferred over title).
- [ ] AC-36: Same shape but `items[0] = {"title": "T"}` (no `"headline"` key) returns `"T"` (fallback to title).
- [ ] AC-37: `neo.member_sections = []` (empty list), `neo.member_sections = None`, `neo.member_sections = [{"member_id": "someone_else", "items": [...]}]`, and `neo.member_sections = [{"member_id": "tzlil", "items": []}]` — all four cases return the literal placeholder `"עוד השבוע..."`, and none of them raises.
- [ ] AC-38: `_draw_member_rows(...)` always issues exactly `ROW_COUNT` (5) `rounded_rectangle` row-background calls and 5 `ellipse` dot calls, regardless of the contents/shape of `neo.member_sections` (including when it is `None` or `[]`) — member coverage never depends on upstream data being well-formed.
- [ ] AC-39: The 5 rows' `row_box` top coordinates, in `MEMBER_ORDER` iteration order, are exactly `[720, 824, 928, 1032, 1136]` (i.e. `ROWS_TOP + i * ROW_STEP` for `i in 0..4`), and no row's `y1` (`row_top + ROW_HEIGHT`) exceeds `CARD_BOX[3]` (1310).

### 2.8 Footer + public entry point — `generate_teaser()`

**What to implement:**

```python
def _draw_footer(draw: ImageDraw.ImageDraw, raqm_available: bool,
                  fonts_dir: str, edition_number: Optional[int],
                  date_str: str) -> None:
    """Two-line footer, matching templates/newsletter.html.j2's footer
    content (lines 813-817) and STYLE_GUIDE.md §1's BINDING footer
    requirement ("by AgentsOS @ nimrod.bio" must appear on every edition).
    Per §1 Assumption 7, the template's family-emoji strip
    ("⛵ 🌿 ⚗️ 🎪 🧮") is intentionally NOT reproduced here — each member
    row (§2.7) already carries that member's color-coded dot, making a
    second emoji-strip redundant, and emoji glyphs are avoided in Pillow
    text drawing entirely (§1 Assumption 7)."""
    cx = (CARD_BOX[0] + CARD_BOX[2]) // 2   # 540
    edition_str = str(edition_number) if edition_number else "1"

    line1 = f"Family Newsletter • #{edition_str} • {date_str}"
    line1_font = _load_font(_font_path(fonts_dir, "rubik_regular"), 22)
    _draw_rtl_text(draw, (cx, FOOTER_LINE1_Y), line1, line1_font,
                    COLOR_FOOTER_GREY, raqm_available, anchor="mm")

    line2 = "by AgentsOS @ nimrod.bio"   # pure Latin — draw plain, no bidi needed
    line2_font = _load_font(_font_path(fonts_dir, "rubik_regular"), 18)
    draw.text((cx, FOOTER_LINE2_Y), line2, fill=COLOR_FOOTER_GREY_LIGHT,
              font=line2_font, anchor="mm")


def generate_teaser(
    neo: NEO,
    *,
    output_dir: str = TEASER_OUTPUT_DIR_DEFAULT,
    edition_number: Optional[int] = None,
    hero_category: Optional[str] = None,
    assets_dir: str = CHARACTER_ASSETS_DIR_DEFAULT,
    fonts_dir: str = FONT_DIR_DEFAULT,
) -> str:
    """THE public entry point. Renders teaser.png (TEASER_WIDTH x
    TEASER_HEIGHT) from neo and writes it to
    <output_dir>/<neo.date>.png, auto-creating output_dir if needed
    (mirrors m4_renderer.save_html()'s exact convention/contract — §1
    Assumption 4). Returns the file path written (str), matching
    save_html()'s return contract. Pure function of (neo, options): no DB
    access, no llm.py/editor.py calls (§1 Assumption 8).

    Raises TeaserRenderError only for: neo is None, neo.date is
    missing/empty, or the PNG could not be written to disk. Every other
    defect (missing font, missing character asset, libraqm absent,
    unrecognized hero_category, missing/oversized headline text) degrades
    gracefully — see §5 — and never raises."""
    if neo is None:
        raise TeaserRenderError("generate_teaser(): neo must not be None")
    if not getattr(neo, "date", None):
        raise TeaserRenderError(
            "generate_teaser(): neo.date is required to name the output file"
        )

    raqm_ok = _raqm_available()
    logger.info(f"[teaser] libraqm available: {raqm_ok}")

    img = Image.new("RGB", (TEASER_WIDTH, TEASER_HEIGHT), COLOR_BG)
    _draw_halftone(img, (0, 0, TEASER_WIDTH, TEASER_HEIGHT))
    draw = ImageDraw.Draw(img)

    shadow_box = tuple(c + CARD_SHADOW_OFFSET for c in CARD_BOX)
    draw.rounded_rectangle(shadow_box, radius=CARD_RADIUS, fill=COLOR_INK)
    draw.rounded_rectangle(CARD_BOX, radius=CARD_RADIUS, fill=COLOR_WHITE)

    _draw_masthead(img, draw, neo, edition_number, raqm_ok, fonts_dir)
    _draw_mascot_and_greeting(img, draw, neo, assets_dir, hero_category, raqm_ok, fonts_dir)
    _draw_member_rows(draw, neo, raqm_ok, fonts_dir)

    date_str = getattr(neo, "date_formatted", None) or getattr(neo, "date", "") or ""
    _draw_footer(draw, raqm_ok, fonts_dir, edition_number, date_str)

    # Card border stroke drawn LAST, on top of everything (band, bubble,
    # rows) so it is always a clean, unbroken outline regardless of what
    # was drawn inside the card interior — see §2.1's MASTHEAD_BOX comment.
    draw.rounded_rectangle(CARD_BOX, radius=CARD_RADIUS, outline=COLOR_INK,
                            width=CARD_BORDER_WIDTH)

    out_dir = Path(output_dir)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{neo.date}.png"
        img.convert("RGB").save(out_path, "PNG", optimize=True)
    except OSError as e:
        raise TeaserRenderError(
            f"generate_teaser(): failed to write {output_dir}/{neo.date}.png: {e}"
        ) from e

    logger.info(f"[teaser] Saved teaser card: {out_path} ({TEASER_WIDTH}x{TEASER_HEIGHT})")
    return str(out_path)
```

**Acceptance criteria:**
- [ ] AC-40: `_draw_footer(...)` always draws a call whose text argument contains the exact literal substring `"by AgentsOS @ nimrod.bio"` (STYLE_GUIDE.md §1's binding requirement) — verified via a mocked `draw.text`.
- [ ] AC-41: `generate_teaser(None)` raises `TeaserRenderError`. A `neo` with `date=""` (or `date=None`) raises `TeaserRenderError`. Neither call touches the filesystem (no directory created, no file written) — verified via a mocked `Path.mkdir`/`Image.save` asserted never called.
- [ ] AC-42: A full `generate_teaser(neo, output_dir=<tmp dir>)` call with a minimal-but-valid `neo` (real `date`, empty `member_sections`, empty `greeting`) succeeds, returns a path string ending in `f"{neo.date}.png"`, and the file at that path — opened with `PIL.Image.open` — has `.size == (1080, 1350)` and `.format == "PNG"`. This must pass even when `fonts_dir`/`assets_dir` point at empty temp directories (exercising the full missing-font + missing-mascot graceful-degradation chain end-to-end, not just its individual units).
- [ ] AC-43: `generate_teaser(...)` called twice with the same `neo`/`output_dir` overwrites the file at the same path (both calls return the identical path string; no `-1`/duplicate-suffix behavior).
- [ ] AC-44: If `Image.save` raises `OSError` (mocked, simulating e.g. a full disk), `generate_teaser()` raises `TeaserRenderError` with the underlying `OSError` chained via `from`, not a bare/uncaught `OSError`.

## 3. Data model changes (if any)

**None.** `teaser.py` performs no database access and defines no new dataclass or schema (§1 Assumption 8). `src/models.py` is not edited by this WP.

### Installs & dependencies (per task brief — this WP's `requirements.txt` / setup changes)

**None of the following are installed in this repository today** (confirmed: `requirements.txt` has no `pillow`/`python-bidi`/`arabic-reshaper` entry; `venv/bin/pip list` shows none of the three installed; no `.ttf`/`.otf` file exists anywhere under this repo).

**1. Add three lines to `requirements.txt`** (append to the existing file, do not reorder/remove anything already there):

```
# Teaser card generation (src/teaser.py — FNL-S001-P002-WP005)
pillow>=10.3            # ImageDraw.rounded_rectangle(corners=...) + text(direction=/language=) need a modern Pillow
python-bidi>=0.4         # RTL reordering fallback — this WP uses the bidi.algorithm.get_display legacy import path
                          # explicitly (confirmed still supported through at least python-bidi 0.6.11), NOT the
                          # newer top-level `from bidi import get_display` Rust-based path, for maximum
                          # cross-platform (Mac dev / Linux runtime) portability with zero extra binary-wheel risk.
arabic-reshaper>=3.0      # Hebrew/Arabic RTL shaping fallback (import name: arabic_reshaper)
```

Then run (in the project's `venv`): `pip install -r requirements.txt`.

**2. System dependency note — libraqm is OPTIONAL, not required, and this WP does not attempt to install it.** Standard `pip install pillow` wheels do not reliably bundle libraqm on every platform/version (confirmed uncertain during spec research — not guaranteed on macOS or Linux manylinux wheels alike); this WP treats that as a given, not a defect to fix (§1 Assumption 2). `teaser.py` detects raqm at runtime (`_raqm_available()`, §2.2) and always has a fully-functional fallback path. **Do not** attempt `brew install raqm` + compiling Pillow from source as part of this WP's setup — out of scope (§6).

**3. Vendor 5 font files into a new `assets/fonts/` directory** (does not exist yet — create it). All 5 are real, freely-licensed (SIL Open Font License) Google Fonts; the exact download URLs below were verified against the `google/fonts` GitHub repository's live directory listings while authoring this spec:

```bash
mkdir -p assets/fonts
curl -sL -o assets/fonts/Bangers-Regular.ttf      https://raw.githubusercontent.com/google/fonts/main/ofl/bangers/Bangers-Regular.ttf
curl -sL -o assets/fonts/Rubik-Regular.ttf        https://raw.githubusercontent.com/google/fonts/main/ofl/rubik/Rubik-Regular.ttf
curl -sL -o assets/fonts/Rubik-Bold.ttf           https://raw.githubusercontent.com/google/fonts/main/ofl/rubik/Rubik-Bold.ttf
curl -sL -o assets/fonts/SecularOne-Regular.ttf   https://raw.githubusercontent.com/google/fonts/main/ofl/secularone/SecularOne-Regular.ttf
```

(`PatrickHand-Regular.ttf` is **not** needed by this WP — teaser.py has no use for it, since its one Latin string, the masthead wordmark, uses Bangers; do not vendor it here.)

Commit the 4 resulting `.ttf` files to git (they are small, license-clear binary assets — the same treatment `assets/characters/` already gets as a tracked directory). After this step, `assets/fonts/` must contain exactly: `Bangers-Regular.ttf`, `Rubik-Regular.ttf`, `Rubik-Bold.ttf`, `SecularOne-Regular.ttf`.

**4. No change to `config/settings.json`.** `teaser.py` takes every tunable (`output_dir`, `assets_dir`, `fonts_dir`, `edition_number`, `hero_category`) as an explicit function parameter with a documented default (§2.8) — matching `WP001`/`WP002`'s established "correct with or without the key present" pattern — so there is nothing this WP needs to add to `settings.json`. A future orchestrator-wiring WP may choose to source these defaults from settings instead; that is out of scope here (§6).

**5. `data/archive/teasers/` (the default output directory) does NOT need to be created manually** — `generate_teaser()` creates it at runtime via `Path.mkdir(parents=True, exist_ok=True)`, identical to `m4_renderer.save_html()`'s existing behavior for `data/archive/html/`.

## 4. API contract changes (if any)

No HTTP endpoints exist in this project (batch/cron pipeline). The contract is `teaser.py`'s public Python surface, plus the file it writes.

| Symbol | Kind | Signature / Shape | Notes |
|---|---|---|---|
| `generate_teaser` | function | `generate_teaser(neo: NEO, *, output_dir: str = "data/archive/teasers/", edition_number: Optional[int] = None, hero_category: Optional[str] = None, assets_dir: str = "assets/characters/", fonts_dir: str = "assets/fonts/") -> str` | THE public entry point. §2.8. Returns the written file path. |
| `TeaserError` | exception | `class TeaserError(Exception)` | Base class. |
| `TeaserRenderError` | exception | `class TeaserRenderError(TeaserError)` | Raised only for the 3 unrecoverable cases in §2.8's docstring. |
| `TEASER_WIDTH`, `TEASER_HEIGHT` | constants | `int` = `1080`, `1350` | For WP006/WP007 to cite (output contract, below). |
| `TEASER_OUTPUT_DIR_DEFAULT` | constant | `str` = `"data/archive/teasers/"` | §1 Assumption 4. |
| `MEMBER_ORDER`, `MEMBER_NAMES_HE`, `MEMBER_COLORS`, `MEMBER_BG`, `MEMBER_EMOJI` | constants | `list[str]` / `dict[str,str]` | The member SSOT table (§1 Assumption 6) — importable if WP007 wants exact parity, though WP007's own template already defines equivalent `{% set %}` blocks and is not required to import this module. |
| `TOPIC_LOOKUP` | constant | `dict[str, dict]` | The topic→scene→character→decoration table (§2.1.7), for any future WP that also needs it (e.g. if WP007's HTML hero adopts the same `hero_category` concept). |

### Output contract (what WP006/WP007 depend on — this WP does not perform the upload or the HTML wiring itself, §6)

| Property | Value |
|---|---|
| Local file path | `<output_dir>/<neo.date>.png`, default `data/archive/teasers/{YYYY-MM-DD}.png` |
| Dimensions | exactly 1080 × 1350 px (portrait, 4:5 aspect ratio) |
| Format | PNG (`img.save(path, "PNG", optimize=True)`), no transparency (flattened to RGB before save) |
| Naming | filename = `f"{neo.date}.png"` — `neo.date` is the same `YYYY-MM-DD` string `m4_renderer.save_html()` uses for the sibling HTML file, so a given edition's HTML and teaser share a filename stem across their respective `data/archive/{html,teasers}/` directories |
| Idempotency | re-running `generate_teaser()` for the same `neo.date` overwrites the existing file at the same path (no versioning/suffixing) |
| Dependency on WP006/WP007 | **none** — `generate_teaser()` never uploads, never touches `config/settings.json`'s `ftp`/`newsletter` sections, and never edits `templates/newsletter.html.j2`'s `og:image` line. WP006 (publisher) is responsible for FTP-uploading the file at the path `generate_teaser()` returns and verifying HTTP 200 at the resulting public URL; WP007 (template) is responsible for pointing `og:image` at that same public URL. Neither dependency runs in the other direction: this WP does not need WP006/WP007 to exist or land first. |

## 5. Error handling requirements

| Error case | Expected behavior |
|---|---|
| `neo is None` | `TeaserRenderError` raised immediately, before any drawing or file I/O (AC-41). |
| `neo.date` missing or empty string | `TeaserRenderError` raised immediately — there is no filename to write (AC-41). |
| libraqm not available (`_raqm_available()` returns `False`) | **Not an error.** Every Hebrew-drawing call transparently uses the `python-bidi` + `arabic-reshaper` fallback path (§2.3) — this is the expected, dependably-correct steady state per §1 Assumption 2, not a degraded corner case. |
| `PIL.features.check("raqm")` itself raises | Caught inside `_raqm_available()`; treated as `False` (fallback path used); a warning is logged (AC-06). |
| A specific font file (`assets/fonts/*.ttf`) is missing or fails to load | `_load_font()` falls back to Pillow's built-in bitmap default font and logs a warning (AC-08) — the card still renders completely, though Hebrew glyphs will not display correctly with the fallback font (this is a genuine visual defect if it happens in production, but it is a **setup omission** — §3's vendoring step was skipped — not a crash; flagged loudly via the log, not silently swallowed). |
| Character/mascot PNG asset not found at any of the 3 lookup tiers | `_resolve_character_asset()` returns `None`; `_draw_mascot_and_greeting()` renders the greeting bubble at full width with no mascot image — a complete, valid card, just without the mascot illustration (AC-31, AC-34). |
| Character/mascot PNG asset found but fails to open/decode (corrupt file, wrong format) | Caught inside `_draw_mascot_and_greeting()`'s `try`/`except`; logged as a warning; treated identically to "no asset found" (falls back to the full-width bubble) (§2.6). |
| `hero_category` given but not a recognized `TOPIC_LOOKUP` key | Logged as a warning; treated as `hero_category=None` — no costume tier attempted, base pose used (AC-32). |
| A member is entirely absent from `neo.member_sections`, or `neo.member_sections` is `None`/empty/malformed | `_member_headline()` returns the neutral placeholder `"עוד השבוע..."` for that member; **the member's row is still drawn** — LOD200 §2's hard rule ("every member ≥1 item") is honored visually even when upstream data is incomplete, by never omitting a row (AC-37, AC-38). |
| A headline (or the combined "`name — headline`" row string, or the masthead wordmark/subtitle/badge, or a greeting-bubble line) is too wide for its allotted box ("oversized text") | `_fit_text()` shrinks the font size within a defined floor, then truncates with a trailing `"…"` if still too wide at the minimum size (AC-15). `_wrap_text()` (greeting bubble only) wraps across up to 3 lines before truncating the last line the same way (AC-19). Neither ever raises or overflows its box. |
| `neo.greeting` missing or empty | The greeting speech bubble is skipped entirely (not drawn) — the rest of the card (masthead, mascot if present, all 5 rows, footer) still renders completely (AC-33). |
| Output directory does not exist | Created via `Path.mkdir(parents=True, exist_ok=True)` — not an error (matches `m4_renderer.save_html()`'s existing behavior). |
| Output directory not writable, disk full, or any other `OSError` during `mkdir`/`save` | Caught and re-raised as `TeaserRenderError`, chained via `from` (AC-44) — this is the one file-I/O failure mode this WP treats as unrecoverable, since there is nothing downstream to hand a missing file to. |
| Mixed Hebrew/Latin/digit text within one string (e.g. a headline containing an English proper noun or a number) | Handled correctly by construction — the Unicode Bidi Algorithm (`python-bidi`) and libraqm both natively handle mixed-direction runs; no special-casing needed in this module (AC-11). |

## 6. Out of scope (explicit)

- **FTP/uPress upload of `teaser.png` and HTTP-200 verification at the public URL** — WP006 (`publisher.py`), per LOD200 §3's happy-path acceptance criterion ("Teaser image generated; uploads to uPress → HTTP 200") splitting the *generation* (this WP) from the *publish+verify* step (WP006). `generate_teaser()` only writes a local file and returns its path (§4).
- **The HTML template's `og:image` line, or any other edit to `templates/newsletter.html.j2`** — WP007. This WP does not touch the template.
- **Sending the WhatsApp teaser message (image + caption + link) via WAHA** — WP006/`whatsapp.py`. This WP produces only the image; `editor.py`'s `teaser_caption` text (WP004) is a separate artifact this WP does not read or depend on (§1 Assumption 8).
- **Deriving `hero_category` automatically from this edition's content** (an equivalent of `SVG_MODULE_SPEC.md`'s `select_hero_topic()`) — accepted as a caller-supplied optional parameter instead; deriving it belongs to whichever future WP assembles `NEO` (§1 Assumption 5).
- **Producing the actual character/mascot artwork** (the PNG files under `assets/characters/{month}/{pose}[__{topic}].png`) — this is a separate, non-code art-production effort (illustration, matching `CHARACTER_ART_DIRECTION`/`CHARACTER_BRIEFS_HE`, §2.1.8), not something `teaser.py`'s code generates. As of this spec's authoring, every asset directory under `assets/characters/` is an empty `.gitkeep` placeholder — `generate_teaser()` is fully correct (via graceful degradation, §5) when none of these assets exist yet.
- **`researcher.py`'s (WP003) real `member_sections` shape** — not yet spec'd at LOD400 authoring time; this WP takes a documented, defensive, fallback-chained dependency on an assumed shape (§1 Assumption 1) rather than blocking on it.
- **Any edit to `src/models.py`, `src/m4_renderer.py`, `src/db.py`, `config/settings.json`, or `requirements.txt`'s existing lines** — this WP only *appends* 3 new lines to `requirements.txt` (§3) and creates new files/directories (`src/teaser.py`, `assets/fonts/*.ttf`); it does not modify any existing file's existing content.
- **A CLI entry point / `if __name__ == "__main__":` block for `teaser.py`** — not requested; `generate_teaser()` is called as a plain function from whichever future orchestrator-wiring WP owns that integration.
- **Compiling/installing a raqm-enabled Pillow build** (`brew install raqm`, building Pillow from source with `--enable-raqm`) — deliberately not attempted; the fallback path is the dependably-correct baseline (§1 Assumption 2, §3).
- **Animated or multi-frame output, video, or any format other than a single static PNG** — not requested by LOD200 or the task brief.

## 7. Test requirements

- **Unit** (no real API/network calls; a handful of tests need real `.ttf` files — see the fixture note below): every AC in §2.1–§2.8 above. Priority/highest-risk targets: the raqm-vs-fallback branch parity in `_draw_rtl_text`/`_measure_rtl_text` (AC-12, AC-13 — the single easiest place for a corner-cutting builder to silently pass `direction=`/`language=` on the non-raqm path and crash in production the moment libraqm is genuinely absent), the character-asset fallback priority chain (AC-28–AC-32), and the "every member always gets a row" guarantee (AC-37, AC-38 — this is LOD200 §2's hard rule made visual). Illustrative skeletons (pytest + pytest-mock, matching the test-stack convention established by WP001/WP002/WP004's specs):

```python
def test_draw_rtl_text_raqm_path_passes_direction_and_language(mocker):
    from src import teaser
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (200, 100))
    draw = ImageDraw.Draw(img)
    text_spy = mocker.patch.object(draw, "text")
    font = mocker.Mock()

    teaser._draw_rtl_text(draw, (10, 10), "שלום", font, "#000000", raqm_available=True)

    text_spy.assert_called_once()
    _, kwargs = text_spy.call_args
    assert kwargs["direction"] == "rtl"
    assert kwargs["language"] == "he"
    assert text_spy.call_args.args[1] == "שלום"   # ORIGINAL, non-bidi-shaped text


def test_draw_rtl_text_fallback_path_omits_direction_and_language(mocker):
    from src import teaser
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (200, 100))
    draw = ImageDraw.Draw(img)
    text_spy = mocker.patch.object(draw, "text")
    font = mocker.Mock()

    teaser._draw_rtl_text(draw, (10, 10), "שלום", font, "#000000", raqm_available=False)

    text_spy.assert_called_once()
    _, kwargs = text_spy.call_args
    assert "direction" not in kwargs
    assert "language" not in kwargs
    assert text_spy.call_args.args[1] == teaser._bidi_shape("שלום")


def test_member_rows_always_draw_all_five(mocker):
    from src import teaser
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (teaser.TEASER_WIDTH, teaser.TEASER_HEIGHT))
    draw = ImageDraw.Draw(img)
    rect_spy = mocker.patch.object(draw, "rounded_rectangle")
    ellipse_spy = mocker.patch.object(draw, "ellipse")
    neo = mocker.Mock(member_sections=None)

    teaser._draw_member_rows(draw, neo, raqm_available=False, fonts_dir="assets/fonts/")

    assert rect_spy.call_count == teaser.ROW_COUNT
    assert ellipse_spy.call_count == teaser.ROW_COUNT


def test_generate_teaser_end_to_end_with_no_assets(tmp_path, mocker):
    from src import teaser
    from PIL import Image
    neo = mocker.Mock(date="2026-07-24", date_formatted="2026-07-24",
                       family_name="בית ולד", greeting="", member_sections=[])

    out_path = teaser.generate_teaser(
        neo,
        output_dir=str(tmp_path / "teasers"),
        assets_dir=str(tmp_path / "no_characters_here"),
        fonts_dir=str(tmp_path / "no_fonts_here"),
    )

    assert out_path.endswith("2026-07-24.png")
    img = Image.open(out_path)
    assert img.size == (1080, 1350)
    assert img.format == "PNG"
```

- **Font/asset fixtures for tests that need a REAL `.ttf`** (e.g. AC-07, and any test exercising the raqm-available=True path against real text shaping rather than a mocked `draw.text`): run §3's vendoring step (`mkdir -p assets/fonts && curl ...`) once in the test environment before running these tests, or vendor a small fixture copy under `tests/fixtures/fonts/` — this spec does not mandate which; either satisfies the ACs as written, since they reference "a real, valid `.ttf` path," not a specific location.
- **Integration** (real Pillow rendering, no network/API cost — this WP makes no LLM calls, so there is no `$` cost to gate, unlike WP001/WP002/WP004's integration tests): after running §3's font-vendoring step for real, call `generate_teaser()` with a realistic mock `NEO` (5 populated `member_sections` entries, a real `greeting` string, a real `hero_category` like `"sailing"`) and manually open the resulting PNG to visually confirm: the masthead gradient+stripe+wordmark+badge render correctly, Hebrew text is right-to-left and legible (not mirrored garbage — confirms the raqm-vs-fallback branch actually in effect on the test machine produced correct output, not just "didn't crash"), all 5 member rows are present in `MEMBER_ORDER`, and the card border is a clean unbroken line. This manual visual check is the only reliable way to catch a subtly-wrong (but non-crashing) RTL rendering bug — unit tests assert on `draw.text()`'s call arguments, not on the actual rendered pixels' visual correctness.
- **Cross-engine validation** (required at L-GATE_VALIDATE per Iron Rule #1 — the validator engine must differ from the builder engine): confirm `src/teaser.py` exports exactly `generate_teaser`, `TeaserError`, `TeaserRenderError`, `TEASER_WIDTH`, `TEASER_HEIGHT`, `TEASER_OUTPUT_DIR_DEFAULT` as its primary public surface (constants in §4's table are also expected to exist and be importable); confirm **no code path ever passes `direction=`/`language=`/`features=` to `draw.text()`/`draw.textbbox()` without first checking `raqm_available`** (AC-12, AC-13 — the single most fragile point in this WP, exactly analogous to WP001's `-f` flag AC-27 being flagged as "the single most safety-critical AC"); confirm `_member_headline()`/`_draw_member_rows()` truly never omit one of the 5 canonical members regardless of input shape (AC-37, AC-38); confirm `git diff` for this WP touches only `src/teaser.py` (new file), `requirements.txt` (3 appended lines only — diff the rest byte-identical), and `assets/fonts/*.ttf` (4 new binary files) — no incidental edits to `src/models.py`, `src/m4_renderer.py`, `templates/newsletter.html.j2`, `config/settings.json`, or `_aos/roadmap.yaml`.

## 8. Consuming team sign-off
> I confirm this spec is executable and unambiguous. All open questions are resolved.
> **Signature:** familynewsletter_build | [PENDING — sign at L-GATE_SPEC]

---

## Cross-Engine Validation — Iron Rule

Documents at LOD400+ require cross-engine validation at L-GATE_VALIDATE.
**The validator engine MUST differ from the builder engine — IRON RULE.**
No exception. No waiver. See `gates/L-GATE_VALIDATE_VALIDATE_AND_LOCK.md`.
