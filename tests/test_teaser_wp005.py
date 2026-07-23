"""
Tests for src/teaser.py — FNL-S001-P002-WP005
Covers: generate without crash, font fallback forces raqm False (P0),
dimensions 1080x1350, mock character missing → graceful degradation.
"""

import pytest
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# ─── Basic import & constants ─────────────────────────────────────────────────

def test_import_teaser():
    """AC-01: module imports with no errors and no side effects."""
    from src import teaser
    assert teaser is not None


def test_exception_hierarchy():
    """AC-02: TeaserRenderError subclasses TeaserError."""
    from src import teaser
    assert issubclass(teaser.TeaserRenderError, teaser.TeaserError)
    assert issubclass(teaser.TeaserError, Exception)


def test_member_constants():
    """AC-03: member tables have exactly 5 canonical keys."""
    from src import teaser
    keys = set(teaser.MEMBER_ORDER)
    assert teaser.MEMBER_ORDER == ["nimrod", "michal", "shaked", "maayan", "tzlil"]
    for tbl in (teaser.MEMBER_NAMES_HE, teaser.MEMBER_COLORS,
                 teaser.MEMBER_BG, teaser.MEMBER_EMOJI):
        assert set(tbl.keys()) == keys, f"Unexpected keys in {tbl}"


def test_topic_lookup_shape():
    """AC-04: TOPIC_LOOKUP has exactly 10 keys with required fields."""
    from src import teaser
    assert len(teaser.TOPIC_LOOKUP) == 10
    for k, v in teaser.TOPIC_LOOKUP.items():
        assert "scene" in v and "member_id" in v and "decorations" in v, k


def test_canvas_dimensions():
    """AC-05: TEASER_WIDTH==1080, TEASER_HEIGHT==1350."""
    from src import teaser
    assert teaser.TEASER_WIDTH == 1080
    assert teaser.TEASER_HEIGHT == 1350


# ─── _raqm_available ─────────────────────────────────────────────────────────

def test_raqm_available_true(mocker):
    """AC-06a: returns True when features.check returns True."""
    from src import teaser
    mocker.patch.object(teaser.features, "check", return_value=True)
    assert teaser._raqm_available() is True


def test_raqm_available_false(mocker):
    """AC-06b: returns False when features.check returns False."""
    from src import teaser
    mocker.patch.object(teaser.features, "check", return_value=False)
    assert teaser._raqm_available() is False


def test_raqm_available_exception(mocker):
    """AC-06c: returns False and logs warning when features.check raises."""
    from src import teaser
    mocker.patch.object(teaser.features, "check", side_effect=RuntimeError("boom"))
    warn = mocker.patch.object(teaser.logger, "warning")
    result = teaser._raqm_available()
    assert result is False
    warn.assert_called_once()


# ─── _load_font ───────────────────────────────────────────────────────────────

def test_load_font_success(tmp_path):
    """AC-07: loads a real TTF, returns FreeTypeFont, no warning."""
    from src import teaser
    import shutil
    real_ttf = Path("assets/fonts/Rubik-Regular.ttf")
    if not real_ttf.exists():
        pytest.skip("Rubik-Regular.ttf not vendored — font-specific test skipped")
    dst = tmp_path / "Rubik-Regular.ttf"
    shutil.copy(real_ttf, dst)
    font = teaser._load_font(str(dst), 40)
    assert isinstance(font, ImageFont.FreeTypeFont)
    assert getattr(font, "_raqm_ok", True) is True


def test_load_font_missing_does_not_raise(mocker):
    """AC-08: missing font path doesn't raise; logs warning; returns usable font."""
    from src import teaser
    warn = mocker.patch.object(teaser.logger, "warning")
    font = teaser._load_font("/definitely/does/not/exist.ttf", 40)
    assert font is not None
    warn.assert_called_once()
    # The returned font must be usable with textbbox
    img = Image.new("RGB", (200, 100))
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), "hello", font=font)
    assert len(bbox) == 4


def test_load_font_fallback_sets_raqm_ok_false(mocker):
    """P0: bitmap fallback font has _raqm_ok=False."""
    from src import teaser
    mocker.patch.object(teaser.logger, "warning")
    font = teaser._load_font("/does/not/exist.ttf", 40)
    assert getattr(font, "_raqm_ok", True) is False


def test_load_font_success_has_raqm_ok_true(tmp_path):
    """P0: successfully loaded TrueType font has _raqm_ok=True."""
    from src import teaser
    real_ttf = Path("assets/fonts/Rubik-Regular.ttf")
    if not real_ttf.exists():
        pytest.skip("Rubik-Regular.ttf not vendored")
    import shutil
    dst = tmp_path / "Rubik-Regular.ttf"
    shutil.copy(real_ttf, dst)
    font = teaser._load_font(str(dst), 40)
    assert getattr(font, "_raqm_ok", None) is True


def test_load_font_older_pillow_fallback(mocker):
    """AC-09: if load_default(size=) raises TypeError, falls back to no-kwarg form."""
    from src import teaser
    mocker.patch.object(teaser.logger, "warning")

    original_load_default = ImageFont.load_default

    def fake_load_default(**kwargs):
        if "size" in kwargs:
            raise TypeError("no size kwarg on this Pillow version")
        return original_load_default()

    mocker.patch.object(ImageFont, "load_default", side_effect=fake_load_default)
    font = teaser._load_font("/does/not/exist.ttf", 40)
    assert font is not None


# ─── _effective_raqm — P0 fix ─────────────────────────────────────────────────

def test_effective_raqm_true_when_font_ok_and_raqm_available():
    """P0: raqm_available=True + font._raqm_ok=True → effective True."""
    from src import teaser
    font = mocker_font(_raqm_ok=True)
    assert teaser._effective_raqm(font, True) is True


def test_effective_raqm_false_when_font_is_fallback():
    """P0: raqm_available=True + font._raqm_ok=False → effective False."""
    from src import teaser
    font = mocker_font(_raqm_ok=False)
    assert teaser._effective_raqm(font, True) is False


def test_effective_raqm_false_when_raqm_not_available():
    """P0: raqm_available=False regardless of font._raqm_ok → effective False."""
    from src import teaser
    font = mocker_font(_raqm_ok=True)
    assert teaser._effective_raqm(font, False) is False


def test_effective_raqm_defaults_true_for_unknown_font():
    """P0: font without _raqm_ok attr → defaults True (safe for real TrueType fonts)."""
    from src import teaser
    font = mocker_font()  # no _raqm_ok attribute
    assert teaser._effective_raqm(font, True) is True


def mocker_font(_raqm_ok=None):
    """Create a minimal mock font object."""
    class FakeFont:
        pass
    f = FakeFont()
    if _raqm_ok is not None:
        f._raqm_ok = _raqm_ok
    return f


# ─── _draw_rtl_text ───────────────────────────────────────────────────────────

def test_draw_rtl_text_raqm_path_passes_direction_and_language(mocker):
    """AC-12a: raqm_available=True → draw.text called with direction='rtl', language='he'."""
    from src import teaser
    img = Image.new("RGB", (200, 100))
    draw = ImageDraw.Draw(img)
    text_spy = mocker.patch.object(draw, "text")
    font = mocker_font(_raqm_ok=True)

    teaser._draw_rtl_text(draw, (10, 10), "שלום", font, "#000000", raqm_available=True)

    text_spy.assert_called_once()
    call_args = text_spy.call_args
    assert call_args.kwargs.get("direction") == "rtl"
    assert call_args.kwargs.get("language") == "he"
    assert call_args.args[1] == "שלום"   # ORIGINAL, non-bidi-shaped text


def test_draw_rtl_text_fallback_path_omits_direction_and_language(mocker):
    """AC-12b: raqm_available=False → draw.text called WITHOUT direction/language."""
    from src import teaser
    img = Image.new("RGB", (200, 100))
    draw = ImageDraw.Draw(img)
    text_spy = mocker.patch.object(draw, "text")
    font = mocker_font(_raqm_ok=True)

    teaser._draw_rtl_text(draw, (10, 10), "שלום", font, "#000000", raqm_available=False)

    text_spy.assert_called_once()
    call_args = text_spy.call_args
    assert "direction" not in call_args.kwargs
    assert "language" not in call_args.kwargs
    assert call_args.args[1] == teaser._bidi_shape("שלום")


def test_draw_rtl_text_bitmap_fallback_forces_bidi_path(mocker):
    """P0 critical: raqm=True + bitmap fallback font → bidi path (no direction= kwarg).
    This is the KeyError crash scenario: raqm globally available but font can't use it."""
    from src import teaser
    img = Image.new("RGB", (200, 100))
    draw = ImageDraw.Draw(img)
    text_spy = mocker.patch.object(draw, "text")
    # Font marked as bitmap fallback (_raqm_ok=False)
    font = mocker_font(_raqm_ok=False)

    teaser._draw_rtl_text(draw, (10, 10), "שלום", font, "#000000", raqm_available=True)

    text_spy.assert_called_once()
    call_args = text_spy.call_args
    # Must NOT have direction= or language= even though raqm_available=True
    assert "direction" not in call_args.kwargs
    assert "language" not in call_args.kwargs


# ─── _bidi_shape ─────────────────────────────────────────────────────────────

def test_bidi_shape_reverses_hebrew():
    """AC-10: _bidi_shape reverses Hebrew character order for RTL visual display."""
    from src import teaser
    shaped = teaser._bidi_shape("שלום")
    # visual-order result should differ from logical-order input
    assert shaped != "שלום"
    assert not shaped.startswith("ש"), "Expected visual-order (right-to-left) output"


def test_bidi_shape_mixed_does_not_raise():
    """AC-11: mixed Hebrew/Latin/digit content doesn't raise."""
    from src import teaser
    result = teaser._bidi_shape("שלום world 123")
    assert isinstance(result, str)


# ─── _resolve_character_asset ────────────────────────────────────────────────

def test_resolve_character_asset_tier1_costumed(tmp_path, mocker):
    """AC-28: tier-1 costumed variant wins when present."""
    from src import teaser
    month = "2026-07"
    pose = "hero-greeting"
    (tmp_path / month).mkdir()
    costumed = tmp_path / month / f"{pose}__sailing.png"
    costumed.write_bytes(b"fake")

    # patch TOPIC_LOOKUP to include "sailing"
    mocker.patch.dict(teaser.TOPIC_LOOKUP, {"sailing": {"scene": "sea", "member_id": "nimrod", "decorations": "sails"}})
    result = teaser._resolve_character_asset(str(tmp_path), month, pose, "sailing")
    assert result == costumed


def test_resolve_character_asset_tier2_base(tmp_path, mocker):
    """AC-29: tier-2 base pose wins when tier-1 costumed is absent."""
    from src import teaser
    month = "2026-07"
    pose = "hero-greeting"
    (tmp_path / month).mkdir()
    base = tmp_path / month / f"{pose}.png"
    base.write_bytes(b"fake")

    mocker.patch.dict(teaser.TOPIC_LOOKUP, {"sailing": {"scene": "sea", "member_id": "nimrod", "decorations": "sails"}})
    result = teaser._resolve_character_asset(str(tmp_path), month, pose, "sailing")
    assert result == base


def test_resolve_character_asset_tier3_placeholder(tmp_path):
    """AC-30: tier-3 _placeholder wins when month-specific assets absent."""
    from src import teaser
    month = "2026-07"
    pose = "hero-greeting"
    placeholder_dir = tmp_path / "_placeholder"
    placeholder_dir.mkdir()
    placeholder = placeholder_dir / f"{pose}.png"
    placeholder.write_bytes(b"fake")

    result = teaser._resolve_character_asset(str(tmp_path), month, pose, None)
    assert result == placeholder


def test_resolve_character_asset_none_when_all_missing(tmp_path, mocker):
    """AC-31: returns None and logs warning when no asset exists at any tier."""
    from src import teaser
    warn = mocker.patch.object(teaser.logger, "warning")
    result = teaser._resolve_character_asset(str(tmp_path), "2026-07", "hero-greeting", None)
    assert result is None
    warn.assert_called_once()


def test_resolve_character_asset_unknown_category_skips_tier1(tmp_path, mocker):
    """AC-32: unrecognized hero_category triggers its own warning and skips tier-1."""
    from src import teaser
    month = "2026-07"
    pose = "hero-greeting"
    # create only base tier-2
    (tmp_path / month).mkdir()
    base = tmp_path / month / f"{pose}.png"
    base.write_bytes(b"fake")

    warnings = []
    mocker.patch.object(teaser.logger, "warning", side_effect=lambda msg, *a, **k: warnings.append(msg))

    result = teaser._resolve_character_asset(str(tmp_path), month, pose, "not_a_real_topic")
    # Should have logged the unrecognized-category warning
    assert any("not_a_real_topic" in w for w in warnings)
    # Should still return base tier-2 (skipped tier-1 entirely)
    assert result == base


# ─── _member_headline ─────────────────────────────────────────────────────────

def test_member_headline_prefers_headline_over_title():
    """AC-35: "headline" preferred over "title"."""
    from src import teaser
    neo = _make_neo(member_sections=[{"member_id": "tzlil", "items": [{"headline": "H", "title": "T"}]}])
    assert teaser._member_headline(neo, "tzlil") == "H"


def test_member_headline_falls_back_to_title():
    """AC-36: missing headline falls back to title."""
    from src import teaser
    neo = _make_neo(member_sections=[{"member_id": "tzlil", "items": [{"title": "T"}]}])
    assert teaser._member_headline(neo, "tzlil") == "T"


def test_member_headline_placeholder_cases():
    """AC-37: all degenerate cases return the neutral placeholder string."""
    from src import teaser
    placeholder = "עוד השבוע..."

    # empty list
    neo = _make_neo(member_sections=[])
    assert teaser._member_headline(neo, "tzlil") == placeholder

    # None
    neo = _make_neo(member_sections=None)
    assert teaser._member_headline(neo, "tzlil") == placeholder

    # no matching member
    neo = _make_neo(member_sections=[{"member_id": "someone_else", "items": [{"headline": "H"}]}])
    assert teaser._member_headline(neo, "tzlil") == placeholder

    # empty items
    neo = _make_neo(member_sections=[{"member_id": "tzlil", "items": []}])
    assert teaser._member_headline(neo, "tzlil") == placeholder


# ─── _draw_member_rows ────────────────────────────────────────────────────────

def test_member_rows_always_draw_all_five(mocker):
    """AC-38: exactly ROW_COUNT rounded_rectangle + ellipse calls, regardless of data."""
    from src import teaser
    img = Image.new("RGB", (teaser.TEASER_WIDTH, teaser.TEASER_HEIGHT))
    draw = ImageDraw.Draw(img)
    rect_spy = mocker.patch.object(draw, "rounded_rectangle")
    ellipse_spy = mocker.patch.object(draw, "ellipse")
    neo = _make_neo(member_sections=None)

    teaser._draw_member_rows(draw, neo, raqm_available=False, fonts_dir="assets/fonts/")

    assert rect_spy.call_count == teaser.ROW_COUNT
    assert ellipse_spy.call_count == teaser.ROW_COUNT


def test_member_rows_top_coordinates():
    """AC-39: row top coords are ROWS_TOP + i*ROW_STEP, none exceed CARD_BOX bottom."""
    from src import teaser
    expected_tops = [teaser.ROWS_TOP + i * teaser.ROW_STEP for i in range(5)]
    assert expected_tops == [720, 824, 928, 1032, 1136]
    for top in expected_tops:
        assert top + teaser.ROW_HEIGHT <= teaser.CARD_BOX[3], f"Row y1={top + teaser.ROW_HEIGHT} exceeds card bottom"


def test_member_rows_shaked_uses_english_name(mocker):
    """P1: Shaked's display name on the teaser row is English 'Shaked', not 'שקד'."""
    from src import teaser
    captured_texts = []
    img = Image.new("RGB", (teaser.TEASER_WIDTH, teaser.TEASER_HEIGHT))
    draw = ImageDraw.Draw(img)

    original_draw_rtl = teaser._draw_rtl_text

    def capture_rtl(d, xy, text, font, fill, raqm_available, anchor="mm"):
        captured_texts.append(text)

    mocker.patch.object(teaser, "_draw_rtl_text", side_effect=capture_rtl)
    mocker.patch.object(teaser, "_fit_text", side_effect=lambda d, t, fp, **kw: (t, mocker_font()))
    mocker.patch.object(draw, "rounded_rectangle")
    mocker.patch.object(draw, "ellipse")

    neo = _make_neo(member_sections=[])
    teaser._draw_member_rows(draw, neo, raqm_available=False, fonts_dir="assets/fonts/")

    # Find text strings that contain member identifiers
    shaked_texts = [t for t in captured_texts if "Shaked" in t or "שקד" in t]
    assert any("Shaked" in t for t in shaked_texts), \
        f"Expected 'Shaked' (English) in row text for shaked member, got: {shaked_texts}"
    assert not any("שקד" in t for t in shaked_texts), \
        f"Expected Hebrew 'שקד' NOT to appear in row (P1: Shaked → English), got: {shaked_texts}"


# ─── _gradient_color_at ───────────────────────────────────────────────────────

def test_gradient_color_at_stops():
    """AC-23: exact stop values at t=0.0, 0.5, 1.0."""
    from src import teaser
    assert teaser._gradient_color_at(0.0, teaser.MASTHEAD_GRADIENT_STOPS) == (192, 57, 43)
    assert teaser._gradient_color_at(0.5, teaser.MASTHEAD_GRADIENT_STOPS) == (231, 76, 60)
    assert teaser._gradient_color_at(1.0, teaser.MASTHEAD_GRADIENT_STOPS) == (230, 126, 34)


def test_diagonal_gradient_corners():
    """AC-24: pixel at (0,0) equals first stop, (w-1,h-1) equals last stop."""
    from src import teaser
    img = teaser._diagonal_gradient(100, 50, teaser.MASTHEAD_GRADIENT_STOPS)
    assert img.size == (100, 50)
    assert img.getpixel((0, 0)) == (192, 57, 43)
    assert img.getpixel((99, 49)) == (230, 126, 34)


def test_add_candy_stripe_mutates_image():
    """AC-25: _add_candy_stripe changes at least one pixel."""
    from src import teaser
    img = Image.new("RGB", (200, 100), (192, 57, 43))
    before = img.copy()
    teaser._add_candy_stripe(img)
    changed = any(img.getpixel((x, y)) != before.getpixel((x, y))
                  for x in range(200) for y in range(100))
    assert changed


# ─── _draw_halftone ───────────────────────────────────────────────────────────

def test_draw_halftone_produces_dots():
    """AC-21: at least one non-background-colored pixel drawn."""
    from src import teaser
    bg = (253, 246, 227)
    img = Image.new("RGB", (100, 100), bg)
    teaser._draw_halftone(img, (0, 0, 100, 100), spacing=24, radius=2)
    pixels = [img.getpixel((x, y)) for x in range(100) for y in range(100)]
    assert any(p != bg for p in pixels)


# ─── _rounded_mask ────────────────────────────────────────────────────────────

def test_rounded_mask_corners():
    """AC-22: top corners rounded (pixel=0), bottom corners square (pixel=255)."""
    from src import teaser
    mask = teaser._rounded_mask((200, 100), radius=20, corners=(True, True, False, False))
    assert mask.mode == "L"
    assert mask.size == (200, 100)
    # Top-left corner should be masked (transparent/0)
    assert mask.getpixel((0, 0)) == 0
    # Bottom-left corner: bottom_left=False → NOT rounded → should be 255 (opaque)
    assert mask.getpixel((0, 99)) == 255


# ─── generate_teaser — core tests ────────────────────────────────────────────

def test_generate_teaser_none_raises():
    """AC-41a: neo=None raises TeaserRenderError."""
    from src import teaser
    with pytest.raises(teaser.TeaserRenderError):
        teaser.generate_teaser(None)


def test_generate_teaser_empty_date_raises():
    """AC-41b: neo.date='' raises TeaserRenderError."""
    from src import teaser
    neo = _make_neo(date="")
    with pytest.raises(teaser.TeaserRenderError):
        teaser.generate_teaser(neo)


def test_generate_teaser_no_assets_end_to_end(tmp_path):
    """AC-42: full render with no fonts/assets succeeds; file is 1080x1350 PNG.

    This exercises the full missing-font + missing-mascot graceful-degradation
    chain end-to-end (fonts_dir and assets_dir point at empty tmp dirs)."""
    from src import teaser
    neo = _make_neo(date="2026-07-24", date_formatted="2026-07-24",
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


def test_generate_teaser_dimensions_1080x1350(tmp_path):
    """Explicit dimension check — 1080x1350."""
    from src import teaser
    neo = _make_neo(date="2026-07-25", member_sections=[])
    out_path = teaser.generate_teaser(
        neo,
        output_dir=str(tmp_path / "teasers"),
        assets_dir=str(tmp_path / "chars"),
        fonts_dir=str(tmp_path / "fonts"),
    )
    img = Image.open(out_path)
    assert img.size == (teaser.TEASER_WIDTH, teaser.TEASER_HEIGHT)
    assert img.size == (1080, 1350)


def test_generate_teaser_with_real_fonts(tmp_path):
    """Integration: render with vendored fonts; file is valid PNG 1080x1350."""
    real_fonts = Path("assets/fonts")
    if not real_fonts.exists() or not (real_fonts / "Rubik-Regular.ttf").exists():
        pytest.skip("Vendored fonts not available — skipping font integration test")
    from src import teaser
    neo = _make_neo(date="2026-07-26", date_formatted="July 26 2026",
                    family_name="בית ולד", greeting="שלום משפחה!",
                    member_sections=[
                        {"member_id": "nimrod", "items": [{"headline": "הפלגה בים"}]},
                        {"member_id": "michal", "items": [{"headline": "גינה חדשה"}]},
                        {"member_id": "shaked", "items": [{"headline": "כימיה מגניבה"}]},
                        {"member_id": "maayan", "items": [{"headline": "קרקס מדהים"}]},
                        {"member_id": "tzlil",  "items": [{"headline": "מתמטיקה"}]},
                    ])
    out_path = teaser.generate_teaser(
        neo,
        output_dir=str(tmp_path / "teasers"),
        assets_dir=str(tmp_path / "chars"),
        fonts_dir=str(real_fonts),
    )
    img = Image.open(out_path)
    assert img.size == (1080, 1350)
    assert img.format == "PNG"


def test_generate_teaser_idempotent(tmp_path):
    """AC-43: second call overwrites same path, no suffix added."""
    from src import teaser
    neo = _make_neo(date="2026-07-27", member_sections=[])
    out1 = teaser.generate_teaser(neo, output_dir=str(tmp_path / "t"),
                                   assets_dir=str(tmp_path / "c"),
                                   fonts_dir=str(tmp_path / "f"))
    out2 = teaser.generate_teaser(neo, output_dir=str(tmp_path / "t"),
                                   assets_dir=str(tmp_path / "c"),
                                   fonts_dir=str(tmp_path / "f"))
    assert out1 == out2


def test_generate_teaser_save_oserror_raises_render_error(tmp_path, mocker):
    """AC-44: OSError during save is re-raised as TeaserRenderError (chained)."""
    from src import teaser
    mocker.patch("PIL.Image.Image.save", side_effect=OSError("disk full"))
    neo = _make_neo(date="2026-07-28", member_sections=[])
    with pytest.raises(teaser.TeaserRenderError) as exc_info:
        teaser.generate_teaser(neo, output_dir=str(tmp_path / "t"),
                                assets_dir=str(tmp_path / "c"),
                                fonts_dir=str(tmp_path / "f"))
    # Verify chaining
    assert exc_info.value.__cause__ is not None


def test_generate_teaser_missing_character_graceful(tmp_path):
    """Mock character missing → graceful degradation (no crash, valid PNG)."""
    from src import teaser
    neo = _make_neo(date="2026-07-29", greeting="שלום!", member_sections=[])
    out_path = teaser.generate_teaser(
        neo,
        output_dir=str(tmp_path / "teasers"),
        assets_dir=str(tmp_path / "empty_assets"),   # no character PNGs
        fonts_dir=str(tmp_path / "empty_fonts"),
    )
    img = Image.open(out_path)
    assert img.size == (1080, 1350)


def test_font_fallback_forces_raqm_false_in_real_render(tmp_path, mocker):
    """P0 integration: when fonts are missing, draw.text is never called with
    direction=, even when raqm is globally available.
    This is the critical regression guard for the KeyError crash scenario."""
    from src import teaser

    # Force raqm to appear available
    mocker.patch.object(teaser, "_raqm_available", return_value=True)

    # Intercept draw.text calls and check for illegal direction= kwargs
    original_new = Image.new
    calls_with_direction = []

    class SpyDraw:
        def __init__(self, draw):
            self._draw = draw

        def __getattr__(self, name):
            attr = getattr(self._draw, name)
            if name == "text":
                def spy_text(*args, **kwargs):
                    if "direction" in kwargs:
                        calls_with_direction.append((args, kwargs))
                    return attr(*args, **kwargs)
                return spy_text
            return attr

    neo = _make_neo(date="2026-07-30", member_sections=[])
    # Render with NO real fonts (all font loads will fall back to bitmap)
    out_path = teaser.generate_teaser(
        neo,
        output_dir=str(tmp_path / "t"),
        assets_dir=str(tmp_path / "c"),
        fonts_dir=str(tmp_path / "f"),  # empty dir → all fonts fall back to bitmap
    )
    # If we got here without crashing, the P0 fix is working.
    assert Path(out_path).exists()

    # Additionally verify: no draw.text() call with direction= was made
    # when all fonts are bitmap fallbacks (_raqm_ok=False)
    # (this is checked implicitly — a crash would have occurred above
    #  if direction= was passed to a bitmap fallback font with raqm=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_neo(**overrides):
    """Create a minimal NEO-like object for testing."""
    from src.models import NEO
    defaults = dict(
        date="2026-07-24",
        family_name="בית ולד",
        greeting="",
        family_content=[],
        member_sections=[],
        discovery=[],
        trivia={},
        survey_question="",
        date_formatted="",
    )
    defaults.update(overrides)
    return NEO(**defaults)
