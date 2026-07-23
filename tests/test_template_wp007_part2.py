"""
WP007-part-2: Template extension — Personal Corners ×5, Viewing, Family-Table,
Extended-Family, Shelf, Dark-mode CSS, Footer, og:image.

Tests render via m4_renderer.render() with rich/sparse NEO fixtures.
All assertions use string/substring checks on the returned HTML — no browser needed.
"""
from __future__ import annotations

import re
from pathlib import Path
import pytest

from src.m4_renderer import render, get_character_html
from src.models import NEO, Settings


# ─── Fixture helpers ──────────────────────────────────────────────────────────

def _item(member_id: str, *, url: str = "https://example.com", image_url=None,
          title: str = "כותרת", summary: str = "סיכום כלשהו", language: str = "he") -> dict:
    return {
        "title": title,
        "summary": summary,
        "full_text": summary,
        "url": url,
        "source_name": "מקור",
        "category": "קטגוריה",
        "language": language,
        "image_url": image_url,
        "published_at": None,
    }


def _section(member_id: str, items: list, *, language: str = "he") -> dict:
    names = {"nimrod": "נימרוד", "michal": "מיכל", "shaked": "Shaked",
             "maayan": "יויו", "tzlil": "צליל"}
    names_en = {"nimrod": "Nimrod", "michal": "Michal", "shaked": "Shaked",
                "maayan": "Maayan", "tzlil": "Tzlil"}
    return {
        "member_id": member_id,
        "member_name": names.get(member_id, member_id),
        "member_name_en": names_en.get(member_id, member_id),
        "language": language,
        "items": items,
    }


def _full_neo(*, extra_meta: dict | None = None, family_content: list | None = None) -> NEO:
    """Fixture with all 5 members, all optional sections populated."""
    meta = {
        "opener_text": "שלום משפחה <strong>יקרה</strong>!",
        "closer_text": "להתראות שבוע הבא.",
        "weather": [
            {"city": "פרדס חנה", "icon": "☀️", "temp": "28°", "is_temp": False,
             "wind_alert": False, "daily": [], "description": "בית", "week_summary": ""}
        ],
        "viewing": {
            "family_pick": {
                "title": "The Bear",
                "platform": "Disney+",
                "hebrew_subs": True,
                "available_il": True,
                "note": "ממליצים!",
            },
            "personal_pick": {
                "member_id": "michal",
                "title": "Barry",
                "platform": "MAX",
                "hebrew_subs": False,
                "available_il": True,
                "note": "",
            },
        },
        "family_table_text": "שאלת השבוע: מה הדבר הכי מגניב שעשיתם?",
        "extended_family": [
            {"name": "סבתא רות", "relation": "סבתא", "headline": "ביקרה בניו יורק",
             "pointer_text": "הצילומים מהטיול", "link_url": "https://example.com/photos"},
            {"name": "דוד אלי", "relation": "דוד", "headline": "פרסם ספר חדש",
             "pointer_text": "", "link_url": ""},
        ],
        "shelf_pick": {
            "title_he": "אלף שמשות",
            "title_en": "A Thousand Suns",
            "author": "ח. א. ניומן",
            "category": "ספרות",
            "member_id": "michal",
            "blurb": "ספר מרגש על חוסן משפחתי.",
        },
        "editor_name": "צליל",
        "whatsapp_number": "972501234567",
        "whatsapp_group_link": "",
        "character_emoji": "🎩",
        "character_name": "Cat in the Hat",
        "character_month": "2026-07",
    }
    if extra_meta:
        meta.update(extra_meta)

    return NEO(
        date="2026-07-25",
        family_name="בית ולד",
        greeting="שלום משפחה!",
        family_content=family_content or [],
        member_sections=[
            _section("nimrod", [_item("nimrod"), _item("nimrod"), _item("nimrod")]),
            _section("michal", [_item("michal")]),
            _section("shaked", [_item("shaked"), _item("shaked")], language="en"),
            _section("maayan", [_item("maayan"), _item("maayan"), _item("maayan"), _item("maayan")]),
            _section("tzlil", [_item("tzlil")]),
        ],
        discovery=[
            {"bridge_text": "חיבור מעניין", "title": "כתבה", "url": "https://example.com/disc",
             "summary": "תקציר"},
        ],
        trivia={"puzzle": "מה מספר שישי?", "answer": "6", "history": "היום 1776"},
        survey_question="מה דעתכם?",
        date_formatted="יום שישי, 25 ביולי 2026",
        metadata=meta,
    )


def _placeholder_neo() -> NEO:
    """Fixture with BUILD_DIRECTIVE D1 placeholder values (as orchestrator sets them)."""
    meta = {
        "opener_text": "פתיח",
        "closer_text": "סגירה",
        "weather": [],
        "viewing": {
            "family_pick": {"title": "🚧 בהכנה", "platform": "", "hebrew_subs": False,
                            "available_il": False, "note": ""},
            "personal_pick": None,
        },
        "family_table_text": "🚧 בהכנה",
        "extended_family": [
            {"headline": "🚧 בהכנה", "name": "", "relation": "", "pointer_text": "", "link_url": ""}
        ],
        "shelf_pick": {"blurb": "🚧 בהכנה"},
        "editor_name": "צליל",
        "whatsapp_number": "",
        "whatsapp_group_link": "",
        "character_emoji": "🎩",
        "character_name": "Cat in the Hat",
        "character_month": "2026-07",
    }
    return NEO(
        date="2026-07-25",
        family_name="בית ולד",
        greeting="שלום!",
        family_content=[],
        member_sections=[
            _section("nimrod", [_item("nimrod"), _item("nimrod")]),
            _section("michal", [_item("michal")]),
            _section("shaked", [_item("shaked")], language="en"),
            _section("maayan", [_item("maayan"), _item("maayan"), _item("maayan")]),
            _section("tzlil", [_item("tzlil")]),
        ],
        discovery=[
            {"bridge_text": "גשר", "title": "כתבה", "url": "https://example.com", "summary": "סיכום"}
        ],
        trivia={"puzzle": "חידה", "answer": "42", "history": "היסטוריה"},
        survey_question="שאלה?",
        date_formatted="יום שישי",
        metadata=meta,
    )


def _sparse_neo() -> NEO:
    """Minimal NEO — most optional sections absent (metadata keys missing)."""
    return NEO(
        date="2026-07-25",
        family_name="בית ולד",
        greeting="שלום!",
        family_content=[],
        member_sections=[
            _section("nimrod", [_item("nimrod")]),
        ],
        discovery=[],
        trivia={"puzzle": "", "answer": "", "history": ""},
        survey_question="",
        date_formatted="",
        metadata={},
    )


@pytest.fixture(autouse=True)
def chdir_workspace(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])


def _body(html: str) -> str:
    """Return the HTML body portion — everything after the last </style> tag.

    CSS rules define class names like `.viewing-panel {` which cause naive
    substring searches to report false positives when testing for section
    absence or relative ordering in the rendered HTML body.
    """
    marker = "</style>"
    idx = html.rfind(marker)
    return html[idx + len(marker):] if idx != -1 else html


# ─── Section marker checks ────────────────────────────────────────────────────

class TestAllSectionsPresent:
    """AC-12 + §7 table: all 13 LOD200 sections + shelf visible in full fixture.

    NOTE: Sections rendered with panel-level3 have class="panel-level3 X-panel",
    so assertions check substring 'X-panel' (or '"X-panel"') rather than
    the full 'class="X-panel"' attribute.
    """

    def test_cover_present(self):
        html = render(_full_neo())
        assert 'class="cover"' in html
        assert "Family Newsletter!" in html

    def test_opener_present(self):
        html = render(_full_neo())
        assert 'class="opener"' in html

    def test_family_strip_present(self):
        html = render(_full_neo())
        assert 'class="family-strip"' in html

    def test_weather_present(self):
        html = render(_full_neo())
        assert 'class="weather-section"' in html

    def test_personal_corners_five_present(self):
        html = render(_full_neo())
        assert html.count('class="member-corner') == 5

    def test_discovery_present(self):
        html = render(_full_neo())
        assert 'discovery-panel' in html

    def test_viewing_present(self):
        html = render(_full_neo())
        assert 'viewing-panel' in html

    def test_family_table_present(self):
        html = render(_full_neo())
        assert 'family-table-panel' in html

    def test_shelf_present(self):
        html = render(_full_neo())
        assert 'shelf-panel' in html

    def test_puzzle_present(self):
        html = render(_full_neo())
        assert 'puzzle-panel' in html

    def test_extended_family_present(self):
        html = render(_full_neo())
        assert 'extended-family-panel' in html

    def test_history_present(self):
        html = render(_full_neo())
        assert 'history-panel' in html

    def test_survey_present(self):
        html = render(_full_neo())
        assert 'survey-panel' in html

    def test_closer_present(self):
        html = render(_full_neo())
        assert 'class="closer"' in html

    def test_footer_present(self):
        html = render(_full_neo())
        assert 'class="footer-strip"' in html


class TestPlaceholderSectionsVisible:
    """BUILD_DIRECTIVE D1: placeholder sections must be visibly rendered."""

    def test_viewing_placeholder_renders(self):
        html = render(_placeholder_neo())
        assert 'viewing-panel' in html
        assert "🚧 בהכנה" in html

    def test_family_table_placeholder_renders(self):
        html = render(_placeholder_neo())
        assert 'family-table-panel' in html

    def test_extended_family_placeholder_renders(self):
        html = render(_placeholder_neo())
        assert 'extended-family-panel' in html

    def test_shelf_placeholder_renders(self):
        """Shelf renders even when only blurb=placeholder, no title_he/title_en."""
        html = render(_placeholder_neo())
        assert 'shelf-panel' in html

    def test_all_13_plus_shelf_in_placeholder_build(self):
        html = render(_placeholder_neo())
        for marker in [
            'class="cover"',
            'class="opener"',
            'class="family-strip"',
            'class="member-corner',
            'discovery-panel',
            'viewing-panel',
            'family-table-panel',
            'shelf-panel',
            'puzzle-panel',
            'extended-family-panel',
            'history-panel',
            'survey-panel',
            'class="closer"',
            'class="footer-strip"',
        ]:
            assert marker in html, f"Missing section marker: {marker}"


# ─── Personal Corners ─────────────────────────────────────────────────────────

class TestPersonalCorners:
    def test_five_corners_full_fixture(self):
        html = render(_full_neo())
        assert html.count('class="member-corner') == 5

    def test_member_with_zero_items_skipped(self):
        neo = _full_neo()
        neo.member_sections[0]["items"] = []
        html = render(neo)
        # Should have 4 corners, not 5
        assert html.count('class="member-corner') == 4

    def test_hero_is_panel_level1(self):
        html = render(_full_neo())
        assert 'panel-level1' in html

    def test_single_item_corner_no_level2(self):
        """AC-17: member with 1 item → only hero, no level2-row."""
        neo = _full_neo()
        neo.member_sections = [_section("nimrod", [_item("nimrod")])]
        html = render(neo)
        assert 'class="member-corner"' in html
        assert 'class="level2-row"' not in html

    def test_three_items_corner_no_solo_for_even_rest(self):
        """AC-16: corner_rest of length 2 → zero panel-level2-solo on any element.

        CSS defines '.panel-level2-solo { flex:1 }' so the bare substring
        'panel-level2-solo' is always present.  The trailing-quote form
        'panel-level2-solo"' only matches the HTML class attribute.
        """
        neo = _full_neo()
        neo.member_sections = [_section("nimrod", [_item("nimrod")] * 3)]  # 1 hero + 2 rest = even
        html = render(neo)
        assert 'panel-level2-solo"' not in html

    def test_five_items_no_solo(self):
        """AC-16: corner_rest of length 4 → zero panel-level2-solo on any element."""
        neo = _full_neo()
        neo.member_sections = [_section("nimrod", [_item("nimrod")] * 5)]  # 1 hero + 4 rest = even
        html = render(neo)
        assert 'panel-level2-solo"' not in html

    def test_four_items_has_solo_on_last(self):
        """AC-16: corner_rest of length 3 → solo on last item."""
        neo = _full_neo()
        neo.member_sections = [
            _section("nimrod", [_item("nimrod")] * 4)  # 1 hero + 3 rest = odd → solo
        ]
        html = render(neo)
        assert 'panel-level2-solo"' in html

    def test_two_items_has_solo(self):
        """AC-15: corner_rest of length 1 → solo class present."""
        neo = _full_neo()
        neo.member_sections = [_section("nimrod", [_item("nimrod")] * 2)]  # 1 hero + 1 rest
        html = render(neo)
        assert 'panel-level2-solo"' in html

    def test_no_member_tag_inside_corner(self):
        """AC-18: no class="member-tag" inside member-corner cards."""
        html = render(_full_neo())
        # member-tag should only appear in family-strip context
        # The corner cards should not have individual member-tag chips
        # Count member-tag occurrences; they should only be in CSS (.member-tag {...})
        # not in the HTML body inside .member-corner
        # Simple check: member-tag as html class inside a corner block is absent
        # We look for class= attributes with member-tag inside a corner section
        assert 'class="member-tag"' not in html.split('<div class="member-corner')[1] if html.count('<div class="member-corner') >= 1 else True

    def test_hero_svg_scene_has_member_id_suffix(self):
        """AC-19: SVG defs ids are suffixed with member_id."""
        neo = _full_neo()
        for sec in neo.member_sections:
            for item in sec["items"]:
                item["image_url"] = None
        html = render(neo)
        assert 'id="corner-sky-nimrod"' in html
        assert 'id="corner-sky-michal"' in html

    def test_youtube_item_gets_yt_thumb(self):
        """AC-23: yt-thumb only on YouTube URLs."""
        items = [
            _item("nimrod", url="https://youtube.com/watch?v=abc", image_url="https://img.example.com/thumb.jpg"),
            _item("nimrod", url="https://example.com/article"),
        ]
        neo = _full_neo()
        neo.member_sections = [_section("nimrod", items)]
        html = render(neo)
        assert "yt-thumb" in html

    def test_no_old_hero_level_comments_in_template_code(self):
        """AC-11: old LEVEL 1/2/3 Jinja template blocks removed (CSS comments ok)."""
        # The template still has CSS comments /* ===== LEVEL 1: HERO PANEL ===== */
        # but the OLD JINJA template code (<!-- ===== LEVEL 1: HERO ===== -->) is gone
        html = render(_full_neo())
        assert "ns.l2_count" not in html  # Jinja variable absolutely gone

    def test_no_l2_count_in_template_source(self):
        """AC-11: ns.l2_count absent from template source."""
        template_text = Path("templates/newsletter.html.j2").read_text(encoding="utf-8")
        assert "ns.l2_count" not in template_text

    def test_character_html_hero_safe_rendered(self):
        """AC-21/22: character_html | safe renders emoji span, not escaped HTML."""
        html = render(_full_neo())
        assert "hero-character-slot" in html
        assert "&lt;span" not in html  # autoescape would produce this if | safe missing


# ─── Viewing Section ──────────────────────────────────────────────────────────

class TestViewingSection:
    def test_viewing_renders_with_real_data(self):
        html = render(_full_neo())
        assert "The Bear" in html
        assert "Disney+" in html
        assert "כתוביות עברית ✓" in html

    def test_viewing_absent_when_no_metadata(self):
        """AC-25: viewing panel absent when viewing key missing.

        Searches the HTML body (after </style>) because CSS always defines
        '.viewing-panel { ... }', which would cause a false match.
        """
        html = _body(render(_sparse_neo()))
        assert 'viewing-panel' not in html

    def test_viewing_family_pick_only(self):
        """AC-26: only family_pick renders."""
        neo = _full_neo()
        neo.metadata["viewing"] = {
            "family_pick": {"title": "Succession", "platform": "HBO", "hebrew_subs": False,
                            "available_il": True, "note": ""},
            "personal_pick": None,
        }
        html = render(neo)
        assert "Succession" in html

    def test_viewing_hebrew_subs_badge(self):
        html = render(_full_neo())
        assert "viewing-badge-ok" in html

    def test_viewing_placeholder_shows_placeholder_block(self):
        html = render(_placeholder_neo())
        assert "placeholder-block" in html

    def test_viewing_between_discovery_and_puzzle(self):
        """AC-29: viewing-panel appears after discovery-panel and before puzzle-panel.

        Searches the HTML body (after </style>) to avoid the CSS rule ordering
        which differs from the body element ordering.
        """
        body = _body(render(_full_neo()))
        disc_pos = body.find('discovery-panel')
        view_pos = body.find('viewing-panel')
        puzzle_pos = body.find('puzzle-panel')
        assert disc_pos != -1
        assert view_pos != -1
        assert puzzle_pos != -1
        assert disc_pos < view_pos < puzzle_pos


# ─── Family Table ─────────────────────────────────────────────────────────────

class TestFamilyTable:
    def test_family_table_renders_with_text(self):
        html = render(_full_neo())
        assert "שאלת השבוע: מה הדבר" in html

    def test_family_table_absent_when_both_empty(self):
        """AC-31: section absent when both family_content empty and family_table_text empty.

        Searches the HTML body (after </style>) to avoid the CSS rule.
        """
        neo = _sparse_neo()
        neo.metadata["family_table_text"] = ""
        html = _body(render(neo))
        assert 'family-table-panel' not in html

    def test_family_table_with_submissions(self):
        """AC-32: renders items when family_content present."""
        neo = _full_neo(family_content=[
            {"member_name": "מיכל", "headline": "ביקרנו בים", "summary": "כיף היה",
             "link_url": "https://example.com/beach", "message_type": "text"}
        ])
        neo.metadata["family_table_text"] = ""
        html = render(neo)
        assert 'family-table-panel' in html
        assert "מיכל שיתפ/ה" in html

    def test_family_table_text_only_no_items_div(self):
        """AC-33: only prompt when family_content empty."""
        neo = _full_neo()
        neo.metadata["family_table_text"] = "שאלה לשולחן"
        neo.family_content = []
        html = render(neo)
        assert 'class="family-table-items"' not in html

    def test_family_table_placeholder_visible(self):
        html = render(_placeholder_neo())
        assert 'family-table-panel' in html

    def test_family_table_item_missing_member_name(self):
        """AC-36: absent member_name renders '' not error."""
        neo = _full_neo(family_content=[
            {"headline": "משהו", "summary": "", "link_url": "", "message_type": "text"}
        ])
        neo.metadata["family_table_text"] = ""
        html = render(neo)
        assert "שיתפ/ה" in html  # renders even with no name


# ─── Shelf Section ────────────────────────────────────────────────────────────

class TestShelfSection:
    def test_shelf_renders_with_full_data(self):
        html = render(_full_neo())
        assert "אלף שמשות" in html
        assert "ח. א. ניומן" in html

    def test_shelf_absent_when_no_shelf_key(self):
        """AC-37: shelf absent when shelf_pick key entirely missing.

        Searches the HTML body (after </style>) to avoid the CSS rule.
        """
        neo = _sparse_neo()
        html = _body(render(neo))
        assert 'shelf-panel' not in html

    def test_shelf_only_title_he(self):
        """AC-38: only title_he renders correctly without shelf-title-en."""
        neo = _full_neo()
        neo.metadata["shelf_pick"] = {"title_he": "ספר ישראלי", "author": "מחבר"}
        html = render(neo)
        assert "ספר ישראלי" in html
        assert 'class="shelf-title-en"' not in html

    def test_shelf_after_family_table_before_puzzle(self):
        """AC-39: shelf-panel between family-table-panel and puzzle-panel.

        Searches the HTML body (after </style>) to avoid CSS rule ordering.
        """
        body = _body(render(_full_neo()))
        ft_pos = body.find('family-table-panel')
        shelf_pos = body.find('shelf-panel')
        puzzle_pos = body.find('puzzle-panel')
        assert ft_pos != -1
        assert shelf_pos != -1
        assert puzzle_pos != -1
        assert ft_pos < shelf_pos < puzzle_pos

    def test_shelf_placeholder_renders(self):
        """D1: shelf renders even with only blurb=placeholder."""
        html = render(_placeholder_neo())
        assert 'shelf-panel' in html

    def test_shelf_character_reading_used(self):
        """AC-40: reading pose used for shelf (not hero-greeting etc.)."""
        neo = _full_neo()
        html = render(neo)
        assert "character-reading" in html


# ─── Extended Family ──────────────────────────────────────────────────────────

class TestExtendedFamily:
    def test_extended_family_renders(self):
        html = render(_full_neo())
        assert 'extended-family-panel' in html
        assert "סבתא רות" in html

    def test_extended_family_absent_when_empty(self):
        """AC-42: absent when extended_family list is empty.

        Searches the HTML body (after </style>) to avoid the CSS rule.
        """
        neo = _full_neo()
        neo.metadata["extended_family"] = []
        html = _body(render(neo))
        assert 'extended-family-panel' not in html

    def test_extended_family_no_img_video(self):
        """AC-43: extended-family section contains no <img, <video, <source."""
        html = render(_full_neo())
        idx = html.find('extended-family-panel')
        assert idx != -1
        # Grab a generous chunk of the section (2000 chars after the class marker)
        section_html = html[idx:idx + 2000]
        assert "<img" not in section_html
        assert "<video" not in section_html
        assert "<source" not in section_html

    def test_extended_family_relation_absent(self):
        """AC-45: no middot separator when relation missing."""
        neo = _full_neo()
        neo.metadata["extended_family"] = [
            {"name": "דוד מוטי", "headline": "ביקר", "pointer_text": "", "link_url": ""}
        ]
        html = render(neo)
        assert "דוד מוטי" in html
        # No middot after the name when relation is absent
        name_idx = html.find("דוד מוטי")
        next_div = html.find("</div>", name_idx)
        assert "&middot;" not in html[name_idx:next_div]

    def test_extended_family_between_puzzle_and_history(self):
        """AC-46: extended-family-panel between puzzle-panel and history-panel.

        Searches the HTML body (after </style>) to avoid CSS rule ordering.
        """
        body = _body(render(_full_neo()))
        puzzle_pos = body.find('puzzle-panel')
        ef_pos = body.find('extended-family-panel')
        history_pos = body.find('history-panel')
        assert puzzle_pos != -1
        assert ef_pos != -1
        assert history_pos != -1
        assert puzzle_pos < ef_pos < history_pos

    def test_extended_family_placeholder_visible(self):
        html = render(_placeholder_neo())
        assert 'extended-family-panel' in html


# ─── Character HTML / Mascot ──────────────────────────────────────────────────

class TestCharacterHtml:
    def test_character_emoji_count_decreased_by_3(self):
        """AC-47: character_emoji references decreased by 3 from original 5 → now 2.

        Original count: 5 (cover, char-placeholder in old hero grid, puzzle, survey, closer).
        After WP007-part2:
          - Old hero char-placeholder deleted (grid replacement) → -1
          - Puzzle: replaced with character_html → -1
          - Closer: replaced with character_html → -1
        Remaining: 2 (cover mascot-name + survey mini-mascot).
        """
        template_text = Path("templates/newsletter.html.j2").read_text(encoding="utf-8")
        count = template_text.count("neo.metadata.get('character_emoji'")
        assert count == 2, f"Expected 2 character_emoji usages, got {count}"

    def test_all_character_html_calls_have_safe(self):
        """AC-21/48: every {{ character_html( template call is followed by | safe."""
        template_text = Path("templates/newsletter.html.j2").read_text(encoding="utf-8")
        lines = template_text.splitlines()
        for i, line in enumerate(lines, 1):
            if "character_html(" in line and "{{" in line:
                assert "| safe" in line, (
                    f"Line {i}: character_html( call missing '| safe': {line.strip()}"
                )

    def test_character_html_renders_emoji_fallback(self):
        """AC-22: without PNG assets, emoji span rendered (not escaped markup)."""
        html = render(_full_neo())
        # character-emoji class should be present (emoji fallback)
        assert "character-emoji" in html or "character-img" in html
        # autoescape would produce &lt;span if | safe missing — must NOT appear
        assert "&lt;span" not in html
        assert "&lt;img" not in html

    def test_thinking_pose_in_puzzle(self):
        html = render(_full_neo())
        assert "character-thinking" in html

    def test_pointing_pose_in_discovery(self):
        html = render(_full_neo())
        assert "character-pointing" in html

    def test_goodbye_pose_in_closer(self):
        html = render(_full_neo())
        assert "character-goodbye" in html

    def test_hero_greeting_in_corner_hero(self):
        html = render(_full_neo())
        assert "hero-character-slot" in html

    def test_five_character_html_call_sites(self):
        """5 call sites: corner hero, shelf reading, puzzle thinking, discovery pointing, closer goodbye."""
        template_text = Path("templates/newsletter.html.j2").read_text(encoding="utf-8")
        call_sites = [l for l in template_text.splitlines() if "character_html(" in l and "{{" in l]
        assert len(call_sites) == 5, f"Expected 5 character_html call sites, got {len(call_sites)}"


# ─── Footer ───────────────────────────────────────────────────────────────────

class TestFooter:
    def test_editor_credit_present(self):
        """AC-60: עורכת: appears exactly once."""
        html = render(_full_neo())
        assert html.count("עורכת:") == 1

    def test_editor_name_default_tzlil(self):
        """AC-60: defaults to צליל when editor_name not set."""
        neo = _full_neo()
        neo.metadata.pop("editor_name", None)
        html = render(neo)
        assert "עורכת: צליל" in html

    def test_editor_name_custom(self):
        neo = _full_neo(extra_meta={"editor_name": "מיכל"})
        html = render(neo)
        assert "עורכת: מיכל" in html

    def test_rating_buttons_absent_without_wa(self):
        """AC-61: no rating-row when neither wa link nor number set."""
        neo = _full_neo()
        neo.metadata["whatsapp_number"] = ""
        neo.metadata["whatsapp_group_link"] = ""
        html = render(neo)
        assert 'class="rating-row"' not in html

    def test_rating_buttons_with_wa_number(self):
        """AC-62: 4 buttons with distinct wa.me hrefs when whatsapp_number set."""
        # Use no survey_question to avoid the survey section's own wa.me link
        neo = _full_neo(extra_meta={"whatsapp_number": "972501234567", "whatsapp_group_link": ""})
        neo.survey_question = ""  # suppress survey to avoid duplicate wa.me refs
        html = render(neo)
        assert 'class="rating-row"' in html
        # Find rating-row section
        rating_section = html.split('class="rating-row"')[1].split('</div>')[0]
        rate_hrefs = re.findall(r'href="(https://wa\.me/[^"]+)"', rating_section)
        assert len(rate_hrefs) == 4, f"Expected 4 rate hrefs, got {rate_hrefs}"
        assert len(set(rate_hrefs)) == 4, "Each rating button should have a distinct wa.me URL"

    def test_rating_buttons_count(self):
        neo = _full_neo()
        html = render(neo)
        assert html.count('class="rate-btn"') == 4
        assert html.count('id="rate-') == 4

    def test_rating_buttons_with_wa_group_link(self):
        """AC-63: 4 buttons with same group link when only group_link set."""
        neo = _full_neo(extra_meta={"whatsapp_number": "", "whatsapp_group_link": "https://chat.whatsapp.com/test"})
        neo.survey_question = ""
        html = render(neo)
        assert 'class="rating-row"' in html
        rating_section = html.split('class="rating-row"')[1].split('</div>')[0]
        hrefs = re.findall(r'href="([^"]+)"', rating_section)
        group_hrefs = [h for h in hrefs if "chat.whatsapp.com" in h]
        assert len(group_hrefs) == 4, f"Expected 4 group hrefs, got {group_hrefs}"
        assert len(set(group_hrefs)) == 1, "All 4 buttons should share the same group link"

    def test_rating_button_ids_sequential(self):
        """AC-64: rate-1 through rate-4."""
        neo = _full_neo()
        html = render(neo)
        for i in range(1, 5):
            assert f'id="rate-{i}"' in html

    def test_urlencode_applied_to_rating_text(self):
        """AC-65: Hebrew text in href is percent-encoded."""
        neo = _full_neo()
        html = render(neo)
        # Find rating buttons specifically (look for rate-btn links)
        rate_hrefs = re.findall(r'id="rate-\d+"[^>]*href="([^"]+)"', html) or \
                     re.findall(r'href="([^"]+)"[^>]*class="rate-btn"', html)
        # Fall back: just look for wa.me links in the footer area
        footer_section = html.split('class="footer-strip"')[1] if 'class="footer-strip"' in html else html
        wa_hrefs = re.findall(r'href="(https://wa\.me/[^"]+)"', footer_section)
        for href in wa_hrefs:
            if "text=" in href:
                assert "%" in href, f"Expected percent-encoding in href: {href}"


# ─── og:image ────────────────────────────────────────────────────────────────

class TestOgImage:
    def test_no_og_image_without_settings(self):
        """AC-66: no og:image meta when settings not provided."""
        html = render(_full_neo())
        assert 'property="og:image"' not in html

    def test_og_image_with_settings(self):
        """AC-67: og:image present when settings provided."""
        settings = Settings(
            schedule={},
            content={},
            newsletter={"base_url": "https://example.com/newsletter"},
            ftp={},
            distribution={},
            ai={},
            budget={},
        )
        neo = _full_neo()
        html = render(neo, settings=settings)
        assert 'property="og:image"' in html
        assert "teaser.png" in html

    def test_og_image_url_contains_date(self):
        settings = Settings(
            schedule={}, content={},
            newsletter={"base_url": "https://example.com/newsletter"},
            ftp={}, distribution={}, ai={}, budget={},
        )
        neo = _full_neo()
        html = render(neo, settings=settings)
        assert neo.date in html

    def test_og_tags_in_head(self):
        """AC-69: og tags appear before <style>."""
        settings = Settings(
            schedule={}, content={},
            newsletter={"base_url": "https://example.com/newsletter"},
            ftp={}, distribution={}, ai={}, budget={},
        )
        html = render(_full_neo(), settings=settings)
        og_pos = html.find('property="og:image"')
        style_pos = html.find("<style>")
        assert og_pos < style_pos

    def test_six_meta_tags_rendered(self):
        settings = Settings(
            schedule={}, content={},
            newsletter={"base_url": "https://example.com/newsletter"},
            ftp={}, distribution={}, ai={}, budget={},
        )
        html = render(_full_neo(), settings=settings)
        assert 'property="og:title"' in html
        assert 'property="og:type"' in html
        assert 'name="twitter:card"' in html


# ─── Dark mode CSS ────────────────────────────────────────────────────────────

class TestDarkModeCSS:
    def test_shadow_color_token_present(self):
        template_text = Path("templates/newsletter.html.j2").read_text(encoding="utf-8")
        assert "--shadow-color: var(--ink);" in template_text

    def test_dark_mode_media_query_present(self):
        template_text = Path("templates/newsletter.html.j2").read_text(encoding="utf-8")
        assert "prefers-color-scheme: dark" in template_text

    def test_member_bg_uses_css_vars(self):
        """AC-09: member_bg dict uses var(--nimrod-bg) etc. not hex."""
        template_text = Path("templates/newsletter.html.j2").read_text(encoding="utf-8")
        assert "var(--nimrod-bg)" in template_text
        assert "'nimrod': '#e6f0fa'" not in template_text

    def test_member_bg_renders_css_var_not_hex(self):
        """AC-09: rendered HTML contains var(--nimrod-bg) string, not resolved hex."""
        html = render(_full_neo())
        assert "var(--nimrod-bg)" in html

    def test_no_box_shadow_with_var_ink(self):
        """AC-53: no box-shadow declarations still using var(--ink)."""
        template_text = Path("templates/newsletter.html.j2").read_text(encoding="utf-8")
        for line in template_text.splitlines():
            if "box-shadow" in line and "var(--ink)" in line:
                pytest.fail(f"box-shadow still uses var(--ink): {line.strip()}")

    def test_dot_color_token_present(self):
        template_text = Path("templates/newsletter.html.j2").read_text(encoding="utf-8")
        assert "var(--dot-color)" in template_text

    def test_new_section_panels_have_dark_mode_overrides(self):
        """AC-58: viewing/family-table/shelf/extended-family have dark-mode backgrounds."""
        template_text = Path("templates/newsletter.html.j2").read_text(encoding="utf-8")
        dark_block = template_text.split("prefers-color-scheme: dark")[1]
        for panel in [".viewing-panel", ".family-table-panel", ".shelf-panel", ".extended-family-panel"]:
            assert panel in dark_block, f"Dark mode override missing for {panel}"


# ─── Render stability ─────────────────────────────────────────────────────────

class TestRenderStability:
    def test_sparse_neo_does_not_raise(self):
        """AC-07: render with missing metadata keys does not raise UndefinedError."""
        html = render(_sparse_neo())
        assert len(html) >= 1000

    def test_member_section_with_none_url_no_raise(self):
        """AC-08: url=None in item does not crash YouTube detection."""
        neo = _full_neo()
        neo.member_sections[0]["items"][0]["url"] = None
        html = render(neo)
        assert len(html) >= 1000

    def test_empty_discovery_no_section(self):
        """discovery-panel HTML element absent when discovery list is empty.

        Searches the HTML body (after </style>) to avoid the CSS rule.
        """
        neo = _full_neo()
        neo.discovery = []
        html = _body(render(neo))
        assert 'discovery-panel' not in html

    def test_render_with_all_5_members_and_varied_items(self):
        """Exercises corner-tiering across different item counts."""
        neo = _full_neo()
        neo.member_sections = [
            _section("nimrod", [_item("nimrod")] * 1),   # 1 item
            _section("michal", [_item("michal")] * 2),   # 2 items
            _section("shaked", [_item("shaked")] * 3),   # 3 items
            _section("maayan", [_item("maayan")] * 4),   # 4 items
            _section("tzlil", [_item("tzlil")] * 5),    # 5 items
        ]
        html = render(neo)
        assert html.count('class="member-corner') == 5

    def test_no_raw_jinja_syntax_in_output(self):
        """Catches unrendered/leaked Jinja syntax — matches qa_probe.mjs --absent check."""
        html = render(_full_neo())
        assert "{{" not in html
        assert "{%" not in html

    def test_html_size_reasonable(self):
        """Full render should produce substantial HTML."""
        html = render(_full_neo())
        assert len(html) >= 20_000, f"HTML too small: {len(html)} bytes"
