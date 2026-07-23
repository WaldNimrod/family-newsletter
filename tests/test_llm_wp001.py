"""WP001 llm.py tests — Anthropic mocked; P0 AC corrections applied."""
from __future__ import annotations

import json

import pytest

import src.llm as llm
from src.llm import (
    DEFAULT_CURSOR_MODEL,
    LLMAllDriversFailedError,
    LLMConfigError,
    LLMError,
    LLMJsonError,
    _DriverCallError,
    _try_parse_json,
    complete,
    configure,
)


@pytest.fixture(autouse=True)
def _reset_llm_state():
    llm._state.update(
        {"db": None, "ai_settings": None, "mock": False, "token_tracker": None}
    )
    yield
    llm._state.update(
        {"db": None, "ai_settings": None, "mock": False, "token_tracker": None}
    )


def test_default_cursor_model_is_cursor_grok_high():
    assert DEFAULT_CURSOR_MODEL == "cursor-grok-4.5-high"


def test_exception_hierarchy():
    assert issubclass(LLMConfigError, LLMError)
    assert issubclass(LLMJsonError, LLMError)
    assert issubclass(LLMAllDriversFailedError, LLMError)
    assert not issubclass(_DriverCallError, LLMError)


def test_configure_then_complete_mock_json(mocker):
    db = mocker.Mock()
    configure(db, {}, mock=True)
    # P0 AC-10: use JSON-friendly mock op (submission_edit), not greeting
    result = complete(
        "edit this",
        max_tokens=100,
        module="editor",
        operation="submission_edit",
        expect_json=True,
    )
    assert isinstance(result, dict)
    assert "headline" in result


def test_complete_without_configure_raises():
    with pytest.raises(LLMConfigError):
        complete("x", max_tokens=10, module="m", operation="op")


def test_tools_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        complete(
            "x",
            max_tokens=10,
            module="m",
            operation="op",
            tools=[{"type": "web_search"}],
        )


def test_empty_provider_fallback_raises(mocker):
    # P0 AC-09: empty list must raise (check raw before `or [provider]`)
    db = mocker.Mock()
    configure(db, {"provider_fallback": []}, mock=True)
    with pytest.raises(LLMConfigError, match="empty list"):
        complete("x", max_tokens=10, module="m", operation="op")


def test_unknown_provider_raises(mocker):
    db = mocker.Mock()
    configure(db, {"provider": "nope"}, mock=True)
    with pytest.raises(LLMConfigError, match="Unknown"):
        complete("x", max_tokens=10, module="m", operation="op")


def test_expect_json_false_returns_raw(mocker):
    db = mocker.Mock()
    configure(db, {}, mock=True)
    text = complete(
        "hi",
        max_tokens=50,
        module="m",
        operation="greeting",
        expect_json=False,
    )
    assert isinstance(text, str)
    assert len(text) > 0


def test_try_parse_json_variants():
    assert _try_parse_json('{"a": 1}') == {"a": 1}
    assert _try_parse_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert _try_parse_json('Here:\n{"a": 3}\nThanks') == {"a": 3}
    assert _try_parse_json("[1,2,3]") is None
    assert _try_parse_json("not json") is None


def test_anthropic_failure_falls_to_cursor(mocker):
    db = mocker.Mock()
    configure(
        db,
        {"provider_fallback": ["anthropic", "cursor"]},
        mock=True,
    )
    mocker.patch.object(
        llm,
        "_call_anthropic",
        side_effect=_DriverCallError("anthropic", "boom"),
    )
    # Rebind registry after patch
    llm._DRIVERS["anthropic"] = llm._call_anthropic
    llm._DRIVERS["cursor"] = llm._call_cursor

    # Cursor mock returns non-JSON; expect_json False
    out = complete(
        "x",
        max_tokens=10,
        module="m",
        operation="op",
        expect_json=False,
    )
    assert "MOCK cursor" in out


def test_json_retry_then_success(mocker):
    db = mocker.Mock()
    configure(db, {"provider_fallback": ["anthropic"]}, mock=True)

    calls = {"n": 0}

    def fake_anth(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return "not json"
        return json.dumps({"ok": True})

    mocker.patch.object(llm, "_call_anthropic", side_effect=fake_anth)
    llm._DRIVERS["anthropic"] = llm._call_anthropic

    result = complete(
        "x", max_tokens=10, module="m", operation="op", expect_json=True
    )
    assert result == {"ok": True}
    assert calls["n"] == 2


def test_cursor_argv_includes_f_flag(mocker):
    db = mocker.Mock()
    db.log_token_usage = mocker.Mock()
    configure(
        db,
        {"provider_fallback": ["cursor"], "cursor_model": "cursor-grok-4.5-high"},
        mock=False,
    )
    llm._state["mock"] = False  # force live cursor path
    completed = mocker.Mock(
        returncode=0,
        stdout=json.dumps({"result": '{"z": 1}'}),
        stderr="",
    )
    run = mocker.patch("src.llm.subprocess.run", return_value=completed)
    llm._DRIVERS["cursor"] = llm._call_cursor

    result = complete(
        "prompt",
        max_tokens=10,
        module="m",
        operation="op",
        expect_json=True,
    )
    assert result == {"z": 1}
    argv = run.call_args[0][0]
    assert argv[-1] == "-f"
    assert "cursor-grok-4.5-high" in argv
