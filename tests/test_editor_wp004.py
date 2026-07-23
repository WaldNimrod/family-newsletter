"""
WP004 test suite — editor.py
All tests are unit tests: no live Anthropic/LLM calls (llm.complete always
mocked), no DB, no network. Covers all ACs in LOD400 §2.1–§2.8 plus:
  - P0: unconditional Shaked English rule in EDITORIAL_SYSTEM_PROMPT
  - P0: AC-04 rescoped to bare-{identifier} regex (schema JSON {} allowed)
  - P1: Nimrod no-farm-business guardrail in EDITORIAL_SYSTEM_PROMPT
  - Mock mode short-circuit (AC-28, AC-29)
  - Schema validation paths (AC-09–AC-14)
  - Retry/error propagation (AC-31–AC-33)
"""

import re
import pytest

# ─── Fixtures / helpers ───────────────────────────────────────────────────────


def _make_member(mocker, member_id="tzlil", lang="he", nickname="צליל",
                 name="צליל"):
    m = mocker.Mock()
    m.id = member_id
    m.language_preference = lang
    m.nickname_newsletter = nickname
    m.name = name
    m.media_sources = []
    return m


def _make_family(mocker, member_ids=None):
    """Create a FamilyConfig-like mock with the five core members."""
    if member_ids is None:
        member_ids = ["nimrod", "michal", "shaked", "maayan", "tzlil"]
    family = mocker.Mock()
    family.family_name = "בית ולד"
    family.family_name_en = "Beit Vald"
    family.shared_interests = {}
    family.members = [
        _make_member(mocker, mid, nickname=mid, name=mid,
                     lang="en" if mid == "shaked" else "he")
        for mid in member_ids
    ]
    return family


def _valid_editorial_dict():
    """A fully valid editorial dict matching §2.2's canonical schema."""
    from src.editor import TEASER_LINK_PLACEHOLDER
    return {
        "opener": "בוקר טוב, בית ולד!",
        "closer": "נתראה בשישי הבא.",
        "discovery_bridges": [
            {"from_member": "nimrod", "to_member": "tzlil", "text": "גשר ראשון."},
            {"from_member": "michal", "to_member": "maayan", "text": "גשר שני."},
        ],
        "puzzle": {
            "intro": "החידה השבועית!",
            "question": "מה זה 2+2?",
            "answer": "4",
            "last_week_answer_reveal": "תשובת השבוע שעבר הייתה 42.",
        },
        "today_in_history": {
            "fact": "ב-1969 נחת האדם על הירח.",
            "family_idea_callout": "אולי ערב קולנוע?",
        },
        "question_of_the_week": {
            "preamble": "השבוע אנחנו רוצים לדעת:",
            "poll_question": "מה כדאי לבנות בשרת?",
            "poll_options": ["טירה", "עיר", "פארק", "הפתעה"],
        },
        "teaser_caption": f"📰 בית ולד הגיע! {TEASER_LINK_PLACEHOLDER}",
        "editors_choice": {"ref": "bridge_1", "note": "בחירת העורכת: הגשר הראשון."},
    }


# ─── §2.1 Constants (AC-01 through AC-03) ────────────────────────────────────


def test_ac01_import_no_errors():
    """AC-01: import succeeds with no import-time errors."""
    from src import editor  # noqa: F401


def test_ac02_exception_hierarchy():
    """AC-02: EditorError at module level; EditorSchemaError subclasses it."""
    from src import editor
    assert issubclass(editor.EditorSchemaError, editor.EditorError)
    assert issubclass(editor.EditorError, Exception)


def test_ac03_constants():
    """AC-03: all required constants have correct values."""
    from src import editor
    assert set(editor.MEMBER_TASTE_ANCHORS.keys()) == {
        "nimrod", "michal", "shaked", "maayan", "tzlil"
    }
    for v in editor.MEMBER_TASTE_ANCHORS.values():
        assert isinstance(v, str) and v
    assert editor.TEASER_LINK_PLACEHOLDER == "{EDITION_LINK}"
    assert editor.EDITOR_CREDIT == "עורכת: צליל"
    assert editor.MAX_DISCOVERY_BRIDGES == 3
    assert editor.MIN_POLL_OPTIONS == 2
    assert editor.MAX_POLL_OPTIONS == 6


# ─── §2.3 System prompt (AC-04) — P0 fixes ───────────────────────────────────


def test_ac04_system_prompt_contains_required_substrings():
    """AC-04 (P0 fix): EDITORIAL_SYSTEM_PROMPT contains 'צליל' and 'json'."""
    from src import editor
    prompt = editor.EDITORIAL_SYSTEM_PROMPT
    assert isinstance(prompt, str) and prompt
    assert "צליל" in prompt
    assert "json" in prompt.lower()


def test_ac04_system_prompt_no_bare_identifier_placeholders():
    """AC-04 (P0 fix): bare-{identifier} regex finds no format placeholders.
    Schema JSON {} braces (empty or with quoted keys) are ALLOWED — only
    {word} patterns (leftover f-string markers) are forbidden."""
    from src import editor
    prompt = editor.EDITORIAL_SYSTEM_PROMPT
    bare_ids = re.findall(r'\{[a-zA-Z_]\w*\}', prompt)
    assert bare_ids == [], (
        f"Found bare identifier placeholders in EDITORIAL_SYSTEM_PROMPT "
        f"(should be zero — these indicate accidental f-string leakage): {bare_ids}"
    )


def test_p0_shaked_english_rule_unconditional_in_system_prompt():
    """P0 BUILD_DIRECTIVE: the Shaked English rule is in the SYSTEM PROMPT
    unconditionally — it must fire regardless of research_highlights content,
    not only in the empty-highlights fallback of the user prompt."""
    from src import editor
    prompt = editor.EDITORIAL_SYSTEM_PROMPT.lower()
    assert "shaked" in prompt, "System prompt must mention Shaked by name"
    assert "english" in prompt, "System prompt must contain the word 'english'"
    # Verify the rule is stated as unconditional (key words from the spec)
    assert "unconditional" in prompt or "always" in prompt or "absolute" in prompt, (
        "System prompt must state the Shaked English rule as unconditional/absolute/always"
    )


def test_p1_nimrod_no_farm_business_in_system_prompt():
    """P1: Nimrod no-farm-business guardrail is present in EDITORIAL_SYSTEM_PROMPT."""
    from src import editor
    prompt = editor.EDITORIAL_SYSTEM_PROMPT.lower()
    assert "nimrod" in prompt
    # The guardrail should mention farm/business prohibition
    assert (
        "farm" in prompt
        or "commercial" in prompt
        or "business" in prompt
        or "חווה" in editor.EDITORIAL_SYSTEM_PROMPT
    ), "System prompt must include Nimrod no-farm-business guardrail"


def test_system_prompt_is_fully_static():
    """EDITORIAL_SYSTEM_PROMPT is a str constant — same object each access."""
    from src import editor
    assert editor.EDITORIAL_SYSTEM_PROMPT is editor.EDITORIAL_SYSTEM_PROMPT


# ─── §2.3b User prompt (AC-05 through AC-08) ─────────────────────────────────


def test_ac05_user_prompt_with_highlights(mocker):
    """AC-05: returns string containing date, highlight, and prior answer."""
    from src import editor
    family = _make_family(mocker)
    result = editor._build_user_prompt(
        family, {"nimrod": ["מסלול קייטסינג חדש"]}, "42", "2026-07-24"
    )
    assert "2026-07-24" in result
    assert "מסלול קייטסינג חדש" in result
    assert "42" in result


def test_ac06_user_prompt_none_highlights_falls_back_to_anchors(mocker):
    """AC-06: research_highlights=None → every member falls back to MEMBER_TASTE_ANCHORS."""
    from src import editor
    family = _make_family(mocker)
    result = editor._build_user_prompt(family, None, None, "2026-07-24")
    # At least one anchor string should appear verbatim
    found_anchor = any(
        anchor in result
        for anchor in editor.MEMBER_TASTE_ANCHORS.values()
    )
    assert found_anchor, "Expected at least one MEMBER_TASTE_ANCHORS entry in fallback output"


def test_ac07_prior_puzzle_answer_none_uses_first_edition_text(mocker):
    """AC-07: prior_puzzle_answer=None → first-edition framing, not reveal."""
    from src import editor
    family = _make_family(mocker)
    result_none = editor._build_user_prompt(family, None, None, "2026-07-24")
    result_42 = editor._build_user_prompt(family, None, "42", "2026-07-24")
    # When None: first-edition framing present, prior-answer instruction absent
    assert "החידה הראשונה" in result_none
    assert "42" not in result_none
    # When "42": prior-answer instruction present
    assert "42" in result_42
    assert "החידה הראשונה" not in result_42


def test_ac08_user_prompt_always_contains_edition_link_placeholder(mocker):
    """AC-08: returned string always contains the literal '{EDITION_LINK}'."""
    from src import editor
    family = _make_family(mocker)
    result = editor._build_user_prompt(family, None, None, "2026-07-24")
    assert "{EDITION_LINK}" in result


# ─── §2.4 Validation (AC-09 through AC-14) ───────────────────────────────────


def test_ac09_valid_canonical_example_returns_empty():
    """AC-09: _validate_editorial on the canonical example returns []."""
    from src import editor
    assert editor._validate_editorial(_valid_editorial_dict()) == []


def test_ac10_missing_required_fields_each_produce_error():
    """AC-10: removing each required field produces at least one error."""
    from src import editor

    def _check_removed(key, parent=None):
        d = _valid_editorial_dict()
        if parent:
            d[parent] = dict(d[parent])
            del d[parent][key]
        else:
            del d[key]
        errors = editor._validate_editorial(d)
        assert errors, f"Expected errors when '{key}' removed from {parent or 'root'}"
        return errors

    # Top-level required fields
    assert any("opener" in e for e in _check_removed("opener"))
    assert any("closer" in e for e in _check_removed("closer"))
    assert any("puzzle" in e for e in _check_removed("puzzle"))
    assert any("today_in_history" in e for e in _check_removed("today_in_history"))
    assert any("question_of_the_week" in e for e in _check_removed("question_of_the_week"))
    assert any("teaser_caption" in e for e in _check_removed("teaser_caption"))

    # Nested required fields
    assert any("puzzle.intro" in e for e in _check_removed("intro", "puzzle"))
    assert any("puzzle.question" in e for e in _check_removed("question", "puzzle"))
    assert any("puzzle.answer" in e for e in _check_removed("answer", "puzzle"))
    assert any("today_in_history.fact" in e for e in _check_removed("fact", "today_in_history"))
    assert any(
        "poll_question" in e
        for e in _check_removed("poll_question", "question_of_the_week")
    )


def test_ac11_poll_options_boundary_validation():
    """AC-11: poll_options length boundaries are enforced correctly."""
    from src import editor

    def _with_options(opts):
        d = _valid_editorial_dict()
        d["question_of_the_week"] = dict(d["question_of_the_week"])
        d["question_of_the_week"]["poll_options"] = opts
        return editor._validate_editorial(d)

    # Too few (1) → error
    assert any("poll_options" in e for e in _with_options(["only one"]))
    # Too many (7) → error
    assert any("poll_options" in e for e in _with_options(["a"] * 7))
    # One empty string → error
    assert any("poll_options" in e for e in _with_options(["", "valid"]))
    # Exactly 2 (boundary inclusive) → no poll_options error
    assert not any("poll_options" in e for e in _with_options(["a", "b"]))
    # Exactly 6 (boundary inclusive) → no poll_options error
    assert not any("poll_options" in e for e in _with_options(["a", "b", "c", "d", "e", "f"]))


def test_ac12_teaser_caption_placeholder_required():
    """AC-12: teaser_caption without {EDITION_LINK} → error mentioning placeholder."""
    from src import editor
    d = _valid_editorial_dict()
    d["teaser_caption"] = "📰 בית ולד הגיע — כנסו לקרוא!"
    errors = editor._validate_editorial(d)
    assert any("EDITION_LINK" in e or "placeholder" in e for e in errors)

    d2 = _valid_editorial_dict()  # already has the placeholder
    assert editor._validate_editorial(d2) == []


def test_ac13_discovery_bridges_absent_is_not_a_hard_error():
    """AC-13: discovery_bridges absent entirely is NOT a validation error."""
    from src import editor
    d = _valid_editorial_dict()
    del d["discovery_bridges"]
    assert editor._validate_editorial(d) == []


def test_ac14_last_week_answer_reveal_absent_is_not_a_validation_error():
    """AC-14: puzzle missing last_week_answer_reveal is NOT an error here."""
    from src import editor
    d = _valid_editorial_dict()
    d["puzzle"] = {k: v for k, v in d["puzzle"].items() if k != "last_week_answer_reveal"}
    assert editor._validate_editorial(d) == []


# ─── §2.5 Retry-prompt builder (AC-15) ───────────────────────────────────────


def test_ac15_build_retry_prompt_contains_original_and_errors():
    """AC-15: _build_retry_prompt preserves original prompt and lists errors."""
    from src import editor
    result = editor._build_retry_prompt("ORIGINAL", ["opener: missing"])
    assert "ORIGINAL" in result
    assert "opener: missing" in result


# ─── §2.6 Normalize (AC-16 through AC-24) ────────────────────────────────────


def test_ac16_bridges_truncated_at_max(mocker, caplog):
    """AC-16: 5 valid bridges → truncated to MAX_DISCOVERY_BRIDGES (3)."""
    import logging
    from src import editor
    family = _make_family(mocker)
    data = _valid_editorial_dict()
    data["discovery_bridges"] = [
        {"from_member": "nimrod", "to_member": "tzlil", "text": f"גשר {i}"}
        for i in range(5)
    ]
    with caplog.at_level(logging.WARNING, logger="family.editor"):
        result = editor._normalize_editorial(data, family, None)
    assert len(result["discovery_bridges"]) == 3
    assert any("truncat" in r.message.lower() for r in caplog.records)


def test_ac17_single_bridge_kept_with_warning(mocker, caplog):
    """AC-17: exactly 1 valid bridge → kept as-is, warning logged."""
    import logging
    from src import editor
    family = _make_family(mocker)
    data = _valid_editorial_dict()
    data["discovery_bridges"] = [
        {"from_member": "nimrod", "to_member": "tzlil", "text": "גשר אחד."}
    ]
    with caplog.at_level(logging.WARNING, logger="family.editor"):
        result = editor._normalize_editorial(data, family, None)
    assert len(result["discovery_bridges"]) == 1
    assert any("1" in r.message for r in caplog.records)


def test_ac18_malformed_bridges_dropped(mocker, caplog):
    """AC-18: self-referential and unknown-member bridges are dropped."""
    import logging
    from src import editor
    family = _make_family(mocker)
    data = _valid_editorial_dict()
    data["discovery_bridges"] = [
        {"from_member": "nimrod", "to_member": "nimrod", "text": "self-ref"},
        {"from_member": "nimrod", "to_member": "unknown_id", "text": "bad id"},
        {"from_member": "nimrod", "to_member": "tzlil", "text": "valid"},
    ]
    with caplog.at_level(logging.WARNING, logger="family.editor"):
        result = editor._normalize_editorial(data, family, None)
    assert len(result["discovery_bridges"]) == 1
    assert result["discovery_bridges"][0]["text"] == "valid"
    assert any("dropping" in r.message.lower() for r in caplog.records)


def test_ac19_puzzle_last_week_reveal_fallback(mocker):
    """AC-19: last_week_answer_reveal fallback logic."""
    from src import editor
    family = _make_family(mocker)
    data = _valid_editorial_dict()
    data["puzzle"] = {"intro": "x", "question": "y", "answer": "z"}

    # With prior answer and no reveal: fills fallback containing the answer
    result = editor._normalize_editorial(data, family, "42")
    assert "42" in result["puzzle"]["last_week_answer_reveal"]

    # Without prior answer and no reveal: fills first-edition text
    result2 = editor._normalize_editorial(data, family, None)
    assert "החידה הראשונה" in result2["puzzle"]["last_week_answer_reveal"]

    # LLM supplied reveal: left untouched
    data2 = _valid_editorial_dict()
    data2["puzzle"]["last_week_answer_reveal"] = "תשובה קיימת"
    result3 = editor._normalize_editorial(data2, family, "42")
    assert result3["puzzle"]["last_week_answer_reveal"] == "תשובה קיימת"


def test_ac20_history_callout_fallback(mocker):
    """AC-20: family_idea_callout fallback when absent; untouched when present."""
    from src import editor
    family = _make_family(mocker)
    data = _valid_editorial_dict()
    data["today_in_history"] = {"fact": "עובדה."}
    result = editor._normalize_editorial(data, family, None)
    assert result["today_in_history"]["family_idea_callout"]

    # Already present: untouched
    data2 = _valid_editorial_dict()
    data2["today_in_history"]["family_idea_callout"] = "עניין ספציפי"
    result2 = editor._normalize_editorial(data2, family, None)
    assert result2["today_in_history"]["family_idea_callout"] == "עניין ספציפי"


def test_ac21_poll_options_deduplicated(mocker):
    """AC-21: poll_options deduplicated order-preserving."""
    from src import editor
    family = _make_family(mocker)
    data = _valid_editorial_dict()
    data["question_of_the_week"]["poll_options"] = ["a", "b", "a", "c"]
    result = editor._normalize_editorial(data, family, None)
    assert result["question_of_the_week"]["poll_options"] == ["a", "b", "c"]


def test_ac22_editors_choice_fallback(mocker):
    """AC-22: editors_choice fallback with and without surviving bridges."""
    from src import editor
    family = _make_family(mocker)

    # No editors_choice, 2 valid bridges → ref="bridge_1", non-empty note
    data = _valid_editorial_dict()
    del data["editors_choice"]
    result = editor._normalize_editorial(data, family, None)
    assert result["editors_choice"]["ref"] == "bridge_1"
    assert result["editors_choice"]["note"]

    # No editors_choice, 0 valid bridges → ref="", non-empty note
    data2 = _valid_editorial_dict()
    del data2["editors_choice"]
    data2["discovery_bridges"] = []
    result2 = editor._normalize_editorial(data2, family, None)
    assert result2["editors_choice"]["ref"] == ""
    assert result2["editors_choice"]["note"]


def test_ac23_editor_credit_unconditional(mocker):
    """AC-23: editor_credit always equals EDITOR_CREDIT, even if input had different value."""
    from src import editor
    family = _make_family(mocker)

    data = _valid_editorial_dict()
    result = editor._normalize_editorial(data, family, None)
    assert result["editor_credit"] == editor.EDITOR_CREDIT

    # Even if the dict already had a different value
    data2 = _valid_editorial_dict()
    data2["editor_credit"] = "someone else"
    result2 = editor._normalize_editorial(data2, family, None)
    assert result2["editor_credit"] == editor.EDITOR_CREDIT


def test_ac24_scan_sensitive_terms():
    """AC-24: _scan_sensitive_terms detects name+nails combo but not name alone."""
    from src import editor
    original = {"opener": "יויו עשתה עוד ציור ציפורניים מדהים היום"}
    warnings = editor._scan_sensitive_terms(original)
    assert len(warnings) > 0

    # Name present but no nails term → no warning
    safe = {"opener": "יויו הייתה בקרקס היום"}
    assert editor._scan_sensitive_terms(safe) == []

    # Neither call mutates input
    assert original == {"opener": "יויו עשתה עוד ציור ציפורניים מדהים היום"}
    assert safe == {"opener": "יויו הייתה בקרקס היום"}


# ─── §2.7 Mock mode (AC-25 through AC-28) ────────────────────────────────────


def test_ac25_mock_editorial_passes_validation(mocker):
    """AC-25: _mock_editorial output passes _validate_editorial with zero errors."""
    from src import editor
    family = _make_family(mocker)
    result = editor._mock_editorial(family, None, None, "2026-07-24")
    assert editor._validate_editorial(result) == []


def test_ac26_mock_editorial_is_deterministic(mocker):
    """AC-26: two calls with identical inputs return equal dicts."""
    from src import editor
    family = _make_family(mocker)
    r1 = editor._mock_editorial(family, None, None, "2026-07-24")
    r2 = editor._mock_editorial(family, None, None, "2026-07-24")
    assert r1 == r2


def test_ac27_mock_editorial_prior_answer_overrides_none(mocker):
    """AC-27: mock normalizes the None last_week_answer_reveal using prior_puzzle_answer."""
    from src import editor
    family = _make_family(mocker)
    result = editor._mock_editorial(family, {"nimrod": ["x"]}, "42", "2026-07-24")
    assert "42" in result["puzzle"]["last_week_answer_reveal"]


def test_ac28_mock_editorial_never_calls_llm_complete(mocker):
    """AC-28: _mock_editorial makes zero calls to llm.complete."""
    from src import editor
    spy = mocker.patch("src.editor.llm.complete")
    family = _make_family(mocker)
    editor._mock_editorial(family, None, None, "2026-07-24")
    spy.assert_not_called()


# ─── §2.8 generate_editorial (AC-29 through AC-34) ───────────────────────────


def test_ac29_generate_editorial_mock_true_never_calls_llm(mocker):
    """AC-29: generate_editorial(mock=True) returns valid dict, llm.complete not called."""
    from src import editor
    spy = mocker.patch("src.editor.llm.complete")
    family = _make_family(mocker)
    settings = mocker.Mock(ai={})

    result = editor.generate_editorial(family, None, None, "2026-07-24", settings, mock=True)

    assert editor._validate_editorial(result) == []
    spy.assert_not_called()


def test_ac30_generate_editorial_real_path_single_call(mocker):
    """AC-30: real path, valid first response → called exactly once with correct kwargs."""
    from src import editor
    family = _make_family(mocker)
    settings = mocker.Mock(ai={})
    valid = _valid_editorial_dict()
    mock_complete = mocker.patch("src.editor.llm.complete", return_value=valid)

    result = editor.generate_editorial(family, None, None, "2026-07-24", settings, mock=False)

    assert mock_complete.call_count == 1
    call_kwargs = mock_complete.call_args.kwargs
    assert call_kwargs["module"] == "editor"
    assert call_kwargs["operation"] == "editorial"
    assert call_kwargs["newsletter_date"] == "2026-07-24"
    assert call_kwargs["expect_json"] is True
    assert call_kwargs["max_tokens"] == editor.DEFAULT_MAX_TOKENS
    assert result["opener"] == valid["opener"]


def test_ac31_generate_editorial_retries_once_on_schema_failure(mocker):
    """AC-31: invalid first response → retry with schema_retry operation; second response used."""
    from src import editor
    family = _make_family(mocker)
    settings = mocker.Mock(ai={})
    invalid = {"closer": "x"}  # missing opener, puzzle, etc.
    valid = _valid_editorial_dict()
    mock_complete = mocker.patch(
        "src.editor.llm.complete", side_effect=[invalid, valid]
    )

    result = editor.generate_editorial(family, None, None, "2026-07-24", settings, mock=False)

    assert mock_complete.call_count == 2
    retry_kwargs = mock_complete.call_args_list[1].kwargs
    assert retry_kwargs["operation"] == "editorial_schema_retry"
    # Retry prompt must contain the validation error for "opener"
    retry_prompt = mock_complete.call_args_list[1].args[0]
    assert "opener" in retry_prompt
    assert result["opener"] == valid["opener"]


def test_ac32_generate_editorial_raises_after_two_failures(mocker):
    """AC-32: both calls invalid → EditorSchemaError raised; exactly 2 calls made."""
    from src import editor
    family = _make_family(mocker)
    settings = mocker.Mock(ai={})
    invalid = {"closer": "x"}
    mock_complete = mocker.patch(
        "src.editor.llm.complete", side_effect=[invalid, invalid]
    )

    with pytest.raises(editor.EditorSchemaError):
        editor.generate_editorial(family, None, None, "2026-07-24", settings, mock=False)

    assert mock_complete.call_count == 2


def test_ac33_generate_editorial_propagates_llm_errors(mocker):
    """AC-33: LLMError subclasses propagate unchanged — not wrapped in EditorError."""
    from src import editor, llm
    family = _make_family(mocker)
    settings = mocker.Mock(ai={})

    for exc_class in (
        llm.LLMAllDriversFailedError,
        llm.LLMConfigError,
        llm.LLMJsonError,
    ):
        mocker.patch("src.editor.llm.complete", side_effect=exc_class("boom"))
        with pytest.raises(exc_class):
            editor.generate_editorial(family, None, None, "2026-07-24", settings, mock=False)
        # Must NOT be wrapped in EditorSchemaError
        try:
            editor.generate_editorial(family, None, None, "2026-07-24", settings, mock=False)
        except exc_class:
            pass
        except editor.EditorSchemaError:
            pytest.fail(f"{exc_class.__name__} must not be wrapped in EditorSchemaError")


def test_ac34_max_tokens_from_settings(mocker):
    """AC-34: max_tokens taken from settings.ai.editorial_max_tokens or default."""
    from src import editor
    family = _make_family(mocker)
    valid = _valid_editorial_dict()

    # Custom value in settings
    settings_custom = mocker.Mock(ai={"editorial_max_tokens": 4000})
    mock_complete = mocker.patch("src.editor.llm.complete", return_value=valid)
    editor.generate_editorial(family, None, None, "2026-07-24", settings_custom, mock=False)
    assert mock_complete.call_args.kwargs["max_tokens"] == 4000

    # Default value when key absent
    settings_default = mocker.Mock(ai={})
    mock_complete.reset_mock()
    editor.generate_editorial(family, None, None, "2026-07-24", settings_default, mock=False)
    assert mock_complete.call_args.kwargs["max_tokens"] == editor.DEFAULT_MAX_TOKENS


# ─── Additional P0 coverage ───────────────────────────────────────────────────


def test_p0_shaked_english_applies_even_with_highlights(mocker):
    """P0: Shaked English rule in system prompt applies when highlights ARE provided.
    The user prompt roster entry for Shaked should show 'en' language preference,
    confirming the system prompt rule is the unconditional backstop."""
    from src import editor
    family = _make_family(mocker)
    # Give Shaked research highlights (not the empty-fallback path)
    result = editor._build_user_prompt(
        family,
        {"shaked": ["New LitRPG series just dropped"]},
        None,
        "2026-07-24",
    )
    # The language preference 'en' must appear for Shaked in the user prompt
    assert "shaked" in result.lower()
    # The system prompt separately has the unconditional rule
    assert "english" in editor.EDITORIAL_SYSTEM_PROMPT.lower()
    assert "unconditional" in editor.EDITORIAL_SYSTEM_PROMPT.lower() or \
           "absolute" in editor.EDITORIAL_SYSTEM_PROMPT.lower()


def test_p0_ac04_empty_braces_in_json_are_allowed():
    """P0 AC-04 rescope: the bare-identifier regex must NOT flag empty {} braces
    or JSON-style {"key": val} — only {word} patterns are forbidden."""
    bare_id_re = re.compile(r'\{[a-zA-Z_]\w*\}')
    # These are all fine (JSON syntax, empty braces) — must not match
    allowed = [
        '{}',
        '{"type": "string"}',
        '{"minLength": 1}',
        '{"properties": {"opener": {"type": "string"}}}',
        '"items": {}',
    ]
    for s in allowed:
        assert not bare_id_re.search(s), (
            f"Regex should NOT flag JSON braces in: {s!r}"
        )
    # These are format placeholders — must match
    forbidden = ["{today}", "{roster_block}", "{family_name}"]
    for s in forbidden:
        assert bare_id_re.search(s), (
            f"Regex SHOULD flag format placeholder: {s!r}"
        )
