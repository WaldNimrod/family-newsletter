"""
Family Newsletter — LLM Driver Layer
Unified prompt-in / JSON-out interface over two interchangeable backends
(anthropic = existing token_tracker / Claude Sonnet 5; cursor = cursor-agent
CLI / Grok, headless). Per LOD400 FNL-S001-P002-WP001.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from typing import Optional, Union

from .db import Database
from .token_tracker import TokenTracker

logger = logging.getLogger('family.llm')


class LLMError(Exception):
    """Public base for llm.py errors."""


class LLMConfigError(LLMError):
    """Not configured, unknown driver, or empty fallback chain."""


class LLMJsonError(LLMError):
    """JSON parse failed after one reinforced retry."""


class LLMAllDriversFailedError(LLMError):
    """Every driver in the fallback chain failed."""


class _DriverCallError(Exception):
    """Internal only — not a subclass of LLMError."""

    def __init__(self, driver: str, detail: str):
        self.driver = driver
        self.detail = detail
        super().__init__(f"[{driver}] {detail}")


DEFAULT_PROVIDER = "anthropic"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"
DEFAULT_CURSOR_BINARY = "cursor-agent"
# P0 (BUILD_DIRECTIVE): NOT "grok-4" — that model id is invalid.
DEFAULT_CURSOR_MODEL = "cursor-grok-4.5-high"
DEFAULT_CURSOR_TIMEOUT_SECONDS = 120

JSON_RETRY_SUFFIX = (
    "\n\nIMPORTANT: Your previous response could not be parsed as JSON. "
    "Return ONLY a single valid JSON object as your entire response — "
    "no prose before or after, no markdown code fences, no explanation."
)

_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)

_state: dict = {
    "db": None,
    "ai_settings": None,
    "mock": False,
    "token_tracker": None,
}


def configure(db: Database, ai_settings: dict, mock: bool = False) -> None:
    """Wire process-wide llm state. Re-callable (full replace)."""
    _state["db"] = db
    _state["ai_settings"] = ai_settings if ai_settings is not None else {}
    _state["mock"] = mock
    _state["token_tracker"] = TokenTracker(db, mock=mock)


def complete(
    prompt: str,
    *,
    system: Optional[str] = None,
    max_tokens: int,
    module: str,
    operation: str,
    newsletter_date: Optional[str] = None,
    expect_json: bool = True,
    tools: Optional[list] = None,
) -> Union[dict, str]:
    """Prompt-in / JSON-out (or raw string) over the configured driver chain."""
    if tools is not None:
        raise NotImplementedError(
            "llm.complete(): 'tools' is not implemented in FNL-S001-P002-WP001. "
            "Web-search/tool-use support is added to token_tracker.research() "
            "in WP002 and wired into researcher.py in WP003. Pass tools=None "
            "until a later WP updates this module."
        )

    if _state["db"] is None:
        raise LLMConfigError(
            "llm.configure(db, ai_settings, mock=...) must be called once "
            "before llm.complete()."
        )

    ai_settings = _state["ai_settings"] or {}
    provider = ai_settings.get("provider", DEFAULT_PROVIDER)

    # P0 AC-09: check raw provider_fallback BEFORE `or [provider]` so that
    # an explicit empty list raises LLMConfigError ([] is falsy).
    raw_fallback = ai_settings.get("provider_fallback")
    if raw_fallback is None:
        fallback_chain = [provider]
    else:
        fallback_chain = list(raw_fallback)

    if not fallback_chain:
        raise LLMConfigError(
            "ai.provider_fallback resolved to an empty list — must contain "
            "at least one driver name."
        )

    for name in [provider, *fallback_chain]:
        if name not in _DRIVERS:
            raise LLMConfigError(
                f"Unknown LLM driver '{name}'. Known drivers: "
                f"{sorted(_DRIVERS.keys())}."
            )

    # Deduplicate while preserving order (provider first if not already in chain)
    seen = set()
    ordered: list[str] = []
    for name in fallback_chain:
        if name not in seen:
            seen.add(name)
            ordered.append(name)

    failures: list[str] = []
    winning_driver = None
    raw_text = None

    for driver_name in ordered:
        driver_fn = _DRIVERS[driver_name]
        try:
            raw_text = driver_fn(
                prompt, system, max_tokens, module, operation, newsletter_date
            )
            winning_driver = driver_name
            break
        except _DriverCallError as e:
            logger.warning(f"[llm] driver {e.driver} failed: {e.detail}")
            failures.append(f"{e.driver}: {e.detail}")
            continue

    if winning_driver is None:
        raise LLMAllDriversFailedError(
            "All LLM drivers failed: " + "; ".join(failures)
        )

    if not expect_json:
        return raw_text

    parsed = _try_parse_json(raw_text)
    if parsed is not None:
        return parsed

    # One reinforced retry on the SAME winning driver
    retry_op = f"{operation}_json_retry"
    retry_prompt = prompt + JSON_RETRY_SUFFIX
    try:
        raw_text_2 = _DRIVERS[winning_driver](
            retry_prompt, system, max_tokens, module, retry_op, newsletter_date
        )
    except _DriverCallError as e:
        raise LLMJsonError(
            f"JSON retry on driver '{winning_driver}' failed: {e.detail}"
        ) from e

    parsed_2 = _try_parse_json(raw_text_2)
    if parsed_2 is not None:
        return parsed_2

    raise LLMJsonError(
        f"Could not parse JSON from driver '{winning_driver}' after retry. "
        f"raw={raw_text_2[:300]!r}"
    )


def _strip_code_fence(text: str) -> str:
    m = _FENCE_RE.match(text.strip())
    if m:
        return m.group(1).strip()
    return text.strip()


def _extract_outer_json(text: str) -> str:
    start_obj = text.find("{")
    start_arr = text.find("[")
    candidates = [i for i in (start_obj, start_arr) if i >= 0]
    if not candidates:
        return text
    start = min(candidates)
    opener = text[start]
    closer = "}" if opener == "{" else "]"
    end = text.rfind(closer)
    if end <= start:
        return text
    return text[start : end + 1]


def _try_parse_json(raw_text: str) -> Optional[dict]:
    if raw_text is None:
        return None
    text = _strip_code_fence(str(raw_text))
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, TypeError):
        pass

    extracted = _extract_outer_json(text)
    try:
        obj = json.loads(extracted)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, TypeError):
        return None
    return None


def _call_anthropic(
    prompt, system, max_tokens, module, operation, newsletter_date
) -> str:
    ai_settings = _state["ai_settings"] or {}
    model = ai_settings.get("anthropic_model", DEFAULT_ANTHROPIC_MODEL)
    tt: TokenTracker = _state["token_tracker"]
    try:
        return tt.generate(
            module=module,
            operation=operation,
            prompt=prompt,
            max_tokens=max_tokens,
            model=model,
            newsletter_date=newsletter_date,
            system=system,
        )
    except Exception as e:
        raise _DriverCallError("anthropic", str(e)) from e


def _log_cursor_usage(module, operation, newsletter_date, cost: float) -> None:
    ai_settings = _state["ai_settings"] or {}
    cursor_model = ai_settings.get("cursor_model", DEFAULT_CURSOR_MODEL)
    model_label = f"cursor:{cursor_model}"
    db: Database = _state["db"]
    ts = datetime.now(timezone.utc).isoformat()
    db.log_token_usage(
        ts, module, operation, model_label, 0, 0, cost, newsletter_date
    )


def _call_cursor(
    prompt, system, max_tokens, module, operation, newsletter_date
) -> str:
    ai_settings = _state["ai_settings"] or {}
    cursor_model = ai_settings.get("cursor_model", DEFAULT_CURSOR_MODEL)

    if _state["mock"]:
        text = (
            f"[MOCK cursor:{operation}] mock response for {module}/{operation}"
        )
        _log_cursor_usage(module, operation, newsletter_date, cost=0.0)
        return text

    binary = ai_settings.get("cursor_binary", DEFAULT_CURSOR_BINARY)
    timeout_s = ai_settings.get(
        "cursor_timeout_seconds", DEFAULT_CURSOR_TIMEOUT_SECONDS
    )
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    argv = [
        binary,
        "-p",
        full_prompt,
        "--output-format",
        "json",
        "-m",
        cursor_model,
        "-f",
    ]

    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_s,
        )
    except FileNotFoundError as e:
        raise _DriverCallError(
            "cursor", f"cursor binary not found: {binary}"
        ) from e
    except subprocess.TimeoutExpired as e:
        raise _DriverCallError(
            "cursor", f"cursor-agent timed out after {timeout_s}s"
        ) from e

    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "").lower()
        auth_markers = (
            "trust",
            "auth",
            "unauthorized",
            "login",
            "not logged in",
        )
        if any(m in err for m in auth_markers):
            raise _DriverCallError(
                "cursor",
                f"cursor-agent auth/trust failure (exit {completed.returncode}): "
                f"{(completed.stderr or '')[:300]}",
            )
        raise _DriverCallError(
            "cursor",
            f"cursor-agent exited {completed.returncode}: "
            f"{(completed.stderr or completed.stdout or '')[:300]}",
        )

    try:
        envelope = json.loads(completed.stdout or "")
    except json.JSONDecodeError as e:
        raise _DriverCallError(
            "cursor", f"cursor-agent returned non-JSON stdout: {e}"
        ) from e

    result = envelope.get("result") if isinstance(envelope, dict) else None
    if not isinstance(result, str):
        raise _DriverCallError(
            "cursor",
            "cursor-agent JSON envelope missing string 'result' field",
        )

    _log_cursor_usage(module, operation, newsletter_date, cost=0.0)
    return result


_DRIVERS = {
    "anthropic": _call_anthropic,
    "cursor": _call_cursor,
}
