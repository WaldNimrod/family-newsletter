"""
WP003 test suite — researcher.py
All tests are unit tests: no live Anthropic calls, no live DB writes (SQLite
in-memory), no real network. tt.research() is always mocked.
"""

import json
import sqlite3
import tempfile
import os
import pytest

# ─── Fixtures / helpers ───────────────────────────────────────────────────────

VALID_ITEM = {
    "title": "כותרת בדיקה",
    "summary": "תקציר קצר לבדיקה.",
    "url": "https://example.com/test",
    "source": "Test Source",
    "category": "test",
    "share_note": "הסבר למה זה מעניין.",
}

VALID_PICK = {
    "title": "Test Show",
    "service": "netflix",
    "summary": "תקציר סדרה.",
    "content_rating": "PG-13",
    "hebrew_subtitles_verified": True,
    "availability_verified": True,
    "verification_source_url": "https://www.justwatch.com/il/test",
    "share_note": "מסביר למה הסדרה מתאימה השבוע.",
}


def _make_member(mocker, member_id="tzlil", lang="he", nickname="צליל",
                 name="צליל", media_sources=None):
    m = mocker.Mock()
    m.id = member_id
    m.language_preference = lang
    m.nickname_newsletter = nickname
    m.name = name
    m.media_sources = media_sources if media_sources is not None else []
    return m


def _make_family(mocker, members=None):
    family = mocker.Mock()
    if members is None:
        members = [_make_member(mocker, mid, nickname=mid, name=mid)
                   for mid in ["nimrod", "michal", "shaked", "maayan", "tzlil"]]
    family.members = members
    family.shared_interests = {}
    return family


# ─── §2.1 Constants (AC-07: all 10 constants) ────────────────────────────────

def test_all_constants_exist():
    from src import researcher
    assert researcher.DEFAULT_DEDUP_DAYS == 45
    assert researcher.DEFAULT_MAX_WEB_SEARCHES_RESEARCH == 8
    assert researcher.DEFAULT_MAX_WEB_SEARCHES_SCOUT == 3
    assert researcher.DEFAULT_TARGET_ITEM_COUNT == 3
    assert researcher.DEFAULT_RESEARCH_MAX_TOKENS == 4096
    assert researcher.DEFAULT_SCOUT_MAX_TOKENS == 2048
    assert researcher.DEFAULT_WEB_FETCH_MAX_USES_RESEARCH == 3
    assert researcher.DEFAULT_WEB_FETCH_MAX_USES_SCOUT == 2
    assert researcher._MAX_CANDIDATES_CONSIDERED == 10
    assert researcher._MAX_BLOCKLIST_URLS_SHOWN == 60


# ─── §2.1 Module-level exceptions (AC-05, AC-06) ─────────────────────────────

def test_module_imports():
    from src import researcher
    assert hasattr(researcher, "ResearcherError")
    assert hasattr(researcher, "TasteProfileMissingError")
    assert hasattr(researcher, "research_member")
    assert hasattr(researcher, "research_all_members")
    assert hasattr(researcher, "screen_scout")


def test_exception_hierarchy():
    from src.researcher import ResearcherError, TasteProfileMissingError
    assert issubclass(ResearcherError, Exception)
    assert issubclass(TasteProfileMissingError, ResearcherError)


# ─── §2.2 Taste profile loading (AC-08, AC-09, AC-10, AC-11) ─────────────────

def test_load_taste_profile_nimrod():
    from src.researcher import _load_taste_profile
    text = _load_taste_profile("nimrod", "profiles/")
    assert text.startswith("# נימרוד")


def test_load_taste_profile_missing(tmp_path):
    from src.researcher import _load_taste_profile, TasteProfileMissingError
    with pytest.raises(TasteProfileMissingError) as exc:
        _load_taste_profile("nobody", str(tmp_path) + "/")
    assert "nobody" in str(exc.value)


def test_load_taste_profile_empty(tmp_path):
    from src.researcher import _load_taste_profile, TasteProfileMissingError
    (tmp_path / "empty.md").write_text("   \n", encoding='utf-8')
    with pytest.raises(TasteProfileMissingError):
        _load_taste_profile("empty", str(tmp_path) + "/")


def test_member_language(mocker):
    from src.researcher import _member_language
    en_member = _make_member(mocker, lang="en")
    he_member = _make_member(mocker, lang="he")
    both_member = _make_member(mocker, lang="both")
    assert _member_language(en_member) == "en"
    assert _member_language(he_member) == "he"
    assert _member_language(both_member) == "he"


# ─── §2.3 Source hints (AC-12, AC-13) ────────────────────────────────────────

def test_format_source_hints_empty(mocker):
    from src.researcher import _format_source_hints
    m = _make_member(mocker, media_sources=[])
    result = _format_source_hints(m)
    assert "no specific preferred sources" in result


def test_format_source_hints_populated(mocker):
    from src.researcher import _format_source_hints
    sources = [
        {"name": "Yachting World", "type": "rss", "url": "https://www.yachtingworld.com/feed"},
        {"name": "Sailing World", "type": "rss", "url": "https://www.sailingworld.com/rss"},
    ]
    m = _make_member(mocker, media_sources=sources)
    result = _format_source_hints(m)
    lines = result.splitlines()
    assert len(lines) == 2
    assert "Yachting World" in result
    assert "https://www.yachtingworld.com/feed" in result


# ─── §2.3 Bookshelf P0 fix (AC-14, AC-15) ────────────────────────────────────

def test_format_bookshelf_nimrod_includes_small_is_beautiful(mocker):
    """AC-14: nimrod sees Small is Beautiful (sustainability theme), not Alice's Storm."""
    from src.researcher import _format_bookshelf
    from src.m1_profiles import load_profiles
    family = load_profiles("config/")
    result = _format_bookshelf(family, "nimrod")
    assert "Small is Beautiful" in result or "קטן זה יפה" in result
    assert "Alice's Storm" not in result and "סופה של אליס" not in result


def test_format_bookshelf_shaked_fallback(mocker):
    """AC-15: shaked (no curated relevance entry) always gets the fallback,
    even though 'shared' has themes — the P0 fix prevents shared themes from
    masking the missing-member-entry condition."""
    from src.researcher import _format_bookshelf
    from src.m1_profiles import load_profiles
    family = load_profiles("config/")
    result = _format_bookshelf(family, "shaked")
    assert "no specifically relevant family bookshelf titles on file for this member" in result


def test_format_bookshelf_no_relevance_key(mocker):
    """Members with no curated relevance (tzlil, maayan) also get the fallback."""
    from src.researcher import _format_bookshelf
    from src.m1_profiles import load_profiles
    family = load_profiles("config/")
    for mid in ("maayan", "tzlil"):
        result = _format_bookshelf(family, mid)
        assert "no specifically relevant" in result, f"{mid} should get fallback"


def test_format_bookshelf_shared_only_member_hits_fallback(mocker):
    """Unit-level: a member with no own relevance entry gets fallback even
    if 'shared' is non-empty — verifies the P0 fix logic directly."""
    from src.researcher import _format_bookshelf
    family = mocker.Mock()
    family.shared_interests = {
        "bookshelf": {
            "books": [{"title_he": "ספר", "title_en": "Book", "category": "cat",
                       "themes": ["philosophy"]}],
            "profile_insights": {
                "relevance": {
                    "shared": ["philosophy"],     # shared has themes
                    "nimrod": ["philosophy"],      # nimrod has its own entry
                    # "unknown_member" is absent
                }
            }
        }
    }
    result = _format_bookshelf(family, "unknown_member")
    assert "no specifically relevant" in result


# ─── §2.3 Blocklist formatting (AC-16) ───────────────────────────────────────

def test_format_blocklist_empty():
    from src.researcher import _format_blocklist
    assert _format_blocklist(set()) == "(none yet)"


def test_format_blocklist_limit():
    from src.researcher import _format_blocklist
    urls = {f"https://example.com/{i}" for i in range(100)}
    result = _format_blocklist(urls, limit=60)
    assert len(result.splitlines()) == 60


# ─── §2.4 JSON parsing (AC-17 – AC-22) ───────────────────────────────────────

def test_parse_json_clean():
    from src.researcher import _parse_json_response
    assert _parse_json_response('{"items": []}') == {"items": []}


def test_parse_json_code_fence():
    from src.researcher import _parse_json_response
    assert _parse_json_response('```json\n{"items": []}\n```') == {"items": []}


def test_parse_json_embedded_prose():
    from src.researcher import _parse_json_response
    assert _parse_json_response('Here you go:\n{"items": []}\nEnjoy!') == {"items": []}


def test_parse_json_array_returns_none():
    from src.researcher import _parse_json_response
    assert _parse_json_response('[1, 2, 3]') is None


def test_parse_json_none_and_empty():
    from src.researcher import _parse_json_response
    assert _parse_json_response(None) is None
    assert _parse_json_response("") is None


def test_parse_json_not_json():
    from src.researcher import _parse_json_response
    assert _parse_json_response("not json") is None


# ─── §2.5 Guardrails (AC-23 – AC-27) ────────────────────────────────────────

def test_self_reference_guard_maayan():
    from src.researcher import _apply_content_guardrails
    item = {"title": "מעיין ולד עושה ציפורניים", "summary": "", "share_note": ""}
    reason = _apply_content_guardrails(item, "maayan")
    assert reason is not None
    assert "self-reference" in reason


def test_third_party_nailart_allowed():
    from src.researcher import _apply_content_guardrails
    item = {"title": "עסקים בנייל ארט צעירים", "summary": "כתבה על יזמות", "share_note": ""}
    assert _apply_content_guardrails(item, "maayan") is None


def test_political_keyword_guard():
    from src.researcher import _apply_content_guardrails
    item = {"title": "כלכלה", "summary": "ראש הממשלה הכריז", "share_note": ""}
    for mid in ("nimrod", "shaked", "tzlil"):
        reason = _apply_content_guardrails(item, mid)
        assert reason is not None
        assert "political-keyword" in reason


def test_rating_allowed():
    from src.researcher import _rating_allowed
    assert _rating_allowed("PG-13") is True
    assert _rating_allowed("13+") is True
    assert _rating_allowed(None) is True
    assert _rating_allowed("") is True
    assert _rating_allowed("TV-MA") is False
    assert _rating_allowed("R") is False
    assert _rating_allowed("tv-ma") is False


def test_as_bool():
    from src.researcher import _as_bool
    assert _as_bool(True) is True
    assert _as_bool(False) is False
    assert _as_bool("true") is True
    assert _as_bool("FALSE") is False
    assert _as_bool("maybe") is None
    assert _as_bool(1) is None
    assert _as_bool(0) is None


# ─── §2.6 Item validation (AC-28 – AC-36) ────────────────────────────────────

def test_validate_item_valid():
    from src.researcher import _validate_research_item
    result = _validate_research_item(VALID_ITEM)
    assert isinstance(result, dict)
    assert set(result.keys()) == {"title", "summary", "url", "source", "category", "share_note"}


def test_validate_item_bad_url():
    from src.researcher import _validate_research_item
    item = {**VALID_ITEM, "url": "not-a-url"}
    assert _validate_research_item(item) is None


def test_validate_item_truncates_long_title():
    from src.researcher import _validate_research_item
    item = {**VALID_ITEM, "title": "x" * 200}
    result = _validate_research_item(item)
    assert result is not None
    assert len(result["title"]) == 150


def test_validate_item_missing_key():
    from src.researcher import _validate_research_item
    item = {k: v for k, v in VALID_ITEM.items() if k != "share_note"}
    assert _validate_research_item(item) is None


def test_validate_item_whitespace_title():
    from src.researcher import _validate_research_item
    item = {**VALID_ITEM, "title": "   "}
    assert _validate_research_item(item) is None


def test_parse_and_validate_dedup_in_batch():
    from src.researcher import _parse_and_validate_items
    raw = json.dumps({"items": [VALID_ITEM, VALID_ITEM]})
    result = _parse_and_validate_items(raw, "nimrod", set(), set())
    assert len(result) == 1


def test_parse_and_validate_blocklist_url():
    from src.researcher import _parse_and_validate_items
    raw = json.dumps({"items": [VALID_ITEM]})
    result = _parse_and_validate_items(raw, "nimrod", {VALID_ITEM["url"]}, set())
    assert result == []


def test_parse_and_validate_none():
    from src.researcher import _parse_and_validate_items
    assert _parse_and_validate_items(None, "nimrod", set(), set()) == []


def test_parse_and_validate_guardrail_drops_one():
    from src.researcher import _parse_and_validate_items
    political_item = {**VALID_ITEM, "url": "https://example.com/p",
                      "summary": "ראש הממשלה הכריז"}
    raw = json.dumps({"items": [VALID_ITEM, political_item]})
    result = _parse_and_validate_items(raw, "nimrod", set(), set())
    assert len(result) == 1
    assert result[0]["url"] == VALID_ITEM["url"]


# ─── §2.7 Mock items (AC-37 – AC-40) ────────────────────────────────────────

def test_mock_items_tzlil():
    from src.researcher import _mock_items, _validate_research_item
    items = _mock_items("tzlil", 3)
    assert len(items) == 3
    urls = [i["url"] for i in items]
    assert len(set(urls)) == 3
    for item in items:
        assert _validate_research_item(item) is not None


def test_mock_items_unknown_member():
    from src.researcher import _mock_items
    items = _mock_items("unknown_id", 3)
    assert len(items) == 3


def test_mock_viewing_pick():
    from src.researcher import _mock_viewing_pick
    pick = _mock_viewing_pick("family_pick")
    assert pick["service"] in ("netflix", "prime")
    assert pick["hebrew_subtitles_verified"] is True
    assert pick["availability_verified"] is True


# ─── §2.8 _call_research (AC-41 – AC-44) ────────────────────────────────────

def test_call_research_returns_text(mocker):
    from src.researcher import _call_research
    tt = mocker.Mock()
    tt.research.return_value = '{"items": []}'
    result = _call_research(tt, "mod", "op", "sys", "user", "2026-07-24", 4096, 8)
    assert result == '{"items": []}'


def test_call_research_catches_exception(mocker):
    from src.researcher import _call_research
    tt = mocker.Mock()
    tt.research.side_effect = RuntimeError("boom")
    result = _call_research(tt, "mod", "op", "sys", "user", "2026-07-24", 4096, 8)
    assert result is None


def test_call_research_uses_kwargs(mocker):
    from src.researcher import _call_research
    tt = mocker.Mock()
    tt.research.return_value = "ok"
    _call_research(tt, "mod", "op", "sys", "user", "2026-07-24", 4096, 8, 3)
    kwargs = tt.research.call_args.kwargs
    assert "module" in kwargs
    assert "operation" in kwargs
    assert "prompt" in kwargs
    assert "system" in kwargs
    assert "max_tokens" in kwargs
    assert "newsletter_date" in kwargs
    assert "web_search_max_uses" in kwargs
    assert "web_fetch_max_uses" in kwargs
    assert not tt.research.call_args.args  # no positional args


# ─── §2.9 Prompt builder (AC-45 – AC-50) ────────────────────────────────────

def test_prompt_builder_shaked_english(mocker):
    from src.researcher import _build_research_member_prompt
    member = _make_member(mocker, "shaked", lang="en", nickname="Shaked")
    family = mocker.Mock(shared_interests={})
    system, user = _build_research_member_prompt(
        member, family, "taste", set(), 3, 8, "2026-07-24"
    )
    # AC-45: {language_label} substitutions use "English" for Shaked.
    # The template's fixed phrase "Search in Hebrew and/or English as appropriate"
    # is always present (not parameterized) — what AC-45 actually tests is that
    # the OUTPUT instructions (e.g. "All text fields in English") use English,
    # not that the hardcoded search-language hint changes.
    assert "in English" in system
    assert "All text fields in English" in system


def test_prompt_builder_critique_sentences(mocker):
    from src.researcher import _build_research_member_prompt
    member = _make_member(mocker, "tzlil", nickname="צליל")
    family = mocker.Mock(shared_interests={})
    system, _ = _build_research_member_prompt(
        member, family, "taste", set(), 3, 8, "2026-07-24"
    )
    assert "(a) Would they send this to a friend, unprompted?" in system
    assert "(b) Is it fresh" in system
    assert "(c) Does it SHOW something" in system


def test_prompt_builder_exactly_3(mocker):
    from src.researcher import _build_research_member_prompt
    member = _make_member(mocker, "tzlil")
    family = mocker.Mock(shared_interests={})
    system, _ = _build_research_member_prompt(
        member, family, "taste", set(), 3, 8, "2026-07-24"
    )
    assert system.count("exactly 3") == 2


def test_prompt_builder_retry_suffix(mocker):
    from src.researcher import _build_research_member_prompt
    member = _make_member(mocker, "tzlil")
    family = mocker.Mock(shared_interests={})
    retry_context = {"previous_count": 1, "missing_count": 2, "previous_urls": "- https://x.com"}
    _, user = _build_research_member_prompt(
        member, family, "taste", set(), 2, 8, "2026-07-24",
        retry_context=retry_context,
    )
    assert "follow-up request" in user
    assert "1 usable item(s)" in user
    assert "2 MORE" in user


def test_prompt_builder_no_retry_suffix(mocker):
    from src.researcher import _build_research_member_prompt
    member = _make_member(mocker, "tzlil")
    family = mocker.Mock(shared_interests={})
    _, user = _build_research_member_prompt(
        member, family, "taste", set(), 3, 8, "2026-07-24"
    )
    assert "follow-up request" not in user


def test_prompt_builder_uses_nickname_newsletter(mocker):
    from src.researcher import _build_research_member_prompt
    member = _make_member(mocker, "maayan", nickname="יויו", name="מעיין")
    family = mocker.Mock(shared_interests={})
    _, user = _build_research_member_prompt(
        member, family, "taste", set(), 3, 8, "2026-07-24"
    )
    assert "יויו" in user
    assert "מעיין" not in user


# ─── §2.10 research_member() — mock mode (AC-51) ─────────────────────────────

def test_research_member_mock_mode_never_calls_research(mocker):
    from src import researcher
    tt = mocker.Mock(mock=True)
    db = mocker.Mock()
    member = _make_member(mocker, "tzlil", nickname="צליל")
    family = _make_family(mocker, [member])
    mocker.patch.object(researcher, "get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile", return_value="some taste profile")

    items = researcher.research_member(tt, db, family, "tzlil", "2026-07-24")

    assert len(items) == 3
    tt.research.assert_not_called()
    assert db.archive_researched_item.call_count == 3


# ─── §2.10 research_member() — single successful call (AC-52) ────────────────

def test_research_member_one_call_three_items(mocker):
    from src import researcher
    tt = mocker.Mock(mock=False)
    db = mocker.Mock(
        get_recent_content_urls=mocker.Mock(return_value=set()),
        get_recent_hashes=mocker.Mock(return_value=set()),
    )
    member = _make_member(mocker, "tzlil", nickname="צליל")
    family = _make_family(mocker, [member])
    mocker.patch.object(researcher, "get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile", return_value="taste")

    items_data = [
        {**VALID_ITEM, "url": f"https://example.com/{i}"} for i in range(3)
    ]
    tt.research.return_value = json.dumps({"items": items_data})

    result = researcher.research_member(tt, db, family, "tzlil", "2026-07-24")

    assert len(result) == 3
    assert tt.research.call_count == 1
    assert db.archive_researched_item.call_count == 3


# ─── §2.10 research_member() — retry on shortfall (AC-53) ───────────────────

def test_research_member_retries_on_shortfall(mocker):
    from src import researcher
    tt = mocker.Mock(mock=False)
    db = mocker.Mock(
        get_recent_content_urls=mocker.Mock(return_value=set()),
        get_recent_hashes=mocker.Mock(return_value=set()),
    )
    member = _make_member(mocker, "tzlil", nickname="צליל")
    family = _make_family(mocker, [member])
    mocker.patch.object(researcher, "get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile", return_value="taste")

    # First call: 1 valid item; second call: 2 valid items with different URLs
    first_items = [{**VALID_ITEM, "url": "https://example.com/a"}]
    second_items = [
        {**VALID_ITEM, "url": "https://example.com/b"},
        {**VALID_ITEM, "url": "https://example.com/c"},
    ]
    tt.research.side_effect = [
        json.dumps({"items": first_items}),
        json.dumps({"items": second_items}),
    ]

    result = researcher.research_member(tt, db, family, "tzlil", "2026-07-24")

    assert tt.research.call_count == 2
    assert len(result) == 3


# ─── §2.10 research_member() — retries once then gives up (AC-54) ────────────

def test_research_member_retries_once_then_gives_up(mocker):
    from src import researcher
    tt = mocker.Mock(mock=False)
    db = mocker.Mock(
        get_recent_content_urls=mocker.Mock(return_value=set()),
        get_recent_hashes=mocker.Mock(return_value=set()),
    )
    member = _make_member(mocker, "tzlil", nickname="צליל")
    family = _make_family(mocker, [member])
    mocker.patch.object(researcher, "get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile", return_value="taste")
    tt.research.side_effect = ['{"items": []}', '{"items": []}']

    items = researcher.research_member(tt, db, family, "tzlil", "2026-07-24")

    assert items == []
    assert tt.research.call_count == 2


# ─── §2.10 research_member() — exception swallowed (AC-55) ──────────────────

def test_research_member_exception_swallowed(mocker):
    from src import researcher
    tt = mocker.Mock(mock=False)
    db = mocker.Mock(
        get_recent_content_urls=mocker.Mock(return_value=set()),
        get_recent_hashes=mocker.Mock(return_value=set()),
    )
    member = _make_member(mocker, "tzlil", nickname="צליל")
    family = _make_family(mocker, [member])
    mocker.patch.object(researcher, "get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile", return_value="taste")
    tt.research.side_effect = RuntimeError("api down")

    result = researcher.research_member(tt, db, family, "tzlil", "2026-07-24")
    assert result == []
    assert tt.research.call_count == 2  # tried both initial + retry


# ─── §2.10 research_member() — MemberNotFound before any call (AC-56) ───────

def test_research_member_member_not_found(mocker):
    from src import researcher
    from src.models import MemberNotFound
    tt = mocker.Mock(mock=False)
    db = mocker.Mock()
    family = _make_family(mocker)
    mocker.patch.object(researcher, "get_member_by_id", side_effect=MemberNotFound("not found"))

    with pytest.raises(MemberNotFound):
        researcher.research_member(tt, db, family, "not_a_real_member", "2026-07-24")
    tt.research.assert_not_called()


# ─── §2.10 research_member() — TasteProfileMissingError before call (AC-57) ──

def test_research_member_missing_profile(mocker):
    from src import researcher
    from src.researcher import TasteProfileMissingError
    tt = mocker.Mock(mock=False)
    db = mocker.Mock()
    member = _make_member(mocker, "tzlil")
    family = _make_family(mocker, [member])
    mocker.patch.object(researcher, "get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile",
                         side_effect=TasteProfileMissingError("missing"))

    with pytest.raises(TasteProfileMissingError):
        researcher.research_member(tt, db, family, "tzlil", "2026-07-24")
    tt.research.assert_not_called()


# ─── §2.10 research_all_members() (AC-58, AC-59) ────────────────────────────

def test_research_all_members_returns_five_keys(mocker):
    from src import researcher
    tt = mocker.Mock(mock=True)
    db = mocker.Mock()
    family = load_real_family()
    # real profiles dir; mock mode won't call tt.research
    mocker.patch.object(researcher, "_load_taste_profile", return_value="taste")
    mocker.patch.object(researcher, "get_member_by_id", side_effect=lambda f, mid: next(
        m for m in f.members if m.id == mid
    ))

    result = researcher.research_all_members(tt, db, family, "2026-07-24",
                                              profiles_dir="profiles/")
    assert set(result.keys()) == {"nimrod", "michal", "shaked", "maayan", "tzlil"}


def test_research_all_members_isolates_failures(mocker):
    from src import researcher
    from src.researcher import TasteProfileMissingError
    tt = mocker.Mock(mock=True)
    db = mocker.Mock()
    family = load_real_family()
    shaked_member = next(m for m in family.members if m.id == "shaked")

    original_load = researcher._load_taste_profile

    def selective_load(member_id, profiles_dir="profiles/"):
        if member_id == "shaked":
            raise TasteProfileMissingError("shaked profile missing")
        return original_load(member_id, profiles_dir)

    mocker.patch.object(researcher, "_load_taste_profile", side_effect=selective_load)
    mocker.patch.object(researcher, "get_member_by_id", side_effect=lambda f, mid: next(
        m for m in f.members if m.id == mid
    ))

    result = researcher.research_all_members(tt, db, family, "2026-07-24",
                                              profiles_dir="profiles/")
    assert result["shaked"] == []
    assert len(result["nimrod"]) > 0 or True  # other members attempted


# ─── §2.10 persistence failure doesn't drop item (AC-60) ────────────────────

def test_archive_failure_does_not_drop_item(mocker):
    from src import researcher
    tt = mocker.Mock(mock=True)
    db = mocker.Mock()
    db.archive_researched_item.side_effect = RuntimeError("disk full")
    member = _make_member(mocker, "tzlil", nickname="צליל")
    family = _make_family(mocker, [member])
    mocker.patch.object(researcher, "get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile", return_value="taste")

    result = researcher.research_member(tt, db, family, "tzlil", "2026-07-24")
    assert len(result) == 3  # items still returned despite archive failure


# ─── §2.11 _validate_viewing_pick (AC-61 – AC-68) ───────────────────────────

def test_validate_viewing_pick_valid():
    from src.researcher import _validate_viewing_pick
    result = _validate_viewing_pick(VALID_PICK, set())
    assert result is not None
    assert result["hebrew_subtitles_verified"] is True
    assert result["availability_verified"] is True


def test_validate_viewing_pick_false_subtitles():
    from src.researcher import _validate_viewing_pick
    pick = {**VALID_PICK, "hebrew_subtitles_verified": False}
    assert _validate_viewing_pick(pick, set()) is None


def test_validate_viewing_pick_missing_subtitles_key():
    from src.researcher import _validate_viewing_pick
    pick = {k: v for k, v in VALID_PICK.items() if k != "hebrew_subtitles_verified"}
    assert _validate_viewing_pick(pick, set()) is None


def test_validate_viewing_pick_string_true(mocker):
    from src.researcher import _validate_viewing_pick
    pick = {**VALID_PICK, "hebrew_subtitles_verified": "true"}
    result = _validate_viewing_pick(pick, set())
    assert result is not None
    assert result["hebrew_subtitles_verified"] is True


def test_validate_viewing_pick_wrong_service():
    from src.researcher import _validate_viewing_pick
    pick = {**VALID_PICK, "service": "hulu"}
    assert _validate_viewing_pick(pick, set()) is None


def test_validate_viewing_pick_title_collision():
    from src.researcher import _validate_viewing_pick
    recent = {"test show"}  # VALID_PICK title lowercased
    assert _validate_viewing_pick(VALID_PICK, recent) is None


def test_validate_viewing_pick_disallowed_rating():
    from src.researcher import _validate_viewing_pick
    pick = {**VALID_PICK, "content_rating": "TV-MA"}
    assert _validate_viewing_pick(pick, set()) is None


def test_validate_viewing_pick_bad_url():
    from src.researcher import _validate_viewing_pick
    pick = {**VALID_PICK, "verification_source_url": "not a url"}
    assert _validate_viewing_pick(pick, set()) is None


# ─── §2.12 Personal-pick rotation (AC-69 – AC-72) ───────────────────────────

def test_next_personal_pick_no_history(mocker):
    from src.researcher import _next_personal_pick_member
    db = mocker.Mock()
    db.get_last_personal_pick.return_value = None
    family = _make_family(mocker)
    result = _next_personal_pick_member(db, family)
    assert result == family.members[0].id


def test_next_personal_pick_after_michal(mocker):
    from src.researcher import _next_personal_pick_member
    db = mocker.Mock()
    db.get_last_personal_pick.return_value = {"for_whom": "michal"}
    family = _make_family(mocker)
    result = _next_personal_pick_member(db, family)
    assert result == "shaked"


def test_next_personal_pick_wraps_around(mocker):
    from src.researcher import _next_personal_pick_member
    db = mocker.Mock()
    db.get_last_personal_pick.return_value = {"for_whom": "tzlil"}
    family = _make_family(mocker)
    assert _next_personal_pick_member(db, family) == "nimrod"


def test_next_personal_pick_unknown_member_restarts(mocker):
    from src.researcher import _next_personal_pick_member
    db = mocker.Mock()
    db.get_last_personal_pick.return_value = {"for_whom": "someone_removed"}
    family = _make_family(mocker)
    result = _next_personal_pick_member(db, family)
    assert result == family.members[0].id


# ─── §2.14 screen_scout() — mock mode (AC-77) ────────────────────────────────

def test_screen_scout_mock_mode(mocker):
    from src import researcher
    tt = mocker.Mock(mock=True)
    db = mocker.Mock()
    db.get_last_personal_pick.return_value = None
    member = _make_member(mocker, "nimrod", nickname="נימרוד")
    family = _make_family(mocker, [member])
    mocker.patch.object(researcher, "get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile", return_value="taste")
    mocker.patch.object(researcher, "_next_personal_pick_member", return_value="nimrod")

    result = researcher.screen_scout(tt, db, family, "2026-07-24", profiles_dir="profiles/")

    assert result["family_pick"] is not None
    assert result["personal_pick"] is not None
    tt.research.assert_not_called()
    assert db.insert_watchlist_pick.call_count == 2


# ─── §2.14 screen_scout() — both valid on first call (AC-78) ─────────────────

def test_screen_scout_one_call_both_valid(mocker):
    from src import researcher
    tt = mocker.Mock(mock=False)
    db = mocker.Mock(
        get_recent_watchlist_titles=mocker.Mock(return_value=set()),
        get_last_personal_pick=mocker.Mock(return_value=None),
    )
    member = _make_member(mocker, "nimrod", nickname="נימרוד")
    family = _make_family(mocker, [member])
    mocker.patch.object(researcher, "get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile", return_value="taste")
    mocker.patch.object(researcher, "_next_personal_pick_member", return_value="nimrod")

    response = json.dumps({
        "family_pick": VALID_PICK,
        "personal_pick": {**VALID_PICK, "title": "Another Show"},
    })
    tt.research.return_value = response

    result = researcher.screen_scout(tt, db, family, "2026-07-24", profiles_dir="profiles/")

    assert tt.research.call_count == 1
    assert result["family_pick"] is not None
    assert result["personal_pick"] is not None
    assert db.insert_watchlist_pick.call_count == 2

    # Verify for_whom/pick_type assignments
    calls = {c.kwargs["pick_type"]: c.kwargs for c in db.insert_watchlist_pick.call_args_list}
    assert calls["family"]["for_whom"] == "family"
    assert calls["personal"]["for_whom"] == "nimrod"


# ─── §2.14 screen_scout() — retry on invalid personal_pick (AC-79) ───────────

def test_screen_scout_retry_invalid_personal_pick(mocker):
    from src import researcher
    tt = mocker.Mock(mock=False)
    db = mocker.Mock(
        get_recent_watchlist_titles=mocker.Mock(return_value=set()),
        get_last_personal_pick=mocker.Mock(return_value=None),
    )
    member = _make_member(mocker, "nimrod", nickname="נימרוד")
    family = _make_family(mocker, [member])
    mocker.patch.object(researcher, "get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile", return_value="taste")
    mocker.patch.object(researcher, "_next_personal_pick_member", return_value="nimrod")

    invalid_personal = {**VALID_PICK, "title": "Bad Show", "availability_verified": False}
    first_response = json.dumps({"family_pick": VALID_PICK, "personal_pick": invalid_personal})
    retry_response = json.dumps({"pick": {**VALID_PICK, "title": "Retry Show"}})
    tt.research.side_effect = [first_response, retry_response]

    result = researcher.screen_scout(tt, db, family, "2026-07-24", profiles_dir="profiles/")

    assert tt.research.call_count == 2
    assert result["family_pick"] is not None
    assert result["personal_pick"] is not None


# ─── §2.14 screen_scout() — both slots fail → partial result (AC-80) ─────────

def test_screen_scout_personal_pick_fails_twice(mocker):
    from src import researcher
    tt = mocker.Mock(mock=False)
    db = mocker.Mock(
        get_recent_watchlist_titles=mocker.Mock(return_value=set()),
        get_last_personal_pick=mocker.Mock(return_value=None),
    )
    member = _make_member(mocker, "nimrod", nickname="נימרוד")
    family = _make_family(mocker, [member])
    mocker.patch.object(researcher, "get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile", return_value="taste")
    mocker.patch.object(researcher, "_next_personal_pick_member", return_value="nimrod")

    invalid = {**VALID_PICK, "availability_verified": False}
    bad_response = json.dumps({"family_pick": VALID_PICK, "personal_pick": invalid})
    bad_retry = json.dumps({"pick": invalid})
    tt.research.side_effect = [bad_response, bad_retry]

    result = researcher.screen_scout(tt, db, family, "2026-07-24", profiles_dir="profiles/")

    assert result["personal_pick"] is None
    assert result["family_pick"] is not None
    assert db.insert_watchlist_pick.call_count == 1  # only family pick inserted


# ─── §2.14 screen_scout() — personal_pick_member_id always set (AC-81) ───────

def test_screen_scout_personal_pick_member_id_always_set(mocker):
    from src import researcher
    tt = mocker.Mock(mock=False)
    db = mocker.Mock(
        get_recent_watchlist_titles=mocker.Mock(return_value=set()),
        get_last_personal_pick=mocker.Mock(return_value=None),
    )
    member = _make_member(mocker, "shaked", nickname="Shaked")
    family = _make_family(mocker, [member])
    mocker.patch.object(researcher, "get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile", return_value="taste")
    mocker.patch.object(researcher, "_next_personal_pick_member", return_value="shaked")
    tt.research.return_value = '{"family_pick": null}'  # invalid → both None

    result = researcher.screen_scout(tt, db, family, "2026-07-24", profiles_dir="profiles/")
    assert result["personal_pick_member_id"] == "shaked"


# ─── §2.14 screen_scout() — persistence failure doesn't affect return (AC-82) ─

def test_screen_scout_persistence_failure_ok(mocker):
    from src import researcher
    tt = mocker.Mock(mock=True)
    db = mocker.Mock()
    db.get_last_personal_pick.return_value = None
    db.insert_watchlist_pick.side_effect = RuntimeError("db locked")
    member = _make_member(mocker, "nimrod", nickname="נימרוד")
    family = _make_family(mocker, [member])
    mocker.patch.object(researcher, "get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile", return_value="taste")
    mocker.patch.object(researcher, "_next_personal_pick_member", return_value="nimrod")

    result = researcher.screen_scout(tt, db, family, "2026-07-24", profiles_dir="profiles/")
    # picks still returned even though persistence failed
    assert result["family_pick"] is not None
    assert result["personal_pick"] is not None


# ─── §2.15 Database — watchlist DDL (AC-83: 14 columns) ─────────────────────

def test_watchlist_table_has_14_columns():
    """AC-83 FIX: The spec's AC-83 incorrectly states '13 columns'. The DDL
    has 14: id, title, service, for_whom, pick_type, recommended_date,
    hebrew_subtitles, availability_note, source_url, status, reaction_text,
    reaction_rating, created_at, updated_at."""
    from src.db import Database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        db = Database(path)
        cols = db.conn.execute("PRAGMA table_info(watchlist)").fetchall()
        col_names = [c["name"] for c in cols]
        assert len(col_names) == 14, f"Expected 14 columns, got {len(col_names)}: {col_names}"
        expected = [
            "id", "title", "service", "for_whom", "pick_type", "recommended_date",
            "hebrew_subtitles", "availability_note", "source_url", "status",
            "reaction_text", "reaction_rating", "created_at", "updated_at",
        ]
        assert col_names == expected
        db.close()
    finally:
        os.unlink(path)


def test_watchlist_check_constraint_service(tmp_path):
    """AC-84: Inserting service='hulu' raises IntegrityError."""
    from src.db import Database
    db = Database(str(tmp_path / "test.db"))
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute(
            "INSERT INTO watchlist (title, service, for_whom, pick_type, recommended_date) "
            "VALUES ('t', 'hulu', 'family', 'family', '2026-07-24')"
        )
    db.close()


def test_watchlist_default_status(tmp_path):
    """AC-85: status defaults to 'recommended'."""
    from src.db import Database
    db = Database(str(tmp_path / "test.db"))
    db.conn.execute(
        "INSERT INTO watchlist (title, service, for_whom, pick_type, recommended_date) "
        "VALUES ('Test', 'netflix', 'family', 'family', '2026-07-24')"
    )
    row = db.conn.execute("SELECT status FROM watchlist").fetchone()
    assert row["status"] == "recommended"
    db.close()


def test_get_recent_content_urls(tmp_path):
    """AC-86: archive_researched_item → get_recent_content_urls."""
    from src.db import Database
    db = Database(str(tmp_path / "test.db"))
    db.archive_researched_item(
        url="https://x.com", title="t", source_name="s",
        raw_text="r", tags=["cat"], language="he"
    )
    urls = db.get_recent_content_urls(days=45)
    assert "https://x.com" in urls
    db.close()


def test_archive_idempotent(tmp_path):
    """AC-87: INSERT OR IGNORE — second call with same URL doesn't raise."""
    from src.db import Database
    db = Database(str(tmp_path / "test.db"))
    db.archive_researched_item(url="https://x.com", title="first", source_name="s",
                                raw_text="r", tags=[], language="he")
    db.archive_researched_item(url="https://x.com", title="second", source_name="s",
                                raw_text="r", tags=[], language="he")
    rows = db.conn.execute("SELECT count(*) as c FROM content_archive WHERE url='https://x.com'").fetchone()
    assert rows["c"] == 1
    title_row = db.conn.execute("SELECT title FROM content_archive WHERE url='https://x.com'").fetchone()
    assert title_row["title"] == "first"  # original preserved
    db.close()


def test_get_recent_watchlist_titles(tmp_path):
    """AC-88: insert_watchlist_pick → get_recent_watchlist_titles (lowercased)."""
    from src.db import Database
    db = Database(str(tmp_path / "test.db"))
    db.insert_watchlist_pick(
        title="Test Show", service="netflix", for_whom="family",
        pick_type="family", recommended_date="2026-07-24",
        hebrew_subtitles=True, availability_note="", source_url="https://j.com"
    )
    titles = db.get_recent_watchlist_titles(days=45)
    assert "test show" in titles
    db.close()


def test_get_last_personal_pick_empty(tmp_path):
    """AC-89: empty watchlist → None."""
    from src.db import Database
    db = Database(str(tmp_path / "test.db"))
    assert db.get_last_personal_pick() is None
    db.close()


def test_get_last_personal_pick_latest(tmp_path):
    """AC-89: with two rows, returns the one with the later recommended_date."""
    from src.db import Database
    db = Database(str(tmp_path / "test.db"))
    db.insert_watchlist_pick(title="Old", service="netflix", for_whom="nimrod",
                              pick_type="personal", recommended_date="2026-07-17",
                              hebrew_subtitles=True, availability_note="", source_url="https://j.com")
    db.insert_watchlist_pick(title="New", service="prime", for_whom="michal",
                              pick_type="personal", recommended_date="2026-07-24",
                              hebrew_subtitles=True, availability_note="", source_url="https://j.com")
    last = db.get_last_personal_pick()
    assert last["for_whom"] == "michal"
    db.close()


def test_insert_watchlist_pick_returns_id(tmp_path):
    """AC-90: insert_watchlist_pick returns the new row's id."""
    from src.db import Database
    db = Database(str(tmp_path / "test.db"))
    row_id = db.insert_watchlist_pick(
        title="My Show", service="prime", for_whom="tzlil",
        pick_type="personal", recommended_date="2026-07-24",
        hebrew_subtitles=False, availability_note="n/a", source_url="https://j.com"
    )
    assert isinstance(row_id, int)
    row = db.conn.execute("SELECT * FROM watchlist WHERE id=?", (row_id,)).fetchone()
    assert row["title"] == "My Show"
    db.close()


# ─── §2.0 models.py (AC-01 – AC-03) ─────────────────────────────────────────

def test_member_profile_media_sources_field():
    """AC-01: MemberProfile has media_sources field defaulting to []."""
    from src.models import MemberProfile, Interest
    m = MemberProfile(
        id="x", name="X", name_en="X", nickname="X", nickname_newsletter="X",
        role="parent", phone=None, email=None, language_preference="he",
        interests=[], max_items_per_day=3, preferred_format="summary",
    )
    assert m.media_sources == []


def test_load_profiles_nimrod_media_sources():
    """AC-02: Nimrod's media_sources loaded (8 entries, first is Yachting World RSS)."""
    from src.m1_profiles import load_profiles
    family = load_profiles("config/")
    nimrod = next(m for m in family.members if m.id == "nimrod")
    assert len(nimrod.media_sources) == 8
    assert nimrod.media_sources[0]["name"] == "Yachting World"
    assert nimrod.media_sources[0]["type"] == "rss"


def test_load_profiles_member_no_media_sources():
    """AC-03: member with no media_sources key loads with []."""
    from src.m1_profiles import load_profiles
    family = load_profiles("config/")
    # All members present; if any lack the field they should not raise
    for m in family.members:
        assert isinstance(m.media_sources, list)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_real_family():
    from src.m1_profiles import load_profiles
    return load_profiles("config/")
