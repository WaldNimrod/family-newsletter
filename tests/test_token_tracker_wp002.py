"""WP002 token_tracker tests — Anthropic mocked; pause_turn REPLACE (corrected AC-25)."""
from __future__ import annotations

import json

import pytest

from src.token_tracker import ResearchLoopError, TokenTracker


def test_calculate_cost_intro_vs_standard():
    assert TokenTracker.calculate_cost(
        "claude-sonnet-5", 1_000_000, 0, "2026-08-31"
    ) == 2.0
    assert TokenTracker.calculate_cost(
        "claude-sonnet-5", 1_000_000, 0, "2026-09-01"
    ) == 3.0


def test_mock_research_returns_json(mocker):
    db = mocker.Mock()
    tt = TokenTracker(db, mock=True)
    text = tt.research("researcher", "gather", "find stuff", 1000)
    data = json.loads(text)
    assert "items" in data
    db.log_token_usage.assert_called()


def test_research_pause_turn_replaces_messages(mocker):
    """Corrected AC-25: messages stay length-2 [user, latest assistant]."""
    paused = mocker.Mock(
        stop_reason="pause_turn",
        content=[mocker.Mock(type="server_tool_use")],
        usage=mocker.Mock(
            input_tokens=100, output_tokens=10, server_tool_use=None
        ),
    )
    done = mocker.Mock(
        stop_reason="end_turn",
        content=[mocker.Mock(type="text", text="done")],
        usage=mocker.Mock(
            input_tokens=50, output_tokens=5, server_tool_use=None
        ),
    )
    db = mocker.Mock()
    tracker = TokenTracker(db=db, api_key="x")
    tracker.mock = False
    tracker.client = mocker.Mock()
    tracker.client.messages.create.side_effect = [paused, paused, done]
    mocker.patch("src.token_tracker.time.sleep")

    assert tracker.research("m", "op", "prompt", 1000, max_continuations=2) == "done"
    assert tracker.client.messages.create.call_count == 3

    for call in tracker.client.messages.create.call_args_list[1:]:
        msgs = call.kwargs["messages"]
        assert len(msgs) == 2
        assert msgs[0] == {"role": "user", "content": "prompt"}
        assert msgs[1]["role"] == "assistant"


def test_research_max_continuations_raises(mocker):
    paused = mocker.Mock(
        stop_reason="pause_turn",
        content=[mocker.Mock(type="server_tool_use")],
        usage=mocker.Mock(
            input_tokens=10, output_tokens=1, server_tool_use=None
        ),
    )
    db = mocker.Mock()
    tracker = TokenTracker(db=db, api_key="x")
    tracker.mock = False
    tracker.client = mocker.Mock()
    tracker.client.messages.create.return_value = paused
    mocker.patch("src.token_tracker.time.sleep")

    with pytest.raises(ResearchLoopError, match="max_continuations"):
        tracker.research("m", "op", "prompt", 1000, max_continuations=0)
    assert tracker.client.messages.create.call_count == 1


def test_research_tools_omit_allowed_callers(mocker):
    """BUILD_DIRECTIVE: allowed_callers deferred to Mac live smoke."""
    done = mocker.Mock(
        stop_reason="end_turn",
        content=[mocker.Mock(type="text", text="ok")],
        usage=mocker.Mock(
            input_tokens=1, output_tokens=1, server_tool_use=None
        ),
    )
    db = mocker.Mock()
    tracker = TokenTracker(db=db, api_key="x")
    tracker.mock = False
    tracker.client = mocker.Mock()
    tracker.client.messages.create.return_value = done

    tracker.research("m", "op", "prompt", 100)
    tools = tracker.client.messages.create.call_args.kwargs["tools"]
    for t in tools:
        assert "allowed_callers" not in t


def test_web_search_fee_logged(mocker):
    stu = mocker.Mock(web_search_requests=2)
    done = mocker.Mock(
        stop_reason="end_turn",
        content=[mocker.Mock(type="text", text="ok")],
        usage=mocker.Mock(
            input_tokens=10, output_tokens=5, server_tool_use=stu
        ),
    )
    db = mocker.Mock()
    tracker = TokenTracker(db=db, api_key="x")
    tracker.mock = False
    tracker.client = mocker.Mock()
    tracker.client.messages.create.return_value = done

    tracker.research("m", "op", "prompt", 100)
    ops = [c.args[2] for c in db.log_token_usage.call_args_list]
    assert "web_search" in ops


def test_settings_json_has_research_keys():
    import json
    from pathlib import Path

    settings = json.loads(
        Path("config/settings.json").read_text(encoding="utf-8")
    )
    ai = settings["ai"]
    for key in (
        "thinking_enabled",
        "research_max_tokens",
        "research_web_search_max_uses",
        "research_web_fetch_max_uses",
        "research_web_fetch_max_content_tokens",
        "research_max_continuations",
    ):
        assert key in ai
    assert settings["budget"]["weekly_alert_usd"] == 2.50
    assert ai["summary_model"] == "claude-sonnet-5"
