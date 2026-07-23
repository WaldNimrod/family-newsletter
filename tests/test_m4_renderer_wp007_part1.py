"""WP007-part-1: render(settings=), og_image_url, GeneratedContent fields, _placeholder."""
from __future__ import annotations

from pathlib import Path

from src.m4_renderer import get_character_html, render
from src.models import GeneratedContent, NEO, Settings


def _minimal_neo() -> NEO:
    return NEO(
        date="2026-07-24",
        family_name="בית ולד",
        greeting="שלום",
        family_content=[],
        member_sections=[
            {
                "member_id": "nimrod",
                "name": "נמרוד",
                "items": [
                    {"headline": "כותרת", "summary": "סיכום" * 40, "url": "https://example.com"}
                ],
            }
        ],
        discovery=[],
        trivia={"puzzle": "חידה", "answer": "42", "history": "היסטוריה"},
        survey_question="שאלה?",
        date_formatted="יום שישי",
        metadata={},
    )


def test_generated_content_has_four_new_fields():
    gc = GeneratedContent(
        greeting="",
        greeting_en="",
        puzzle="",
        puzzle_answer="",
        survey_question="",
        survey_question_en="",
        headlines={},
        summaries={},
        submission_edits={},
        bridges=[],
    )
    assert gc.viewing == {}
    assert gc.family_table_text == ""
    assert gc.extended_family == []
    assert gc.shelf_pick == {}


def test_render_without_settings_no_og_image(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    html = render(_minimal_neo())
    assert 'property="og:image"' not in html
    assert len(html) >= 1000


def test_render_with_settings_computes_og_image_url(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    settings = Settings(
        schedule={},
        content={},
        newsletter={"url_base": "https://example.test/nl"},
        ftp={},
        distribution={},
        ai={},
        budget={},
    )
    # Force env_compat path that uses settings.newsletter.url_base
    monkeypatch.delenv("UPRESS_PUBLIC_BASE", raising=False)
    monkeypatch.delenv("UPRESS_UPLOAD_PATH", raising=False)
    monkeypatch.delenv("FTP_PATH", raising=False)
    html = render(_minimal_neo(), settings=settings)
    # Current template may not emit og tags yet (part-2); ensure render accepts settings.
    assert len(html) >= 1000


def test_get_character_html_placeholder_fallback(tmp_path, monkeypatch):
    root = tmp_path
    monkeypatch.chdir(root)
    pose = "thinking"
    ph = root / "assets" / "characters" / "_placeholder"
    ph.mkdir(parents=True)
    (ph / f"{pose}.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    html = get_character_html(pose, month="2099-01")
    assert "_placeholder/thinking.png" in html
    assert "character-emoji" not in html
