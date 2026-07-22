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

# llm.py — Dual-Driver LLM Layer (Anthropic Primary + Cursor/Grok Fallback) — LOD400 Implementation Spec

**work_package_id:** FNL-S001-P002-WP001
**parent_lod200:** _aos/work_packages/FNL-S001-P001-WP001/LOD200.md
**parent_lod300:** N/A — Track A only
**approved_by:** [PENDING — familynewsletter_build sign-off at L-GATE_SPEC]
**approved_at:** [PENDING]

## 1. Scope reminder

This WP creates **`src/llm.py`** (new file, does not exist yet) — a unified prompt-in / JSON-out interface over two interchangeable LLM backends, so every future caller (`researcher.py`, `editor.py`, `teaser.py`, `orchestrator.py` — all separate WPs per LOD200 §8) writes one line (`llm.complete(...)`) instead of branching on which engine is configured. Two drivers sit behind the interface: `anthropic` wraps the existing `TokenTracker.generate()` (Claude Sonnet 5, no tools); `cursor` shells `cursor-agent -p ... --output-format json -m <grok> -f`, headless (verified working on the Mac 2026-07-22 — memory `family-newsletter-engine-env-canon.md`). The active driver and its fallback order are read from `settings.json → ai.provider` / `ai.provider_fallback`; on a driver error, `complete()` falls through to the next driver in the configured chain. Every call — on either driver — logs to the existing `token_usage` table (cursor logs cost as `$0`, since there is no per-token billing API for a Cursor-subscription CLI call). Output robustness is prompt-level, not API-level: `complete()` strips code fences/leading-trailing prose and parses JSON, retrying **once** with a "return ONLY valid JSON" reinforcement before raising a typed `LLMJsonError`.

**Design source — REVIVAL_PLAN_2026-07-22.md §3.6** (quoted, original Hebrew, verbatim):

> **מימוש:** שכבת `llm.py` עם שני דרייברים מאחורי ממשק אחיד (prompt in → JSON out):
> - `cursor` (ברירת מחדל): `cursor-agent -p --output-format json -m <grok>` על השרת
> - `anthropic` (fallback): ה-token_tracker הקיים, claude-sonnet-5 + web_search
>
> הבחירה ב-`settings.json` → `ai.provider`, עם fallback אוטומטי לפי סדר. כל ריצה נרשמת ל-token_usage כרגיל (עלות Cursor נרשמת כ-$0).

**⚠️ CORRECTION TO §3.6 — read before implementing `ai.provider`'s default value.** §3.6 (written early in the 2026-07-22 session) names `cursor` as the settings.json default and `anthropic` as the fallback, based on the original Cursor-subscription cost-minimization rationale ("שם יש עודף טוקנים במנוי... עלות שולית ~אפס"). This was **superseded later the same day** once live verification established: (1) there is **no Grok/xAI API key on the server yet** — cursor-agent-on-server is an unverified fast-follow, confirmed working headless only **on the Mac**; (2) the `anthropic` path (Sonnet-5 via the existing `token_tracker`) **is** headless-verified and proven at ~$1.5/wk. Both facts are recorded in memory `family-newsletter-engine-env-canon.md` ("`ai.provider` default for edition-1 = anthropic, NOT cursor") and `data/profile-raw/TRANSCRIPT_MINING_2026-07-22.md` → *Pipeline / engine / env* section. **This spec overrides §3.6 on the default:** edition-1's `ai.provider` default is `"anthropic"`, and `ai.provider_fallback` default is `["anthropic"]` (single-driver, no `cursor` in the chain) — see §4. The `cursor` driver is still built **in full** per §3.6's technical design (dual-driver interface, exact argv shape, §2.5) so Phase-C can flip the default later — it is simply not exercised by default in edition-1, and this WP's acceptance criteria require the `anthropic` path to work with **zero dependency** on `cursor-agent` being installed, authenticated, or even present on the host (see §6, §7 cross-engine check).

### Assumptions (where the brief was silent — flag these at L-GATE_VALIDATE if wrong)

1. **`cursor-agent`'s `--output-format json` envelope shape is assumed to be `{"result": "<text>", ...}`** — a top-level string field named `result`. This is **not** verified against real `cursor-agent` output in any source material available at spec-authoring time (the 2026-07-22 Mac smoke-test confirmed the CLI runs headless with `-f` and completed a real cross-engine loop; it did not record the JSON envelope's field names). §7 makes confirming this real field name, live, an explicit manual step before merge. If the real field differs, update `_call_cursor`'s extraction line (§2.5) and this note — no other part of the module is affected.
2. **The Grok model string passed to `-m` is a placeholder** (`DEFAULT_CURSOR_MODEL = "grok-4"`), sourced from `ai.cursor_model` in settings with this constant as the fallback default. No verified `cursor-agent`-recognized Grok model identifier was available in any read source (the engine-env-canon memory explicitly notes no Grok/xAI API key exists on the server yet, and the Mac verification tested that the CLI runs headless, not which exact `-m` value it expects). Since edition-1's default driver chain is `["anthropic"]` (see the §3.6 correction above), this placeholder is inert for edition-1 and blocks nothing here — it must be confirmed (e.g. `cursor-agent --help` / `cursor-agent models list` if such a subcommand exists, or a live smoke test) before Phase-C flips the default.
3. **`configure(db, ai_settings, mock=False)` is a new public function, not present in the task brief's literal `complete(...)` signature.** `complete()` needs a `Database` instance (to construct the shared `TokenTracker` and to log cursor-driver usage) and a `mock` flag, but the brief's example signature has neither. Rather than adding two more keyword arguments to every `complete()` call site across the whole codebase (`researcher.py`, `editor.py`, `teaser.py` — all future WPs), this spec adds one `configure()` call the orchestrator makes **once** per process (mirroring `logging.basicConfig()`, and the existing orchestrator pattern `tt = TokenTracker(db, mock=args.mock)` built once in `cmd_weekly_build`) — `complete()`'s own signature then matches the brief exactly, verbatim. `complete()` raises `LLMConfigError` if called before `configure()`.
4. **`tools` (accepted by `complete()`'s signature per the brief) is not implemented by either driver in this WP.** It exists in the public signature for forward-interface-compatibility with WP002's `research()` (`web_search`/`web_fetch` server tools) and WP003's `researcher.py`, which land later and will call `complete(..., tools=[...])`. Passing a non-`None` value in **this** WP raises `NotImplementedError` immediately — a loud, explicit, easily-testable failure — rather than silently ignoring the argument or half-wiring it through only the `anthropic` driver, which would be a much harder bug to catch later.
5. **This spec targets `token_tracker.py`'s POST-WP002 interface**: `generate(module, operation, prompt, max_tokens, model="claude-sonnet-5", newsletter_date=None, system=None, thinking_enabled=False)` and the date-gated `PRICING["claude-sonnet-5"]` entry (see `_aos/work_packages/FNL-S001-P002-WP002/LOD400_spec.md` §2.1–§2.2), since WP002's own scope statement frames itself as "the Claude-API-calling layer both [WP001 and WP003] sit on top of." **This WP does not depend on WP002 landing first to avoid crashing** — `_call_anthropic` (§2.4) passes `model="claude-sonnet-5"` as a plain string either way, and `TokenTracker.generate()` has no model whitelist. Pre-WP002, `calculate_cost()`'s existing fallback (`PRICING.get(model, PRICING["claude-sonnet-4-6"])`) logs cost at the `claude-sonnet-4-6` rate ($3/$15 — exactly correct from 2026-09-01 onward, ≈33% overcounted vs. the correct intro rate before that) until WP002 lands, at which point costs self-correct with **zero code changes in `llm.py`**. `llm.py` never passes `thinking_enabled` explicitly — it relies on `generate()`'s own default (`False`/disabled) for cost control, consistent with LOD200 §6.
6. **The cursor-driver trust/auth-failure detection is a keyword heuristic on `stderr`** (`"trust"`, `"auth"`, `"unauthorized"`, `"login"`, `"not logged in"`), since no real `cursor-agent` error text was available at spec-authoring time. It affects only the log message's clarity, not control flow — both a generic non-zero exit and a keyword-matched "trust/auth failure" trigger the **identical** driver-fallback behavior (§2.5, §5). If real error text later shows the heuristic is wrong, only the keyword list needs updating.

## 2. Technical specification

This WP creates one new file, `src/llm.py`. Implement the following components **in this exact order within that one file** — the order matters because `_DRIVERS` (§2.6) references `_call_anthropic` and `_call_cursor`, which must already be defined above it in the source.

### 2.1 Module foundations — imports, exception hierarchy, constants, module state, `configure()`

**What to implement:**

1. Module docstring + imports:

```python
"""
Family Newsletter — LLM Driver Layer
Unified prompt-in / JSON-out interface over two interchangeable backends
(anthropic = existing token_tracker / Claude Sonnet 5; cursor = cursor-agent
CLI / Grok, headless). Per LOD400 FNL-S001-P002-WP001.
"""

import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from typing import Optional, Union

from .db import Database
from .token_tracker import TokenTracker

logger = logging.getLogger('family.llm')
```

2. Exception hierarchy (public exceptions all subclass `LLMError`; `_DriverCallError` is internal-only and deliberately does **not** subclass `LLMError` — it must never be allowed to leak past `complete()`'s fallback loop, so giving it a distinct base makes an accidental `except LLMError` catch-all fail to mask it):

```python
class LLMError(Exception):
    """Base class for all llm.py errors."""


class LLMConfigError(LLMError):
    """Raised for invalid module configuration: configure() not called
    before complete(), or an unknown driver name in ai.provider /
    ai.provider_fallback."""


class LLMJsonError(LLMError):
    """Raised when expect_json=True and the driver's output could not be
    parsed as a JSON object, even after one reinforced retry."""


class LLMAllDriversFailedError(LLMError):
    """Raised when every driver in the configured fallback chain raised an
    error for a given complete() call. Message summarizes each attempt."""


class _DriverCallError(Exception):
    """Internal only — never part of the public API. Raised by a driver
    function (_call_anthropic / _call_cursor) when that specific driver
    failed to produce a response. Always caught inside complete()'s
    fallback loop; must never propagate out of complete() to a caller."""

    def __init__(self, driver: str, detail: str):
        self.driver = driver
        self.detail = detail
        super().__init__(f"[{driver}] {detail}")
```

3. Module-level constants:

```python
DEFAULT_PROVIDER = "anthropic"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"
DEFAULT_CURSOR_BINARY = "cursor-agent"
DEFAULT_CURSOR_MODEL = "grok-4"  # UNVERIFIED placeholder — see §1 Assumption 2
DEFAULT_CURSOR_TIMEOUT_SECONDS = 120

JSON_RETRY_SUFFIX = (
    "\n\nIMPORTANT: Your previous response could not be parsed as JSON. "
    "Return ONLY a single valid JSON object as your entire response — "
    "no prose before or after, no markdown code fences, no explanation."
)
```

4. Module state + `configure()`:

```python
_state = {
    "db": None,
    "ai_settings": None,
    "mock": False,
    "token_tracker": None,
}


def configure(db: Database, ai_settings: dict, mock: bool = False) -> None:
    """Must be called once (per process) before complete(). Re-callable —
    a later call fully replaces prior state, including rebuilding the
    shared TokenTracker.

    ai_settings is the 'ai' sub-object of settings.json (e.g. settings.ai
    if using the m1_profiles Settings wrapper, or raw_json['ai'] if
    loading the file directly) — must support .get(key, default). An
    empty dict {} is valid; every read in this module falls back to a
    documented default (see §4).
    """
    _state["db"] = db
    _state["ai_settings"] = ai_settings
    _state["mock"] = mock
    _state["token_tracker"] = TokenTracker(db, mock=mock)
```

**Acceptance criteria:**
- [ ] AC-01: `from src import llm` (or `import src.llm as llm`) succeeds with no import-time errors when `ANTHROPIC_API_KEY` is unset and no live network/binary is available — the module has no import-time side effects (no network calls, no subprocess calls, no file I/O beyond its own definitions).
- [ ] AC-02: `LLMError`, `LLMConfigError`, `LLMJsonError`, `LLMAllDriversFailedError` are all defined at module level; `LLMConfigError`, `LLMJsonError`, and `LLMAllDriversFailedError` each subclass `LLMError`; `_DriverCallError` subclasses bare `Exception`, not `LLMError`.
- [ ] AC-03: `configure(db, {}, mock=True)` does not raise (empty `ai_settings` dict is valid).
- [ ] AC-04: Calling `configure()` twice with different `db` / `ai_settings` / `mock` values fully replaces the previous state — verified by calling `complete()` after the second `configure()` and confirming its behavior reflects the second call's settings, not the first's.
- [ ] AC-05: `complete(...)` called with no prior `configure()` call in the process (or with `llm._state` manually reset to `{"db": None, "ai_settings": None, "mock": False, "token_tracker": None}`) raises `LLMConfigError`.

### 2.2 Public entry point — `complete()`

**What to implement:**

```python
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
    """THE public entry point. prompt in -> JSON out (dict) by default, or
    raw text (str) when expect_json=False. Tries drivers in the order
    given by ai.provider_fallback, falling through to the next driver on
    any failure. Raises LLMAllDriversFailedError only if every configured
    driver fails. When expect_json=True, a JSON-parse failure triggers
    exactly one retry (reinforced prompt, same driver) before raising
    LLMJsonError — this does NOT restart the driver-fallback chain.

    Must call configure() first. tools is accepted for forward interface
    compatibility with WP002/WP003 but is not implemented in this WP —
    passing a non-None value raises NotImplementedError immediately.
    """
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

    ai_settings = _state["ai_settings"]
    provider = ai_settings.get("provider", DEFAULT_PROVIDER)
    fallback_chain = ai_settings.get("provider_fallback") or [provider]

    if not fallback_chain:
        raise LLMConfigError(
            "ai.provider_fallback resolved to an empty list — must contain "
            "at least one driver name."
        )
    if provider not in _DRIVERS:
        raise LLMConfigError(
            f"Unknown driver '{provider}' in ai.provider. Known drivers: "
            f"{sorted(_DRIVERS)}."
        )
    for name in fallback_chain:
        if name not in _DRIVERS:
            raise LLMConfigError(
                f"Unknown driver '{name}' in ai.provider_fallback. Known "
                f"drivers: {sorted(_DRIVERS)}."
            )

    attempts = []
    raw_text = None
    winning_driver_fn = None
    winning_driver_name = None

    for name in fallback_chain:
        driver_fn = _DRIVERS[name]
        try:
            raw_text = driver_fn(
                prompt, system, max_tokens, module, operation, newsletter_date
            )
            winning_driver_fn = driver_fn
            winning_driver_name = name
            break
        except _DriverCallError as e:
            logger.warning(
                f"[llm] driver '{name}' failed for {module}/{operation}: {e.detail}"
            )
            attempts.append((name, e.detail))
            continue

    if winning_driver_fn is None:
        detail = "; ".join(f"{n}: {d}" for n, d in attempts)
        raise LLMAllDriversFailedError(
            f"All configured drivers failed for {module}/{operation}. "
            f"Attempts: {detail}"
        )

    logger.info(f"[llm] {module}/{operation} served by driver '{winning_driver_name}'")

    if not expect_json:
        return raw_text

    parsed = _try_parse_json(raw_text)
    if parsed is not None:
        return parsed

    reinforced_prompt = prompt + JSON_RETRY_SUFFIX
    retry_operation = f"{operation}_json_retry"
    try:
        raw_text_2 = winning_driver_fn(
            reinforced_prompt, system, max_tokens, module, retry_operation, newsletter_date
        )
    except _DriverCallError as e:
        raise LLMJsonError(
            f"{module}/{operation}: JSON parse failed on the first attempt, "
            f"and the reinforced retry call itself failed on driver "
            f"'{winning_driver_name}': {e.detail}"
        ) from e

    parsed_2 = _try_parse_json(raw_text_2)
    if parsed_2 is not None:
        return parsed_2

    raise LLMJsonError(
        f"{module}/{operation}: could not parse a JSON object after 1 retry "
        f"(driver '{winning_driver_name}'). Last raw output (truncated): "
        f"{raw_text_2[:300]!r}"
    )
```

**Acceptance criteria:**
- [ ] AC-06: `complete(prompt="x", max_tokens=10, module="m", operation="o", tools=["anything"])` raises `NotImplementedError` immediately — verified with `configure()` deliberately **not** called first, confirming the `tools` guard runs before the config-validity check (i.e. it is the first statement in the function body).
- [ ] AC-07: With `ai_settings={"provider": "bogus", "provider_fallback": ["anthropic"]}`, `complete()` raises `LLMConfigError` whose message contains `"bogus"`, and no driver function is ever invoked (assert via a mock/spy that neither `_call_anthropic` nor `_call_cursor` was called, and that no `token_usage` row was written).
- [ ] AC-08: With `ai_settings={"provider": "anthropic", "provider_fallback": ["anthropic", "bogus"]}`, `complete()` raises `LLMConfigError` whose message contains `"bogus"` — validated **before** the earlier, valid `"anthropic"` entry in the same chain is ever attempted (no driver call happens at all).
- [ ] AC-09: With `ai_settings={"provider": "anthropic", "provider_fallback": []}` (empty list), `complete()` raises `LLMConfigError` referencing the empty fallback chain.
- [ ] AC-10: With `ai_settings={}` (no keys at all) and `mock=True`, `complete(prompt="x", max_tokens=10, module="m", operation="greeting")` succeeds via the `anthropic` driver using only documented defaults — no `KeyError`/`AttributeError`.
- [ ] AC-11: Driver-fallback: `provider_fallback=["anthropic", "cursor"]`; `_call_anthropic` monkeypatched/mocked to raise `_DriverCallError("anthropic", "boom")`; `_call_cursor` mocked to return a valid JSON string — `complete()` returns the parsed result from the cursor call, and the anthropic failure is logged via `logger.warning` but does not propagate.
- [ ] AC-12: Driver-fallback exhaustion: both drivers in the configured chain mocked to raise `_DriverCallError` — `complete()` raises `LLMAllDriversFailedError` whose message contains both driver names and both failure details, in chain order.
- [ ] AC-13: `expect_json=False`: driver mocked to return a plain non-JSON string (e.g. `"Good morning, family!"`) — `complete()` returns that exact string unchanged, and `_try_parse_json` is never called (verify with a string that would need real work to "fail" parsing, confirming no exception is swallowed along the way).

### 2.3 JSON-out robustness — parsing, code-fence/prose stripping, and the one-shot reinforced retry

**What to implement:**

```python
_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    """Strip a single leading/trailing markdown code fence (```json ... ```
    or ``` ... ```), if the ENTIRE trimmed string is wrapped in one.
    Returns the input unchanged (just whitespace-trimmed) if no fence
    wraps the whole string."""
    text = text.strip()
    m = _FENCE_RE.match(text)
    if m:
        return m.group(1).strip()
    return text


def _extract_outer_json(text: str) -> str:
    """Find the outermost {...} or [...] span (first opening bracket to
    the LAST matching-type closing bracket in the string) and return that
    slice. Returns the input unchanged if no opening '{' or '[' is found.
    This recovers a JSON object embedded in leading/trailing prose, e.g.
    'Here is the JSON:\\n{...}\\nHope that helps!'."""
    first_obj = text.find("{")
    first_arr = text.find("[")
    candidates = [i for i in (first_obj, first_arr) if i != -1]
    if not candidates:
        return text
    start = min(candidates)
    open_ch = text[start]
    close_ch = "}" if open_ch == "{" else "]"
    end = text.rfind(close_ch)
    if end == -1 or end < start:
        return text
    return text[start:end + 1]


def _try_parse_json(raw_text: str) -> Optional[dict]:
    """Attempt to parse raw_text as a JSON object (top-level dict only —
    a top-level JSON array, string, or number is treated as a parse
    failure for this contract, matching complete()'s dict|str return
    type). Returns the parsed dict on success, or None on any failure."""
    candidate = _strip_code_fence(raw_text)
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    candidate2 = _extract_outer_json(candidate)
    if candidate2 != candidate:
        try:
            parsed = json.loads(candidate2)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return None
```

The one-shot reinforced retry itself is implemented inside `complete()` (§2.2) — this component only provides the parsing primitives `complete()` calls. Do not duplicate retry logic here.

**Acceptance criteria:**
- [ ] AC-14: `_try_parse_json('{"a": 1}')` returns `{"a": 1}`.
- [ ] AC-15: `_try_parse_json('```json\n{"a": 1}\n```')` returns `{"a": 1}` (fenced block stripped).
- [ ] AC-16: `_try_parse_json('Here is your answer:\n{"a": 1}\nHope that helps!')` returns `{"a": 1}` (outer-bracket extraction recovers the object despite leading/trailing prose).
- [ ] AC-17: `_try_parse_json('[1, 2, 3]')` returns `None` — valid JSON, but not a top-level object, is treated as a parse failure under this contract.
- [ ] AC-18: `_try_parse_json('not json at all')` returns `None`.
- [ ] AC-19: End-to-end via `complete()`: the winning driver mocked to return malformed text on its **first** call and `'{"ok": true}'` on its **second** (reinforced) call — `complete()` returns `{"ok": True}`; the driver function was invoked exactly twice; the second invocation's `operation` argument equals `f"{operation}_json_retry"` (assert via the mock's captured call args).
- [ ] AC-20: End-to-end via `complete()`: the winning driver mocked to return malformed text on **both** calls — `complete()` raises `LLMJsonError` whose message contains the operation name and a truncated preview of the second raw output; the driver function was invoked exactly twice (never a third time, and `provider_fallback`'s next entry, if any, is never attempted).
- [ ] AC-21: If the reinforced retry call itself raises `_DriverCallError` (e.g. a transient failure on the second call), `complete()` raises `LLMJsonError` (not `LLMAllDriversFailedError`, and not a bare re-raise of the underlying error) with the underlying `_DriverCallError` chained via `from`.

### 2.4 Anthropic driver — `_call_anthropic()`

**What to implement:**

```python
def _call_anthropic(prompt: str, system: Optional[str], max_tokens: int,
                     module: str, operation: str,
                     newsletter_date: Optional[str]) -> str:
    """anthropic driver: wraps the shared TokenTracker (claude-sonnet-5).
    token_tracker.generate() already retries transient failures 3x
    internally with exponential backoff before raising (see WP002) — this
    function does NOT add a second retry loop on top of that. Every
    driver function in this module shares this exact signature so they
    are interchangeable via the _DRIVERS registry (§2.6)."""
    tt = _state["token_tracker"]
    model = _state["ai_settings"].get("anthropic_model", DEFAULT_ANTHROPIC_MODEL)
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
```

**Acceptance criteria:**
- [ ] AC-22: `_call_anthropic(...)` calls `TokenTracker.generate()` with `model` read from `ai_settings.get("anthropic_model", "claude-sonnet-5")` — verify both the explicit-override case (`ai_settings={"anthropic_model": "claude-sonnet-4-6"}` → `generate()` called with `model="claude-sonnet-4-6"`) and the default case (key absent → called with `model="claude-sonnet-5"`).
- [ ] AC-23: `_call_anthropic(...)` never passes a `tools` or `thinking_enabled` keyword argument to `TokenTracker.generate()` — confirms it relies entirely on `generate()`'s own defaults (§1 Assumption 5).
- [ ] AC-24: If `TokenTracker.generate()` raises any `Exception`, `_call_anthropic` catches it and re-raises `_DriverCallError("anthropic", str(original_exception))`, chained via `from`.
- [ ] AC-25: `_call_anthropic` implements no retry loop of its own — a mocked `generate()` configured to raise exactly once (`side_effect=[Exception("x")]`) causes `_call_anthropic` to raise `_DriverCallError` immediately after that single call; `generate()` is confirmed called exactly once by `_call_anthropic` (any retrying beyond that is `TokenTracker`'s own internal responsibility, already covered by WP002's test suite — not re-tested here).

### 2.5 Cursor driver — `_call_cursor()`

**What to implement:**

1. Exact `cursor-agent` invocation contract — the **entire** argv list, in this order, with the `-f` (trust) flag **hardcoded and unconditional**:

```
[cursor_binary, "-p", full_prompt, "--output-format", "json", "-m", cursor_model, "-f"]
```

where `full_prompt = f"{system}\n\n{prompt}"` if `system` is truthy, else `prompt` unchanged — `cursor-agent -p` has no separate system-prompt flag in the verified invocation, so system and user content are merged into one string.

2. Full driver implementation:

```python
def _call_cursor(prompt: str, system: Optional[str], max_tokens: int,
                  module: str, operation: str,
                  newsletter_date: Optional[str]) -> str:
    """cursor driver: shells out to `cursor-agent` (headless Grok CLI).
    Requires the -f/--trust flag — VERIFIED on the Mac 2026-07-22;
    omitting it is the documented cause of cursor-agent blocking on an
    interactive trust prompt in a headless context. Does NOT retry
    internally (a single subprocess invocation); on any failure this
    function raises _DriverCallError and complete()'s fallback loop (§2.2)
    decides whether to try the next configured driver. max_tokens is
    accepted for interface symmetry with _call_anthropic but is not
    passed to cursor-agent — the CLI has no documented token-limit flag
    in the verified invocation."""
    ai_settings = _state["ai_settings"]

    if _state["mock"]:
        text = f"[MOCK cursor:{operation}] mock response for {module}/{operation}"
        _log_cursor_usage(module, operation, newsletter_date, cost=0.0)
        return text

    binary = ai_settings.get("cursor_binary", DEFAULT_CURSOR_BINARY)
    model = ai_settings.get("cursor_model", DEFAULT_CURSOR_MODEL)
    timeout_s = ai_settings.get("cursor_timeout_seconds", DEFAULT_CURSOR_TIMEOUT_SECONDS)

    full_prompt = f"{system}\n\n{prompt}" if system else prompt

    # List-form argv (not shell=True): full_prompt may contain arbitrary
    # LLM-directed content, incl. Hebrew RTL text — no shell escaping is
    # needed or performed, avoiding shell-injection risk entirely.
    argv = [binary, "-p", full_prompt, "--output-format", "json", "-m", model, "-f"]

    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8", timeout=timeout_s
        )
    except FileNotFoundError as e:
        raise _DriverCallError(
            "cursor",
            f"cursor-agent binary not found (looked for '{binary}' on PATH): {e}",
        ) from e
    except subprocess.TimeoutExpired as e:
        raise _DriverCallError(
            "cursor",
            f"cursor-agent timed out after {timeout_s}s for {module}/{operation}",
        ) from e

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stderr_lower = stderr.lower()
        auth_markers = ("trust", "auth", "unauthorized", "login", "not logged in")
        if any(marker in stderr_lower for marker in auth_markers):
            raise _DriverCallError(
                "cursor",
                f"cursor-agent trust/auth failure (exit {result.returncode}): "
                f"{stderr[:500]}",
            )
        raise _DriverCallError(
            "cursor", f"cursor-agent exited {result.returncode}: {stderr[:500]}"
        )

    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise _DriverCallError(
            "cursor",
            f"cursor-agent --output-format json produced invalid JSON "
            f"envelope: {result.stdout[:300]!r}",
        ) from e

    if not isinstance(envelope, dict) or "result" not in envelope:
        keys = list(envelope.keys()) if isinstance(envelope, dict) else type(envelope).__name__
        raise _DriverCallError(
            "cursor",
            f"cursor-agent JSON envelope missing 'result' field. Envelope "
            f"keys: {keys}. NOTE: the 'result' field name is an unverified "
            f"assumption (spec §1 Assumption 1) — if the real envelope uses "
            f"a different key, update this line.",
        )

    text = envelope["result"]
    if not isinstance(text, str):
        raise _DriverCallError(
            "cursor",
            f"cursor-agent envelope 'result' field is not a string: "
            f"{type(text).__name__}",
        )

    _log_cursor_usage(module, operation, newsletter_date, cost=0.0)
    return text
```

3. `max_tokens` is deliberately unused inside `_call_cursor` beyond being accepted as a parameter (see docstring) — do not attempt to synthesize a `cursor-agent` flag for it; there is none in the verified invocation.

**Acceptance criteria:**
- [ ] AC-26: With `mock=True` (set via `configure()`), `_call_cursor(...)` returns a deterministic mock string, `subprocess.run` is never invoked, and exactly one `token_usage` row is logged with `cost_usd=0.0` and `model` starting with `"cursor:"`.
- [ ] AC-27: With `mock=False`, `_call_cursor(...)` invokes `subprocess.run` with `argv == [cursor_binary, "-p", full_prompt, "--output-format", "json", "-m", cursor_model, "-f"]` exactly, where `full_prompt` is `f"{system}\n\n{prompt}"` when `system` is given, else bare `prompt`. **The `-f` flag is present in every single invocation with no conditional path that can omit it** — this is the single most safety-critical AC in this WP; the 2026-07-22 headless verification is worthless if the implementation silently drops `-f`.
- [ ] AC-28: `subprocess.run` is called with `encoding="utf-8"` explicitly (not relying on locale default) — verified by inspecting the mocked call's kwargs. (Guards Hebrew RTL content per REVIVAL_PLAN §3.6 verification item 3.)
- [ ] AC-29: `subprocess.run` raising `FileNotFoundError` causes `_call_cursor` to raise `_DriverCallError("cursor", ...)` whose message mentions the configured binary name.
- [ ] AC-30: `subprocess.run` raising `subprocess.TimeoutExpired` causes `_call_cursor` to raise `_DriverCallError("cursor", ...)` whose message mentions the configured timeout value.
- [ ] AC-31: A mocked `subprocess.run` result with `returncode=1` and `stderr="permission denied"` (no auth-related keyword) causes `_call_cursor` to raise `_DriverCallError` with the **generic** non-zero-exit message (not the trust/auth-flagged variant).
- [ ] AC-32: A mocked result with `returncode=1` and `stderr="Error: not logged in. Run cursor-agent login."` causes `_call_cursor` to raise `_DriverCallError` whose message contains an explicit trust/auth marker (case-insensitive keyword match against `stderr`).
- [ ] AC-33: A mocked result with `returncode=0` and `stdout="not valid json{{"` causes `_call_cursor` to raise `_DriverCallError` (invalid JSON envelope).
- [ ] AC-34: A mocked result with `returncode=0` and `stdout='{"other_field": "x"}'` (valid JSON, missing the `result` key) causes `_call_cursor` to raise `_DriverCallError` whose message mentions the missing `result` field.
- [ ] AC-35: A mocked result with `returncode=0` and `stdout='{"result": "hello"}'` causes `_call_cursor` to return `"hello"`, and exactly one `token_usage` row is logged with `cost_usd=0.0`, `input_tokens=0`, `output_tokens=0`.

### 2.6 Driver registry & token-usage logging contract

**What to implement:**

1. The `_log_cursor_usage` helper (used by `_call_cursor`, §2.5 — place it immediately above or below `_call_cursor`, anywhere before the `_DRIVERS` registry):

```python
def _log_cursor_usage(module: str, operation: str,
                       newsletter_date: Optional[str], cost: float) -> None:
    """Logs a token_usage row for a cursor-driver call (mock or real),
    mirroring TokenTracker._log()'s row shape so both drivers write
    structurally identical rows to the same table. model is recorded as
    'cursor:<cursor_model>' (e.g. 'cursor:grok-4') to keep cursor-driver
    rows visually distinct from anthropic-driver rows (which record a
    bare model id like 'claude-sonnet-5') when querying token_usage."""
    ts = datetime.now(timezone.utc).isoformat()
    db = _state["db"]
    cursor_model = _state["ai_settings"].get("cursor_model", DEFAULT_CURSOR_MODEL)
    model_label = f"cursor:{cursor_model}"
    try:
        db.log_token_usage(ts, module, operation, model_label, 0, 0, cost, newsletter_date)
    except Exception as e:
        logger.error(f"[llm] Failed to log cursor token usage: {e}")
```

2. The driver registry — **place this line at the very end of the file**, after both `_call_anthropic` (§2.4) and `_call_cursor` (§2.5) are defined above it:

```python
_DRIVERS = {
    "anthropic": _call_anthropic,
    "cursor": _call_cursor,
}
```

   Note for the builder: `complete()` (§2.2) references `_DRIVERS` even though it is defined textually *below* `complete()` in the file. This is safe in Python — names used inside a function body are resolved at **call** time, not definition time, and the whole module finishes loading (defining every function and this dict) before any caller ever invokes `complete()`. Do not move `complete()` below `_DRIVERS` to "fix" this — the ordering specified here (drivers, then the registry, at the bottom) is intentional and correct as-is.

**Token-usage logging contract (cross-cutting — applies to both drivers):** a `token_usage` row is written **if and only if** the underlying driver call succeeds (including mock calls, which always "succeed" with a nominal/zero cost). A failed driver attempt that triggers fallback writes **no** row — there is nothing to log for a call that never completed. The `anthropic` driver logs automatically inside `TokenTracker.generate()` itself (existing behavior, unchanged by this WP); the `cursor` driver logs explicitly via `_log_cursor_usage()` (new in this WP). Both paths ultimately call `Database.log_token_usage(timestamp, module, operation, model, input_tokens, output_tokens, cost_usd, newsletter_date)` with the same 8-argument shape (`src/db.py`, unchanged).

**Acceptance criteria:**
- [ ] AC-36: `_DRIVERS == {"anthropic": _call_anthropic, "cursor": _call_cursor}` — exact keys, and each value is the exact function object (identity, not just a re-implementation).
- [ ] AC-37: A `_DriverCallError` raised by either driver function results in **zero** `token_usage` rows logged for that failed attempt — verified for both `anthropic` (mock `TokenTracker.generate` to raise before doing any logging) and `cursor` (mock `subprocess.run` to fail before any envelope is parsed).
- [ ] AC-38: A successful `complete()` call via the `anthropic` driver that also needed the JSON-retry path (§2.3 AC-19) produces exactly **two** `token_usage` rows — one per driver invocation — with `operation` values `<operation>` and `<operation>_json_retry` respectively, both with `model="claude-sonnet-5"` (or whatever `ai.anthropic_model` was configured).

## 3. Data model changes (if any)

**None required.** `llm.py` writes to the existing `token_usage` table via `Database.log_token_usage(...)` (`src/db.py`, schema unchanged — no `CHECK` constraint on the `model` column, so the `cursor:<model>` label used by the cursor driver, e.g. `cursor:grok-4`, is schema-valid free text). No migration, no new table, no new column.

Illustrative shape of the row types this WP can produce (reference only, not DDL):

```sql
-- anthropic driver: logged automatically by TokenTracker.generate() itself
-- (existing behavior — llm.py adds no logging code on this path)
INSERT INTO token_usage (timestamp, module, operation, model, input_tokens, output_tokens, cost_usd, newsletter_date)
VALUES ('2026-07-24T09:03:11Z', 'editor', 'opener', 'claude-sonnet-5', 1840, 320, 0.0082, '2026-07-24');

-- cursor driver: logged explicitly by llm._log_cursor_usage() — always $0, 0/0 tokens
INSERT INTO token_usage (timestamp, module, operation, model, input_tokens, output_tokens, cost_usd, newsletter_date)
VALUES ('2026-07-24T09:03:12Z', 'editor', 'closer', 'cursor:grok-4', 0, 0, 0.0, '2026-07-24');

-- a JSON-retry attempt: same module, operation suffixed, so retry cost is
-- distinguishable from the original call in cost analysis
INSERT INTO token_usage (timestamp, module, operation, model, input_tokens, output_tokens, cost_usd, newsletter_date)
VALUES ('2026-07-24T09:03:13Z', 'editor', 'opener_json_retry', 'claude-sonnet-5', 1900, 340, 0.0087, '2026-07-24');
```

## 4. API contract changes (if any)

No HTTP endpoints exist in this project (batch/cron pipeline, not a web service). The relevant contract is `llm.py`'s public Python surface, plus the `settings.json → ai` object it reads.

| Symbol | Kind | Signature / Shape | Notes |
|---|---|---|---|
| `configure` | function | `configure(db: Database, ai_settings: dict, mock: bool = False) -> None` | Must be called once (re-callable) before any `complete()` call. New in this WP — see §1 Assumption 3. |
| `complete` | function | `complete(prompt: str, *, system: Optional[str] = None, max_tokens: int, module: str, operation: str, newsletter_date: Optional[str] = None, expect_json: bool = True, tools: Optional[list] = None) -> Union[dict, str]` | THE public entry point, matching the task brief's signature verbatim. Returns `dict` when `expect_json=True` (default), else raw `str`. |
| `LLMError` | exception | `class LLMError(Exception)` | Base class for the public exception hierarchy. |
| `LLMConfigError` | exception | `class LLMConfigError(LLMError)` | `configure()` not called, or unknown driver name. |
| `LLMJsonError` | exception | `class LLMJsonError(LLMError)` | JSON parse failed after the one reinforced retry. |
| `LLMAllDriversFailedError` | exception | `class LLMAllDriversFailedError(LLMError)` | Every driver in the fallback chain failed. |

### `settings.json` — new `ai.*` keys read by `configure()`'s `ai_settings` argument

| Key | Type | Default (if key absent) | Meaning |
|---|---|---|---|
| `ai.provider` | str | `"anthropic"` | Primary driver name. Must be `"anthropic"` or `"cursor"`. |
| `ai.provider_fallback` | list[str] | `[provider]` | Ordered driver-attempt chain, **including** the primary as its first element by convention. Edition-1: `["anthropic"]`. Phase-C: `["cursor", "anthropic"]`. |
| `ai.anthropic_model` | str | `"claude-sonnet-5"` | Model string passed to `TokenTracker.generate(model=...)`. |
| `ai.cursor_binary` | str | `"cursor-agent"` | Executable name/path for the cursor driver. Confirmed at `~/.local/bin/cursor-agent` on the Mac (must be on the orchestrator's `PATH`, or set an absolute path here). |
| `ai.cursor_model` | str | `"grok-4"` (UNVERIFIED — §1 Assumption 2) | Model string passed to `cursor-agent -m`. |
| `ai.cursor_timeout_seconds` | int | `120` | `subprocess.run(..., timeout=...)` bound for the cursor driver. |

**This WP does NOT edit `config/settings.json`.** It defines the contract `configure()`'s `ai_settings` argument must satisfy, and every read in §2 uses `.get(key, default)`, so `llm.py` behaves correctly (via the documented defaults) even before these keys exist in the file. Adding the literal keys to `config/settings.json` is the responsibility of whichever future WP wires `llm.py` into `orchestrator.py` (out of scope here — see §6).

### `cursor-agent` invocation — exact argv (encoded explicitly per task instruction)

```
[cursor_binary, "-p", full_prompt, "--output-format", "json", "-m", cursor_model, "-f"]
```

`full_prompt = f"{system}\n\n{prompt}"` if `system` is given, else `prompt` unchanged. The `-f` flag (trust/auto-approve) is **hardcoded, not configurable** — omitting it is the documented cause of `cursor-agent` blocking on an interactive trust prompt in a headless context, per the 2026-07-22 Mac verification (memory `family-newsletter-engine-env-canon.md`).

### Fallback semantics (encoded explicitly per task instruction)

1. `complete()` reads `ai.provider_fallback` as the **complete, ordered** driver-attempt list (not just "extra" fallbacks beyond `ai.provider`) — see §2.2.
2. Drivers are tried strictly in list order; the first driver to return without raising `_DriverCallError` wins — no further drivers are tried, and its output is what feeds the JSON-parsing/retry stage.
3. On a driver error, `complete()` logs a warning and falls through to the next entry in the chain. No `token_usage` row is written for a failed attempt (§2.6).
4. If every entry in the chain fails, `complete()` raises `LLMAllDriversFailedError` — it never silently returns `None` or an empty result.
5. The JSON-parse-failure retry (§2.3) is **not** part of driver fallback — it always retries on the **same** driver that just succeeded, never advancing to the next entry in `provider_fallback`.

## 5. Error handling requirements

| Error case | Expected behavior |
|---|---|
| `configure()` not called before `complete()` | `LLMConfigError` raised immediately, before touching any driver (AC-05). |
| Unknown driver name in `ai.provider` or `ai.provider_fallback` | `LLMConfigError` raised immediately — the whole chain is validated eagerly against `_DRIVERS` before any driver is attempted, so a bad entry never lets an earlier, valid driver burn a token first (AC-07, AC-08). |
| `tools` passed as a non-`None` value | `NotImplementedError` raised immediately, before config validation or any driver attempt (AC-06; §1 Assumption 4). |
| cursor-agent binary not found on `PATH` | `_DriverCallError("cursor", ...)` internally (`FileNotFoundError` from `subprocess.run`) → this driver's attempt fails, `complete()` falls through to the next driver in `provider_fallback`, or raises `LLMAllDriversFailedError` if cursor was the last configured driver (AC-29). |
| cursor-agent exits non-zero (generic) | `_DriverCallError("cursor", ...)` with `stderr` (truncated to 500 chars) in the message → fallback, same control flow as above (AC-31). |
| cursor-agent trust/auth failure (heuristic `stderr` keyword match) | `_DriverCallError("cursor", ...)` with an explicit trust/auth marker in the message → **identical** fallback control flow to the generic non-zero-exit row; the distinction is log clarity only (§1 Assumption 6), not a different code path (AC-32). |
| cursor-agent times out (`subprocess.TimeoutExpired`, exceeds `ai.cursor_timeout_seconds`) | `_DriverCallError("cursor", ...)` → fallback. This is the cursor-side "network/timeout" case (AC-30). |
| cursor-agent stdout is not valid JSON, or the parsed envelope lacks a `result` string field | `_DriverCallError("cursor", ...)` → fallback. Covers the unverified-envelope-shape risk (§1 Assumption 1) without ever crashing `complete()` — a schema mismatch degrades to "this driver failed," not an unhandled exception (AC-33, AC-34). |
| anthropic driver: `TokenTracker.generate()` raises (after its own internal 3× retry with exponential backoff — covers rate limits, network errors, transient 5xx; see WP002 §2.2/§5) | Caught broadly in `_call_anthropic`, re-raised as `_DriverCallError("anthropic", ...)` → fallback. This is the anthropic-side "network/timeout" case. Note the asymmetry by design: the anthropic driver benefits from `generate()`'s built-in retry before `llm.py` ever sees a failure; the cursor driver has no internal retry — a single subprocess call — so `llm.py`'s driver-fallback loop is cursor's *only* retry mechanism (AC-24, AC-25). |
| Output cannot be parsed as a JSON object, even after the one reinforced retry (`expect_json=True`) | `LLMJsonError` raised; message includes module/operation and a 300-char truncated preview of the last raw output. No further retry and **no** driver fallback at this point — the driver itself succeeded twice; only the *content* wasn't parseable JSON (AC-20). |
| The reinforced-retry driver call itself fails (`_DriverCallError`) | `LLMJsonError` raised (not `LLMAllDriversFailedError`, not a bare re-raise), with the underlying `_DriverCallError` chained via `from` (AC-21). |
| Every driver in `ai.provider_fallback` raised `_DriverCallError` (fallback exhaustion) | `LLMAllDriversFailedError` raised; message lists every attempted driver name and failure detail, in chain order (AC-12). |

## 6. Out of scope (explicit)

- The `research()` method / `web_search`/`web_fetch` tool-use implementation on `token_tracker.py` — **WP002** (`_aos/work_packages/FNL-S001-P002-WP002/LOD400_spec.md`). `complete(..., tools=[...])` raises `NotImplementedError` in this WP (§1 Assumption 4, §5) until WP002's `research()` lands and a follow-up WP wires it through `llm.py`.
- Runtime flip of `ai.provider` / `ai.provider_fallback` to make `cursor` the default **on the server** — Phase-C, explicitly gated on open item **E25** (cursor headless auth + non-interactive web_search + Hebrew RTL output on waldhomeserver, all unverified — cursor-agent is confirmed working headless only **on the Mac** as of 2026-07-22, per the engine-env-canon memory). This WP builds the `cursor` driver in full (so E25 verification has something concrete to test against), but the `anthropic` driver must work with **zero dependency** on `cursor-agent` being installed, authenticated, or reachable — see §2's ACs and §7's cross-engine check.
- Editing `config/settings.json` to add the `ai.provider` / `ai.provider_fallback` / `ai.anthropic_model` / `ai.cursor_*` keys — this WP defines the contract (§4); a later orchestrator-wiring WP adds the literal keys. `configure()`'s `ai_settings.get(key, default)` pattern means `llm.py` is correct with or without those keys present in the file.
- Wiring `llm.py` into `orchestrator.py`, `researcher.py`, `editor.py`, `teaser.py`, `publisher.py` — separate WPs per REVIVAL_PLAN §3's keep/replace table and LOD200 §8.
- Adding `"claude-sonnet-5"` to `token_tracker.py`'s `PRICING` dict, or any other edit to `token_tracker.py` / `db.py` / `config/settings.json` — WP002 (token_tracker) and later wiring WPs respectively. This WP's anthropic driver is robust to WP002 landing before, after, or concurrently with this WP (§1 Assumption 5).
- A CLI flag or per-call override to force a specific driver (e.g. `--provider cursor`) bypassing `settings.json` — not requested by the task brief; `complete()`'s signature matches it exactly, with no such parameter.
- Any change to the newsletter's visual output, content, or templates — this WP is pipeline infrastructure only.
- Confirming the real `cursor-agent --output-format json` envelope field name and the real Grok `-m` model string against a live run — flagged as unverified assumptions (§1 #1, #2) with a mandatory manual verification step in §7, but the *outcome* of that verification (updating the field name / model string if wrong) is a follow-up edit to this same file, not a separate WP.

## 7. Test requirements

- **Unit** (no real API calls, no real `cursor-agent` invocation — mock `TokenTracker.generate`, `subprocess.run`, and `Database`): every AC in §2.1–§2.6 above. Priority/highest-risk targets: the driver-fallback loop and its exhaustion path (AC-07–AC-12), the JSON-retry mechanics — same-driver-only, exactly one retry (AC-19–AC-21), and the cursor argv construction with the `-f` flag (AC-27, the single most safety-critical AC in this WP). Illustrative skeletons (pytest + pytest-mock, matching the test-stack convention already established by WP002's spec):

```python
def test_cursor_argv_always_includes_trust_flag(mocker):
    import src.llm as llm
    db = mocker.Mock()
    llm.configure(db, {"cursor_binary": "cursor-agent", "cursor_model": "grok-4"}, mock=False)
    fake_result = mocker.Mock(returncode=0, stdout='{"result": "hi"}', stderr="")
    run_mock = mocker.patch("subprocess.run", return_value=fake_result)

    text = llm._call_cursor("prompt text", None, 100, "m", "o", "2026-07-24")

    assert text == "hi"
    argv = run_mock.call_args.args[0]
    assert argv == ["cursor-agent", "-p", "prompt text", "--output-format", "json", "-m", "grok-4", "-f"]

def test_complete_falls_through_to_cursor_on_anthropic_failure(mocker):
    import src.llm as llm
    db = mocker.Mock()
    llm.configure(db, {"provider": "anthropic", "provider_fallback": ["anthropic", "cursor"]}, mock=True)
    mocker.patch.object(llm, "_call_anthropic", side_effect=llm._DriverCallError("anthropic", "boom"))
    mocker.patch.object(llm, "_call_cursor", return_value='{"ok": true}')
    llm._DRIVERS["anthropic"] = llm._call_anthropic  # re-bind after patching, if patched via object
    llm._DRIVERS["cursor"] = llm._call_cursor

    result = llm.complete(prompt="x", max_tokens=10, module="m", operation="o")

    assert result == {"ok": True}

def test_all_drivers_failed_raises(mocker):
    import src.llm as llm
    db = mocker.Mock()
    llm.configure(db, {"provider": "anthropic", "provider_fallback": ["anthropic", "cursor"]}, mock=True)
    mocker.patch.object(llm, "_call_anthropic", side_effect=llm._DriverCallError("anthropic", "boom1"))
    mocker.patch.object(llm, "_call_cursor", side_effect=llm._DriverCallError("cursor", "boom2"))
    llm._DRIVERS["anthropic"] = llm._call_anthropic
    llm._DRIVERS["cursor"] = llm._call_cursor

    import pytest
    with pytest.raises(llm.LLMAllDriversFailedError):
        llm.complete(prompt="x", max_tokens=10, module="m", operation="o")
```

  (The `_DRIVERS` re-binding lines above exist because `mocker.patch.object(llm, "_call_anthropic", ...)` replaces the module attribute but not the reference already captured inside the `_DRIVERS` dict at import time — a real test file should settle on one consistent patching strategy, e.g. patching the `_DRIVERS` dict's values directly instead, but the exact mechanics are a test-authoring detail, not part of this spec's contract.)

- **Integration** (opt-in, real cost / real binary — do not run in default CI given LOD200 §6's `$2.50/wk` cost_cap):
  - One live `anthropic`-driver call: `configure(db, {"provider": "anthropic", "provider_fallback": ["anthropic"]}, mock=False)` with a real `ANTHROPIC_API_KEY` in `.env`, then `complete(prompt='Return exactly this JSON object and nothing else: {"ping": "pong"}', max_tokens=100, module="test", operation="smoke")` → assert the returned dict has `ping == "pong"`. Gate behind an explicit opt-in (e.g. `RUN_LIVE_LLM_TESTS=1` env var) so it never runs unattended.
  - One live `cursor`-driver call, **Mac only** (matches the verified environment). This test doubles as the mandatory manual verification of §1 Assumption 1: run `cursor-agent -p "reply with the single word PONG" --output-format json -m <cursor_model> -f` directly in a terminal **first**, inspect the raw stdout, confirm (or correct) the `result` field name in `_call_cursor` (§2.5) before relying on it, **then** run the `llm.py`-level integration test. Do not skip the manual step — it is the only verification this spec has for an unconfirmed third-party CLI output schema.

- **Cross-engine validation** (required at L-GATE_VALIDATE per Iron Rule #1 — the validator engine must differ from the builder engine): confirm `src/llm.py` exports exactly `configure`, `complete`, `LLMError`, `LLMConfigError`, `LLMJsonError`, `LLMAllDriversFailedError` as its public surface; confirm the `anthropic` driver path (default `ai.provider_fallback=["anthropic"]`) never depends on `cursor-agent`/`subprocess` being available at runtime — i.e. edition-1 truly has zero dependency on the cursor driver's correctness (§6); confirm every `cursor-agent` invocation includes `-f` with **no** conditional code path that can omit it (AC-27); confirm the JSON-retry (§2.3) always targets the *same* driver that just succeeded and never restarts the `provider_fallback` chain (AC-19–AC-21); confirm the §3.6 correction (`ai.provider` default = `"anthropic"`, not `"cursor"`) is reflected in every default value in the code (`DEFAULT_PROVIDER`), not just this document's prose; confirm `git diff` for this WP touches only `src/llm.py` (plus test files, if added) — no incidental edits to `token_tracker.py`, `db.py`, `config/settings.json`, or `orchestrator.py`.

## 8. Consuming team sign-off
> I confirm this spec is executable and unambiguous. All open questions are resolved.
> **Signature:** familynewsletter_build | [PENDING — sign at L-GATE_SPEC]

---

## Cross-Engine Validation — Iron Rule

Documents at LOD400+ require cross-engine validation at L-GATE_VALIDATE.
**The validator engine MUST differ from the builder engine — IRON RULE.**
No exception. No waiver. See `gates/L-GATE_VALIDATE_VALIDATE_AND_LOCK.md`.
