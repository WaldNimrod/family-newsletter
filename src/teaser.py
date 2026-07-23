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


# ─── Exceptions ───────────────────────────────────────────────────────────────

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


# ─── Canvas geometry constants ────────────────────────────────────────────────

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


# ─── Color palette ────────────────────────────────────────────────────────────
# hex values ground-truthed from templates/newsletter.html.j2 :root block
# (lines 9–24) and its {% set member_bg %} line (line 491),
# corroborated by STYLE_GUIDE.md §8

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


# ─── Member SSOT table ────────────────────────────────────────────────────────
# per §1 Assumption 6, transcribed verbatim from STYLE_GUIDE.md §8's
# "source of truth" table (primary color/emoji/name) plus
# templates/newsletter.html.j2 line 491 (light tint)

MEMBER_ORDER = ["nimrod", "michal", "shaked", "maayan", "tzlil"]

MEMBER_NAMES_HE = {
    "nimrod": "נימרוד", "michal": "מיכל", "shaked": "שקד",
    "maayan": "יויו", "tzlil": "צליל",
}

# P1: Display names for teaser rows — Shaked uses English name on the card
# (avoids Hebrew-only rendering for a name that's commonly written in English)
MEMBER_NAMES_DISPLAY = {
    "nimrod": "נימרוד", "michal": "מיכל", "shaked": "Shaked",
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


# ─── Font vendoring constants ─────────────────────────────────────────────────

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


# ─── Topic → scene → character → decoration lookup table ─────────────────────
# transcribed from SVG_MODULE_SPEC.md §4's Hebrew table (10 rows, verbatim
# content, English keys for code use). Drives the mascot's optional costumed
# variant (§2.6). member_id is carried for documentation/traceability to the
# source table only; it is NOT read by any selection logic in this WP.

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


# ─── §2.2 Font loading + libraqm detection ───────────────────────────────────

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
    runtime condition, so the fallback always logs a warning.

    P0 FIX: When the bitmap fallback is used, sets `_raqm_ok = False` on
    the returned font object. Callers must call _effective_raqm(font,
    raqm_available) before passing direction=/language= to draw.text(),
    because raqm=True + bitmap fallback font = KeyError crash inside
    Pillow's raqm shaping code (the bitmap font lacks the internal
    glyph-map structures that raqm's shaping engine expects)."""
    try:
        font = ImageFont.truetype(font_path, size)
        font._raqm_ok = True
        return font
    except (OSError, IOError) as e:
        logger.warning(
            f"[teaser] Failed to load font '{font_path}' at size {size}: "
            f"{e!r}. Falling back to Pillow's built-in default font "
            f"(Hebrew text will not render correctly with this fallback; "
            f"see §3 for the required font-vendoring setup step)."
        )
        try:
            font = ImageFont.load_default(size=size)   # Pillow >= 10.1.0
        except TypeError:
            font = ImageFont.load_default()   # older Pillow: no size kwarg
        # P0: bitmap fallback must never receive direction=/language= kwargs —
        # mark this font so _effective_raqm() forces the bidi fallback path.
        font._raqm_ok = False
        return font


def _effective_raqm(font, raqm_available: bool) -> bool:
    """Returns the effective raqm_available flag for a specific font object.
    P0 fix: if the font is a bitmap fallback (_raqm_ok=False), raqm is
    forced off regardless of the global availability, because passing
    direction=/language= to draw.text() with a bitmap fallback font causes
    a KeyError crash inside Pillow's raqm shaping code."""
    return raqm_available and bool(getattr(font, '_raqm_ok', True))


# ─── §2.3 RTL text engine ────────────────────────────────────────────────────

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
    box regardless of the internal shaping direction used to produce it.

    P0 FIX: Uses _effective_raqm(font, raqm_available) so that a bitmap
    fallback font never receives direction=/language= kwargs even when
    raqm is globally available."""
    eff_raqm = _effective_raqm(font, raqm_available)
    if eff_raqm:
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
    gets rendered.

    P0 FIX: Uses _effective_raqm(font, raqm_available) to match
    _draw_rtl_text's exact branching."""
    eff_raqm = _effective_raqm(font, raqm_available)
    if eff_raqm:
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


# ─── §2.4 Halftone texture + rounded-corner masking primitives ───────────────

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


# ─── §2.5 Diagonal gradient + candy-stripe overlay + masthead band ────────────

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


# ─── §2.6 Character/mascot asset resolution + placement ──────────────────────

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


# ─── §2.7 Member headline rows ────────────────────────────────────────────────

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
    hard rule: every member appears).

    P1: Uses MEMBER_NAMES_DISPLAY instead of MEMBER_NAMES_HE so that
    Shaked's name appears as "Shaked" (English) on the teaser row."""
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

        # P1: use MEMBER_NAMES_DISPLAY (Shaked → English "Shaked")
        name = MEMBER_NAMES_DISPLAY.get(member_id, member_id)
        headline = _member_headline(neo, member_id)
        row_text = f"{name}  —  {headline}"
        max_width = ROW_TEXT_RIGHT - CONTENT_LEFT - 14   # 14px clearance past the dot
        fitted_text, fitted_font = _fit_text(
            draw, row_text, row_font_path, max_width=max_width,
            start_size=30, min_size=18, raqm_available=raqm_available,
        )
        _draw_rtl_text(draw, (ROW_TEXT_RIGHT, row_center_y), fitted_text,
                        fitted_font, COLOR_INK, raqm_available, anchor="rm")


# ─── §2.8 Footer + public entry point — generate_teaser() ───────────────────

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
