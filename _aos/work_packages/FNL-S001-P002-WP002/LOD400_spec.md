---
lod_target: LOD400
lod_status: DRAFT
track: A
authoring_team: team_100 (familynewsletter_arch)
consuming_team: familynewsletter_build
date: 2026-07-22
version: v1.0.0
supersedes: null
---

# Token Tracker Update (Sonnet-5 Migration + Research Tool-Use) — LOD400 Implementation Spec

**work_package_id:** FNL-S001-P002-WP002
**parent_lod200:** _aos/work_packages/FNL-S001-P001-WP001/LOD200.md
**parent_lod300:** N/A — Track A only
**approved_by:** [PENDING — familynewsletter_build sign-off at L-GATE_SPEC]
**approved_at:** [PENDING]

## 1. Scope reminder

This WP **updates the existing** `src/token_tracker.py` (not a new file). It does three things: (a) replaces the placeholder `claude-sonnet-4-6`/`claude-opus-4-6` model ids and flat pricing with the real `claude-sonnet-5` id and **date-aware** pricing (intro rate through 2026-08-31, standard rate after — LOD200 §6's `cost_cap ≤ $2.50/wk` assumes the post-intro rate); (b) adds a new `research()` method that calls Sonnet-5 with the `web_search`/`web_fetch` server tools, handling the `pause_turn` server-side-loop stop reason and multi-block responses, and logs the `$10/1k` web-search fee as its own `token_usage` row; (c) hardens both `generate()` and `research()` against three Sonnet-5-specific API changes discovered during 2026-07-22 transcript mining: `temperature` is rejected outright, adaptive thinking is on-by-default and billed, and the tokenizer counts ~30% more tokens than 4.6 for the same text. `generate()`'s existing signature, mock mode, and callers must keep working unchanged. This WP does **not** touch `llm.py` (WP001) or the researcher's prompt/item-selection logic (WP003) — it is purely the Claude-API-calling layer both of those sit on top of.

### Assumptions (where the brief was silent — flag these at L-GATE_VALIDATE if wrong)

1. **`allowed_callers: ["direct"]` is set explicitly on both server tools**, disabling `_20260209`'s default dynamic-filtering-via-code-execution behavior. Rationale: a flat, predictable `server_tool_use` → `*_tool_result` response shape is easier for a corner-cutting builder to parse correctly than one with nested code-execution blocks; it keeps the REVIVAL_PLAN §3 cost model (pure token cost + `$10/1k` search fee) accurate with no hidden execution-container variable; and it preserves ZDR eligibility as a free side effect. This is revisitable in a later WP once real search-result volume is observed.
2. **`research()` is SDK-only** — no raw-HTTP fallback path (unlike `generate()`'s existing `_call_sdk`/`_call_http` split). Tool-use + `pause_turn` continuation via hand-rolled JSON is a large, error-prone surface to spec for a corner-cutting builder; `generate()`'s existing HTTP fallback is preserved unchanged (only its text-extraction bug is fixed — see §2.2).
3. **`research()` returns `str`** (the assembled final text), mirroring `generate()`'s existing contract. Parsing that text into structured `title/summary/url/...` items is WP003's job (researcher.py), not this WP's.
4. **`web_fetch_20260209`** (not `_20250910`) is used, paired with `web_search_20260209` for a consistent tool generation, both confirmed Sonnet-5-supported. The brief specified web_search's exact type string but not web_fetch's.
5. **Both `generate()` and `research()` default `thinking` to `{"type": "disabled"}`**, gated by one new settings key (`ai.thinking_enabled`), not two. A caller can opt in per-call.
6. **`max_content_tokens` is added to the `web_fetch` tool definition** (default 20,000) as a second, cheap cost guardrail beyond the requested `max_uses` — Anthropic's own docs show a single fetched PDF can cost ~125K input tokens, which is 4× LOD200's entire weekly cap in one fetch. Flagged separately from the requested guardrails since it's an addition, not asked for verbatim.
7. **`ResearchLoopError` (new, non-retried) vs. generic retry**: a `pause_turn`-cap breach or an unexpected `stop_reason: "tool_use"` are treated as protocol/safety errors, not transient network failures — they are logged (cost included) and raised without going through the generic 3-attempt exponential-backoff wrapper, so a runaway research loop cannot silently 3x its cost before failing.
8. **Unknown `model` in `calculate_cost()` falls back to `claude-sonnet-5` pricing with a logged warning** (same defensive-fallback spirit as the current code, just pointed at the new real id, plus a warning that didn't exist before).

## 2. Technical specification

### 2.1 Date-aware `PRICING` + `calculate_cost()`

**What to implement:**

1. Add `from datetime import date` to the existing `from datetime import datetime, timezone` import line (top of file).
2. Replace the current `PRICING` dict (lines 17–21 of the file as read for this spec — locate by variable name if line numbers have drifted) with:

```python
# Pricing per million tokens (USD). Sonnet-5 intro pricing is DATE-GATED —
# see calculate_cost(). Verified live 2026-07-22 against
# platform.claude.com/docs/en/about-claude/models/overview.md via the
# claude-api skill (do not hand-edit without re-verifying against that page
# or the Models API: client.models.retrieve("claude-sonnet-5")).
PRICING = {
    "claude-sonnet-5": {
        "intro":    {"input": 2.0, "output": 10.0},   # valid through 2026-08-31 inclusive
        "standard": {"input": 3.0, "output": 15.0},   # 2026-09-01 onward
    },
}

# Last day the introductory Sonnet-5 rate applies (inclusive).
SONNET_5_INTRO_PRICING_CUTOFF = date(2026, 8, 31)

# Sonnet-5's tokenizer counts ~30% more tokens than claude-sonnet-4-6 for
# equivalent text (confirmed: platform.claude.com model-migration guide,
# "Migrating to Claude Sonnet 5"). calculate_cost() itself does NOT use this
# constant — it always prices actual response.usage token counts, which are
# already correct regardless of tokenizer. This constant is for
# PRE-CALL ESTIMATION ONLY: sizing prompts, setting max_tokens budgets, or
# projecting cost from a 4.6-based estimate (e.g. REVIVAL_PLAN §3's cost
# table was estimated pre-Sonnet-5 and should be inflated by this factor
# when re-validated against real usage).
SONNET_5_TOKENIZER_INFLATION_VS_4_6 = 1.30

# Web search server-tool fee — billed per search request, separate from and
# in addition to token costs. Not date-gated (no intro rate announced for
# this fee as of 2026-07-22). Source: platform.claude.com web-search-tool
# page, "Usage and pricing".
WEB_SEARCH_COST_PER_1K = 10.00
```

3. Replace `calculate_cost` (currently a bare `@staticmethod` taking `model, input_tokens, output_tokens`) with:

```python
@staticmethod
def calculate_cost(model: str, input_tokens: int, output_tokens: int,
                    newsletter_date: Optional[str] = None) -> float:
    """Calculate USD cost based on Anthropic pricing.

    Sonnet-5 pricing is date-gated: the introductory rate ($2 in / $10 out
    per MTok) applies through 2026-08-31 inclusive; the standard rate
    ($3 in / $15 out) applies from 2026-09-01 onward. `newsletter_date`
    (YYYY-MM-DD) selects which rate applies. If omitted or unparseable,
    falls back to today's UTC date.
    """
    pricing_entry = PRICING.get(model)
    if pricing_entry is None:
        logger.warning(f"[TokenTracker] Unknown model '{model}' for cost "
                        f"calculation; falling back to claude-sonnet-5 pricing.")
        pricing_entry = PRICING["claude-sonnet-5"]

    if "intro" in pricing_entry:
        ref_date = None
        if newsletter_date:
            try:
                ref_date = datetime.strptime(newsletter_date, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"[TokenTracker] Unparseable newsletter_date "
                                f"'{newsletter_date}' for cost calculation; "
                                f"using today's date.")
        if ref_date is None:
            ref_date = datetime.now(timezone.utc).date()
        pricing = (pricing_entry["intro"] if ref_date <= SONNET_5_INTRO_PRICING_CUTOFF
                   else pricing_entry["standard"])
    else:
        pricing = pricing_entry

    cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
    return round(cost, 6)
```

**Acceptance criteria:**
- [ ] AC-01: `calculate_cost("claude-sonnet-5", 1_000_000, 0, "2026-08-31")` returns exactly `2.0` (intro input rate, boundary date inclusive).
- [ ] AC-02: `calculate_cost("claude-sonnet-5", 1_000_000, 0, "2026-09-01")` returns exactly `3.0` (standard input rate, first day after cutoff).
- [ ] AC-03: `calculate_cost("claude-sonnet-5", 0, 1_000_000, "2026-07-22")` returns exactly `10.0` (intro output rate).
- [ ] AC-04: `calculate_cost("claude-sonnet-5", 0, 1_000_000, "2026-09-15")` returns exactly `15.0` (standard output rate).
- [ ] AC-05: `calculate_cost("unknown-model-xyz", 1000, 1000, "2026-07-22")` does not raise; returns the same value as calling with `"claude-sonnet-5"`; a `logger.warning` call is observed (assert via `caplog`/mock).
- [ ] AC-06: `calculate_cost("claude-sonnet-5", 1000, 1000, None)` does not raise and returns a positive float (uses today's UTC date).
- [ ] AC-07: `calculate_cost("claude-sonnet-5", 1000, 1000, "not-a-date")` does not raise; logs a warning; behaves identically to passing `None`.
- [ ] AC-08: `SONNET_5_TOKENIZER_INFLATION_VS_4_6` and `WEB_SEARCH_COST_PER_1K` exist as module-level constants with the exact values above.

### 2.2 Model defaults + safe multi-block text extraction (`generate()` backward-compat fix)

**What to implement:**

1. In `generate()`'s signature, change `model: str = "claude-sonnet-4-6"` to `model: str = "claude-sonnet-5"`, and add a new trailing parameter `thinking_enabled: bool = False`. Full new signature:

```python
def generate(self, module: str, operation: str,
             prompt: str, max_tokens: int,
             model: str = "claude-sonnet-5",
             newsletter_date: Optional[str] = None,
             system: Optional[str] = None,
             thinking_enabled: bool = False) -> str:
```

   Thread `thinking_enabled` through to both `_call_sdk(...)` and `_call_http(...)` (add it as their last parameter too).

2. **Root-cause fix — this is required even though `generate()` passes no tools.** Sonnet-5 runs adaptive thinking by default. When thinking is on, `response.content[0]` is a `ThinkingBlock`, not the text block — so the current line `text = response.content[0].text` silently returns the *thinking* text (SDK path) or raises/returns garbage (HTTP path `data["content"][0]["text"]`) the moment anyone calls `generate()` with `thinking_enabled=True`, and is fragile even with it off. Add two small static helpers (place near `calculate_cost`, above `_mock_summary`):

```python
@staticmethod
def _extract_text_sdk(content_blocks) -> str:
    """Concatenate all text-type blocks from an SDK response.content list.
    Skips thinking/tool_use/server_tool_use/*_tool_result blocks."""
    return "".join(b.text for b in content_blocks if getattr(b, "type", None) == "text")

@staticmethod
def _extract_text_http(content_blocks) -> str:
    """Same as _extract_text_sdk but for raw-HTTP dict responses
    (data["content"]), where blocks are dicts, not objects."""
    return "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
```

3. In `_call_sdk`, replace `text = response.content[0].text` with `text = self._extract_text_sdk(response.content)`. Add `"thinking": {"type": "adaptive"} if thinking_enabled else {"type": "disabled"}` to the `kwargs` dict (unconditionally — always send a `thinking` param, never omit it, since omitting it is what silently turns adaptive thinking on).
4. In `_call_http`, replace `text = data["content"][0]["text"]` with `text = self._extract_text_http(data["content"])`. Add the same `"thinking": {...}` key to the `body` dict, same conditional as above.
5. **Standing rule, both call sites:** never add `temperature`, `top_p`, or `top_k` to `kwargs`/`body`. Sonnet-5 rejects a non-default value for any of these with HTTP 400; the safe rule is to never send them at all.
6. `calculate_cost(...)` calls inside `_call_sdk`/`_call_http` gain the `newsletter_date` argument (already in scope in both methods): `cost = self.calculate_cost(model, input_tokens, output_tokens, newsletter_date)`.

**Acceptance criteria:**
- [ ] AC-09: `generate()`'s default `model` parameter is `"claude-sonnet-5"`.
- [ ] AC-10: A synthetic SDK response whose `content` is `[ThinkingBlock(type="thinking", thinking="..."), TextBlock(type="text", text="hello")]` yields `generate(...) == "hello"` (not the thinking text, no exception).
- [ ] AC-11: A synthetic SDK response with two text blocks `[TextBlock(text="a"), TextBlock(text="b")]` yields `"ab"` (blocks concatenated in order, no separator inserted).
- [ ] AC-12: `_extract_text_http` applied to `[{"type": "thinking", "thinking": "..."}, {"type": "text", "text": "hello"}]` returns `"hello"`.
- [ ] AC-13: Every `client.messages.create(**kwargs)` call site in `_call_sdk` includes a `"thinking"` key; no call site ever includes `"temperature"`, `"top_p"`, or `"top_k"`. Same for the `body` dict in `_call_http`.
- [ ] AC-14: `generate(..., thinking_enabled=True)` sends `{"type": "adaptive"}`; the default call (`thinking_enabled` omitted) sends `{"type": "disabled"}`.
- [ ] AC-15: Existing callers of `generate()` that pass only the pre-existing positional/keyword arguments (no `thinking_enabled`) continue to work with no code change on their side (verified by not requiring `thinking_enabled` — it has a default).

### 2.3 `research()` — new method: signature, tool definitions, mock mode

**What to implement:**

1. Add a new module-level exception class near `PRICING` (after the constants, before the `TokenTracker` class):

```python
class ResearchLoopError(RuntimeError):
    """Raised by TokenTracker.research() when the server-side tool-use loop
    cannot complete safely: either the pause_turn continuation cap was
    exceeded, or the API returned an unexpected stop_reason='tool_use' (no
    client tools are ever defined for research(), so this indicates a
    protocol assumption violated, not a transient failure). NOT retried by
    research()'s outer retry loop — see §2.6."""
    pass
```

2. Add the public `research()` method to `TokenTracker`, placed after `generate()`:

```python
def research(self, module: str, operation: str,
              prompt: str, max_tokens: int,
              model: str = "claude-sonnet-5",
              newsletter_date: Optional[str] = None,
              system: Optional[str] = None,
              web_search_max_uses: int = 5,
              web_fetch_max_uses: int = 3,
              web_fetch_max_content_tokens: int = 20000,
              max_continuations: int = 5,
              thinking_enabled: bool = False) -> str:
    """Call Claude with web_search + web_fetch server tools, handling the
    pause_turn server-side-loop stop reason. Returns the final assembled
    text (mirrors generate()'s contract) — parsing it into structured
    research items is the caller's job (researcher.py, WP003), not this
    method's. Logs a normal token-cost row (operation=<operation>) plus,
    if any searches ran, a separate row (operation='web_search') for the
    $10/1k search fee. Mock mode (self.mock=True) short-circuits before any
    network call, symmetric to generate()'s _mock_generate."""
    if self.mock:
        return self._mock_research(module, operation, prompt, model, newsletter_date)
    if not self.client:
        raise RuntimeError(
            f"[TokenTracker] research() requires the anthropic SDK "
            f"(no HTTP fallback is implemented for tool use): {module}/{operation}"
        )

    for attempt in range(3):
        try:
            return self._research_once(
                module, operation, prompt, max_tokens, model, newsletter_date,
                system, web_search_max_uses, web_fetch_max_uses,
                web_fetch_max_content_tokens, max_continuations, thinking_enabled,
            )
        except ResearchLoopError:
            raise  # protocol/safety-cap errors are not transient — do not retry
        except Exception as e:
            wait = 2 ** (attempt + 1)
            logger.warning(f"[TokenTracker] research() attempt {attempt+1} "
                            f"failed: {e}. Retrying in {wait}s")
            time.sleep(wait)

    logger.error(f"[TokenTracker] All retries failed for research {module}/{operation}")
    raise RuntimeError(f"Claude API research() failed after 3 retries: {module}/{operation}")
```

3. Tool definitions, constructed inside `_research_once` (see §2.4 for the full method — shown here for the exact literal shape):

```python
tools = [
    {
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": web_search_max_uses,
        "allowed_callers": ["direct"],
    },
    {
        "type": "web_fetch_20260209",
        "name": "web_fetch",
        "max_uses": web_fetch_max_uses,
        "max_content_tokens": web_fetch_max_content_tokens,
        "allowed_callers": ["direct"],
    },
]
```

   `allowed_callers: ["direct"]` is **required on both** — see Assumption 1. Without it, `_20260209` tools default to `["code_execution_20260120"]` (dynamic filtering), which is out of scope for this WP.

4. Add `_mock_research`, placed next to `_mock_generate`:

```python
def _mock_research(self, module, operation, prompt, model, newsletter_date):
    """Return a mock research response for --mock builds. Mirrors
    _mock_generate's fallback pattern — logs a nominal cost, no network call."""
    mock_cost = 0.001
    self._log(module, operation, model, 100, 50, mock_cost, newsletter_date)
    return f"[Mock research response for {operation}]"
```

**Acceptance criteria:**
- [ ] AC-16: `TokenTracker(db, mock=True).research("researcher", "research_member", "find stuff", 4096)` returns a string, makes zero network calls, and writes exactly one row to `token_usage` (via `db.log_token_usage`).
- [ ] AC-17: `TokenTracker(db, mock=False)` with `self.client is None` (SDK unavailable, not mock) calling `research(...)` raises `RuntimeError` immediately, with no retry attempts (verify via call-count on a mocked `time.sleep`).
- [ ] AC-18: The `web_search` tool dict passed to `messages.create` always contains a `max_uses` key with an integer value (never omitted) — construct a test that would fail if `max_uses` were accidentally dropped.
- [ ] AC-19: The `web_fetch` tool dict always contains both `max_uses` and `max_content_tokens` keys.
- [ ] AC-20: Both tool dicts contain `"allowed_callers": ["direct"]`.
- [ ] AC-21: `research()`'s default parameter values are exactly: `model="claude-sonnet-5"`, `web_search_max_uses=5`, `web_fetch_max_uses=3`, `web_fetch_max_content_tokens=20000`, `max_continuations=5`, `thinking_enabled=False`.
- [ ] AC-22: `ResearchLoopError` is defined at module level and subclasses `RuntimeError`.

### 2.4 `pause_turn` continuation loop, iteration cap, `ResearchLoopError`

**What to implement:**

1. Add the private `_research_once` method (called by `research()`'s retry wrapper — see §2.3):

```python
def _research_once(self, module, operation, prompt, max_tokens, model,
                    newsletter_date, system, web_search_max_uses,
                    web_fetch_max_uses, web_fetch_max_content_tokens,
                    max_continuations, thinking_enabled):
    tools = [
        {"type": "web_search_20260209", "name": "web_search",
         "max_uses": web_search_max_uses, "allowed_callers": ["direct"]},
        {"type": "web_fetch_20260209", "name": "web_fetch",
         "max_uses": web_fetch_max_uses,
         "max_content_tokens": web_fetch_max_content_tokens,
         "allowed_callers": ["direct"]},
    ]
    thinking = {"type": "adaptive"} if thinking_enabled else {"type": "disabled"}
    messages = [{"role": "user", "content": prompt}]

    total_input_tokens = 0
    total_output_tokens = 0
    total_web_search_requests = 0
    continuations = 0
    response = None

    while True:
        kwargs = {
            "model": model, "max_tokens": max_tokens,
            "messages": messages, "tools": tools, "thinking": thinking,
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)

        usage = getattr(response, "usage", None)
        total_input_tokens += getattr(usage, "input_tokens", 0) or 0
        total_output_tokens += getattr(usage, "output_tokens", 0) or 0
        server_tool_use = getattr(usage, "server_tool_use", None)
        total_web_search_requests += getattr(server_tool_use, "web_search_requests", 0) or 0

        if response.stop_reason == "pause_turn":
            continuations += 1
            if continuations > max_continuations:
                self._log_research_cost(module, operation, model,
                                         total_input_tokens, total_output_tokens,
                                         total_web_search_requests, newsletter_date)
                raise ResearchLoopError(
                    f"research() exceeded max_continuations={max_continuations} "
                    f"pause_turn resumes for {module}/{operation}"
                )
            # Do NOT add an extra user "Continue" message — the API detects
            # the trailing server_tool_use block and resumes automatically.
            messages = messages + [{"role": "assistant", "content": response.content}]
            continue

        if response.stop_reason == "tool_use":
            # No client tools are ever defined for research() — only the
            # server tools above. This stop_reason should be unreachable;
            # treat it as a protocol violation, not a result to parse.
            self._log_research_cost(module, operation, model,
                                     total_input_tokens, total_output_tokens,
                                     total_web_search_requests, newsletter_date)
            raise ResearchLoopError(
                f"research() got unexpected stop_reason='tool_use' "
                f"(no client tools are defined) for {module}/{operation}"
            )

        break  # end_turn / max_tokens / refusal / stop_sequence — done

    text = self._extract_text_sdk(response.content)
    self._log_research_cost(module, operation, model, total_input_tokens,
                             total_output_tokens, total_web_search_requests,
                             newsletter_date)
    return text
```

2. Add the private `_log_research_cost` helper (shared by the normal-completion path and both `ResearchLoopError` raise sites, so cost is never lost):

```python
def _log_research_cost(self, module, operation, model, input_tokens,
                        output_tokens, web_search_requests, newsletter_date):
    """Log the token-cost row (operation=<operation>) and, if any web
    searches ran, a separate row for the $10/1k search fee
    (operation='web_search'). Called exactly once per _research_once
    invocation, on every exit path (success, cap breach, protocol error)."""
    cost = self.calculate_cost(model, input_tokens, output_tokens, newsletter_date)
    self._log(module, operation, model, input_tokens, output_tokens, cost, newsletter_date)
    if web_search_requests > 0:
        search_cost = round((web_search_requests / 1000) * WEB_SEARCH_COST_PER_1K, 6)
        self._log(module, "web_search", "web_search_20260209", 0, 0,
                  search_cost, newsletter_date)
```

**Why the cap and the non-retry matter (context for the validator):** Anthropic's server-side agentic loop for server tools can itself pause and resume (`pause_turn`) many times before finishing; per Anthropic's own guidance, client code must "cap the number of continuations as you would any retry loop." If `research()`'s outer 3-attempt wrapper (§2.6) also retried a cap breach, a single runaway research call could cost up to `3 × (max_continuations + 1)` API round-trips before finally failing — directly threatening LOD200 §6's `$2.50/wk` cap. `ResearchLoopError` is deliberately excluded from that retry.

**Acceptance criteria:**
- [ ] AC-23: Given a mocked `self.client.messages.create` with `side_effect` returning `max_continuations` responses with `stop_reason="pause_turn"` followed by one `stop_reason="end_turn"` response with text `"done"`, `research(...)` returns `"done"` and `messages.create` was called exactly `max_continuations + 1` times.
- [ ] AC-24: Given a mocked client returning `max_continuations + 1` consecutive `pause_turn` responses, `research(...)` raises `ResearchLoopError` (not a generic `RuntimeError` from the retry-exhaustion path) after logging cost — verify `db.log_token_usage` was called before the exception propagates.
- [ ] AC-25: On a `pause_turn` continuation, the re-sent `messages` list is exactly `[original_user_message, {"role": "assistant", "content": <the paused response's content>}]` for the first continuation (growing by one more assistant+prior-context pair per subsequent continuation) — and **no** extra `{"role": "user", "content": "Continue"}` (or similar) message is ever inserted.
- [ ] AC-26: On every continuation request, the `tools` list passed to `messages.create` is byte-identical to the first request's `tools` list (same `max_uses`, same `allowed_callers`) — a missing/changed tool on a continuation is exactly the failure mode Anthropic's docs warn produces a 400.
- [ ] AC-27: A mocked response with `stop_reason="tool_use"` causes `research()` to raise `ResearchLoopError` (via `_research_once`), and this exception is NOT retried by `research()`'s outer loop (`messages.create` call count stays at 1, not 3).
- [ ] AC-28: `total_input_tokens`/`total_output_tokens` passed to `_log_research_cost` are the **sum across all iterations** of the loop, not just the final response's usage — construct a test with 2 iterations each contributing distinct, non-zero `usage.input_tokens`/`output_tokens` and assert the logged row's values equal the sum.
- [ ] AC-29: A response whose `usage.server_tool_use` is `None` (no search performed that turn) does not raise `AttributeError` and contributes `0` to `total_web_search_requests`.

### 2.5 Web-search cost logging (separate `token_usage` row)

**What to implement:** already fully covered by `_log_research_cost` in §2.4. This subsection states the acceptance criteria for the specific requirement "log web_search cost at $10 per 1k searches into token_usage (operation='web_search', model=the tool id)" in isolation, since it is easy to get subtly wrong (e.g. double-counting, or inventing a bogus web_fetch cost row).

**Acceptance criteria:**
- [ ] AC-30: When `total_web_search_requests > 0`, exactly one additional `token_usage` row is logged with `operation="web_search"`, `model="web_search_20260209"`, `input_tokens=0`, `output_tokens=0`, and `cost_usd == round((total_web_search_requests / 1000) * 10.0, 6)`.
- [ ] AC-31: When `total_web_search_requests == 0` (research completed with no searches, e.g. Claude answered from the prompt alone), **no** `operation="web_search"` row is logged — only the normal token-cost row.
- [ ] AC-32: **No** `token_usage` row is ever logged with `operation="web_fetch"` or any web_fetch-specific cost — web_fetch has no per-call dollar fee (Anthropic: "no additional charges beyond standard token costs"); its cost is already fully captured in the normal token-cost row's `input_tokens` (fetched page/PDF content counts as input tokens like any other context). Adding a separate web_fetch cost row would double-count.
- [ ] AC-33: The search-fee row's `newsletter_date` matches the `newsletter_date` passed into `research()` (or `None`, propagated as-is — this row does not independently default the date; only `calculate_cost`'s pricing lookup defaults it, and this row's cost isn't date-gated in the first place per `WEB_SEARCH_COST_PER_1K` being a flat rate).

### 2.6 Retry/rate-limit handling for `research()`

**What to implement:** already shown in full in §2.3's `research()` listing (the `for attempt in range(3): ... except ResearchLoopError: raise ... except Exception: backoff` structure). This subsection isolates its acceptance criteria.

**Acceptance criteria:**
- [ ] AC-34: A mocked `self.client.messages.create` that raises a generic exception (simulating `anthropic.RateLimitError` or `anthropic.APIConnectionError`) on the first 2 calls and succeeds on the 3rd is retried with `time.sleep` called with `2` then `4` (matching `generate()`'s existing `2 ** (attempt + 1)` backoff), and `research()` ultimately returns the successful result.
- [ ] AC-35: A mocked client that always raises a generic exception causes `research()` to raise `RuntimeError` (the "failed after 3 retries" message) after exactly 3 attempts.
- [ ] AC-36: `ResearchLoopError` raised from inside `_research_once` propagates out of `research()` immediately — `time.sleep` is never called, and `messages.create` is never invoked a second time for that error.

### 2.7 `config/settings.json` edits

**What to implement:** apply exactly these edits to `config/settings.json`. The `"ai"` object gains five new keys (all consumed by the future orchestrator/researcher.py as the default values passed into `generate()`/`research()` — `token_tracker.py` itself does not read this file, matching its current design where every tunable is an explicit method parameter). The `"budget"` object's `weekly_alert_usd` changes per LOD200 §6.

Replace the `"ai"` object with:
```json
"ai": {
  "summary_model": "claude-sonnet-5",
  "summary_max_tokens": 200,
  "headline_max_tokens": 50,
  "greeting_max_tokens": 100,
  "puzzle_max_tokens": 150,
  "submission_edit_max_tokens": 300,
  "survey_max_tokens": 100,
  "bridge_max_tokens": 100,
  "thinking_enabled": false,
  "research_max_tokens": 4096,
  "research_web_search_max_uses": 5,
  "research_web_fetch_max_uses": 3,
  "research_web_fetch_max_content_tokens": 20000,
  "research_max_continuations": 5
}
```

Replace the `"budget"` object with:
```json
"budget": {
  "weekly_alert_usd": 2.50,
  "monthly_alert_usd": 10.00
}
```

Only `ai.summary_model` and `budget.weekly_alert_usd` are **value changes**; the other five `ai.*` keys are **new additions**. `budget.monthly_alert_usd` (10.00) and every other top-level section (`schedule`, `content`, `newsletter`, `ftp`, `distribution`) are unchanged and out of scope.

**Acceptance criteria:**
- [ ] AC-37: `config/settings.json` is valid JSON after edit (parses with `json.load`).
- [ ] AC-38: `ai.summary_model == "claude-sonnet-5"`.
- [ ] AC-39: `budget.weekly_alert_usd == 2.50`.
- [ ] AC-40: `budget.monthly_alert_usd == 10.00` (unchanged).
- [ ] AC-41: All five new `ai.*` keys are present with the exact values shown above.
- [ ] AC-42: No other top-level or nested key in `settings.json` is modified, added, or removed.

### 2.8 Sonnet-5 API gotchas — consolidated cost-estimation guidance

**What to implement:** this subsection has no new code beyond what §2.1–2.7 already added (`SONNET_5_TOKENIZER_INFLATION_VS_4_6`, the never-send-`temperature` rule, the thinking-disabled-by-default rule) — it exists to make these three gotchas independently checkable by the cross-engine validator without hunting through every other subsection, per the parent task's explicit requirement to "encode explicitly" all three.

1. **`temperature` (and `top_p`/`top_k`) is never sent.** Verified in §2.2 AC-13. If a future change reintroduces it, Sonnet-5 returns HTTP 400 `invalid_request_error` — see §5.
2. **Adaptive thinking is on-by-default and billed; both `generate()` and `research()` default it OFF via an explicit `{"type": "disabled"}`, controlled by `thinking_enabled`.** Verified in §2.2 AC-14 and §2.3 AC-21. Thinking tokens are billed as output tokens at the same per-MTok rate — disabling it is a direct, deliberate cost-control decision for this cost-capped project, not an incidental default.
3. **Sonnet-5's tokenizer counts ~30% more tokens than `claude-sonnet-4-6`** for equivalent text. Encoded as `SONNET_5_TOKENIZER_INFLATION_VS_4_6 = 1.30` (§2.1 AC-08). This does not change `calculate_cost()`'s math (it always uses real `response.usage` counts) — it matters for **anyone estimating cost or sizing `max_tokens` ahead of a call**, e.g. re-validating REVIVAL_PLAN §3's `~$1.2–1.8/wk` estimate (which predates real Sonnet-5 usage data) against actual weekly `token_usage` totals once edition-1 ships.

**Acceptance criteria:**
- [ ] AC-43: A code comment at the `SONNET_5_TOKENIZER_INFLATION_VS_4_6` definition (already required by §2.1) states its purpose is pre-call estimation only, not the cost-calculation formula — verified by AC-08 plus a doc-string/comment presence check at review time (not unit-testable; confirm by reading the diff at L-GATE_VALIDATE).

## 3. Data model changes (if any)

**None required.** `token_usage.model` is declared `TEXT NOT NULL` in `src/db.py`'s `_init_schema()` with no `CHECK` constraint (unlike, e.g., `newsletters.status`, which does have one) — storing the tool-type string `"web_search_20260209"` in the `model` column (§2.5, AC-30) is schema-valid as-is. `Database.log_token_usage(...)` and its call signature are unchanged; `TokenTracker._log(...)` is unchanged (§2.4 reuses it as-is for both row types). No migration, no new table, no new column.

Illustrative shape of the two row types `research()` can produce (for the validator's reference — not DDL, no change needed):

```sql
-- normal token-cost row (existing shape, now with the real model id)
INSERT INTO token_usage (timestamp, module, operation, model, input_tokens, output_tokens, cost_usd, newsletter_date)
VALUES ('2026-07-24T09:03:11Z', 'researcher', 'research_member', 'claude-sonnet-5', 41230, 2840, 0.1233, '2026-07-24');

-- NEW: web-search fee row (model column holds the tool type, not a model id — by design, per task instruction)
INSERT INTO token_usage (timestamp, module, operation, model, input_tokens, output_tokens, cost_usd, newsletter_date)
VALUES ('2026-07-24T09:03:11Z', 'researcher', 'web_search', 'web_search_20260209', 0, 0, 0.03, '2026-07-24');
```

## 4. API contract changes (if any)

No HTTP endpoints exist in this project (batch/cron pipeline, not a web service). The relevant "contract" is `TokenTracker`'s public Python method surface:

| Method | Change | Before | After |
|---|---|---|---|
| `generate()` | Signature extended (backward-compatible), default `model` changed, internal thinking/text-extraction fix | `model: str = "claude-sonnet-4-6"`, no `thinking_enabled` param, `text = response.content[0].text` | `model: str = "claude-sonnet-5"`, `+ thinking_enabled: bool = False`, `text = self._extract_text_sdk(response.content)` |
| `calculate_cost()` | Signature extended (new optional param), still `@staticmethod` | `calculate_cost(model, input_tokens, output_tokens)` | `calculate_cost(model, input_tokens, output_tokens, newsletter_date=None)` |
| `research()` | **New method** | N/A | `research(module, operation, prompt, max_tokens, model="claude-sonnet-5", newsletter_date=None, system=None, web_search_max_uses=5, web_fetch_max_uses=3, web_fetch_max_content_tokens=20000, max_continuations=5, thinking_enabled=False) -> str` |
| `_research_once()` | **New private method** | N/A | internal, called only by `research()` |
| `_log_research_cost()` | **New private method** | N/A | internal, called only by `_research_once()` |
| `_mock_research()` | **New private method** | N/A | internal, called only by `research()` when `self.mock` |
| `_extract_text_sdk()` / `_extract_text_http()` | **New private static methods** | N/A | internal, used by `_call_sdk`/`_call_http`/`_research_once` |
| `ResearchLoopError` | **New module-level exception class** | N/A | `class ResearchLoopError(RuntimeError)` |
| `PRICING` | Restructured (breaking for any external code that indexed it directly as `PRICING[model]["input"]`) | flat `{"input": float, "output": float}` per model | `claude-sonnet-5` nests `{"intro": {...}, "standard": {...}}` — direct external indexers must go through `calculate_cost()`, not `PRICING` directly |

## 5. Error handling requirements

| Error case | Expected behavior |
|---|---|
| `temperature`/`top_p`/`top_k` sent to Sonnet-5 | Prevented by code review, not runtime-caught: never construct these keys (§2.2 AC-13). If ever reintroduced, Anthropic returns HTTP 400 `invalid_request_error`; the SDK raises `anthropic.BadRequestError`, which `generate()`'s existing 3-attempt retry wrapper will retry uselessly 3 times before failing (temperature is a permanent, not transient, error — this is a known limitation of reusing `generate()`'s generic wrapper, accepted since the real fix is "never send it," not "handle the 400 gracefully"). |
| Rate limit (429) during `generate()` | Unchanged — existing 3-attempt exponential backoff (`2s, 4s, 8s`) in `generate()`'s outer loop, raises `RuntimeError` after exhausting retries. |
| Rate limit (429) / transient network error during `research()` | Retried up to 3 times with the same `2 ** (attempt+1)` backoff as `generate()` (§2.6 AC-34); raises `RuntimeError` after 3 attempts. |
| `pause_turn` loop-cap breach (`continuations > max_continuations`) | Cost accrued so far is logged (`_log_research_cost`, both the token row and, if applicable, the web_search row) **before** raising `ResearchLoopError`. This error is **not** retried by `research()`'s outer wrapper (§2.4 AC-24, §2.6 AC-36) — retrying a runaway loop wastes tokens and does not fix the underlying cause. |
| Unexpected `stop_reason == "tool_use"` (dangling `server_tool_use` awaiting a client tool result) | Should be unreachable — `research()` defines no client tools, only server tools. Treated as a protocol violation: cost logged, `ResearchLoopError` raised, not retried (§2.4 AC-27). |
| In-band tool error inside a `web_search_tool_result`/`web_fetch_tool_result` block (`max_uses_exceeded`, `url_not_accessible`, `too_many_requests`, `query_too_long`, `request_too_large`, `unavailable`, `invalid_tool_input`, `url_too_long`, `url_not_allowed`, `url_not_in_prior_context`, `unsupported_content_type`) | **Not a Python exception.** Per Anthropic's contract, these arrive as HTTP-200 content blocks (`content` is a single error object instead of a result list/dict); Claude sees the error and continues the turn on its own (may retry the search/fetch itself, explain the failure in its final text, or work around it). `research()` requires no special code for these — they flow through `_extract_text_sdk` like any other content. Do not add exception-raising logic for these codes; doing so would break Claude's normal in-turn error recovery. |
| `web_fetch` `max_uses` omitted from the tool definition | **Prevented by construction, not caught** — Anthropic states web_fetch has "no default limit," i.e. omitting `max_uses` means unbounded fetches. §2.3 AC-19 requires the field is always present; there is no runtime fallback if a future edit removes it — this is a code-review-time guarantee, not a defensive check inside `_research_once`. |
| `response.usage` or `response.usage.server_tool_use` missing/`None` (malformed/unexpected usage shape) | Defensive `getattr(..., default) or 0` pattern (§2.4 code) — treats missing fields as `0`, never raises `AttributeError`. Verified by AC-29. No warning is logged for this case (a `None` `server_tool_use` is an expected, normal shape when no search ran that turn — not an anomaly). |
| `newsletter_date` unparseable or `None` in `calculate_cost()` | Falls back to today's UTC date; logs a warning only when a non-`None` value failed to parse (§2.1 AC-06, AC-07). Never raises. |
| Unknown `model` string in `calculate_cost()` | Falls back to `claude-sonnet-5` pricing; logs a warning; never raises (§2.1 AC-05). |
| `anthropic` SDK not installed AND `research()` called (not mock) | Raises `RuntimeError` immediately, no retry, no HTTP fallback attempted (§2.3 AC-17). Distinct from `generate()`, which does have an HTTP fallback for this case (unchanged, out of scope). |
| Sonnet-5 safety-classifier refusal (`stop_reason == "refusal"`) during `generate()` or `research()` | **Not specifically handled by this WP** — falls through as a normal `end_turn`-like exit from the loop/call (the existing/`_research_once`'s `break` catches any `stop_reason` not equal to `pause_turn`/`tool_use`); `_extract_text_sdk` returns whatever text (if any) is present, which may be empty on a pre-output refusal. Flagged in §6 as an explicit deferral — this project's content (family newsletter research/editorial) is very unlikely to trigger cyber/bio safety classifiers, so building refusal-specific handling now is not justified by the task brief; revisit if a real refusal is ever observed in production logs. |

## 6. Out of scope (explicit)

- `llm.py` driver layer (cursor/grok default + anthropic fallback dual-driver) — **WP001**.
- The researcher's prompt construction, two-step gather+critique logic, taste-profile matching, and parsing `research()`'s returned text into structured `title/summary/url/source/category/share_note` JSON items — **WP003** (`researcher.py`). `research()` in this WP returns raw final text only.
- `editor.py`, `teaser.py`, `whatsapp.py`, `publisher.py`, `orchestrator.py` rewiring — separate WPs per REVIVAL_PLAN §3's keep/replace table.
- Budget-alert triggering/escalation to team_00 on `cost_cap` breach (LOD200 §6) — reads `budget.weekly_alert_usd` (this WP updates the *value*, 0.50 → 2.50) and aggregates `token_usage` via `db.get_daily_cost`/`get_monthly_cost` (unchanged, already exist) — the check-and-escalate logic itself belongs to the orchestrator, not `token_tracker.py`.
- Dynamic filtering / `allowed_callers: ["code_execution_20260120"]` mode for the web tools — deliberately disabled (Assumption 1); a future WP may enable it if search-result token volume grows enough to justify the added response-shape complexity.
- `allowed_domains`/`blocked_domains` on either server tool — not wired into `research()`'s signature in this WP; can be added as optional kwargs later without breaking this contract, once WP003 decides it needs domain restriction (e.g. JustWatch/Netflix-only for viewing picks).
- Raw-HTTP fallback path for `research()` (tool use + `pause_turn` via hand-rolled JSON) — SDK-only per Assumption 2.
- The exact JSON/text shape `_mock_research()` returns — kept as a simple placeholder string (`f"[Mock research response for {operation}]"`), mirroring `generate()`'s existing generic fallback; WP003 defines what shape real (and therefore meaningfully-mockable) research output should take.
- Refusal-specific (`stop_reason == "refusal"`) handling beyond falling through the existing loop exit — see §5's last row.
- Any change to `Database`/`db.py` — confirmed unnecessary in §3.

## 7. Test requirements

- **Unit** (no real API calls; mock `self.client.messages.create` and/or `time.sleep`): every AC in §2.1–§2.7 above. Priority/highest-risk targets: `calculate_cost` date-boundary logic (AC-01–AC-08), the `pause_turn` loop's message-history reconstruction and iteration cap (AC-23–AC-29), the retry-vs-no-retry split between generic exceptions and `ResearchLoopError` (AC-34–AC-36), and the text-extraction helpers against synthetic multi-block responses (AC-10–AC-12). Illustrative skeletons:

```python
def test_calculate_cost_intro_boundary():
    assert TokenTracker.calculate_cost("claude-sonnet-5", 1_000_000, 0, "2026-08-31") == 2.0
    assert TokenTracker.calculate_cost("claude-sonnet-5", 1_000_000, 0, "2026-09-01") == 3.0

def test_research_pause_turn_resumes_and_caps(mocker):
    paused = mocker.Mock(stop_reason="pause_turn", content=[...],
                          usage=mocker.Mock(input_tokens=100, output_tokens=10, server_tool_use=None))
    done = mocker.Mock(stop_reason="end_turn",
                        content=[mocker.Mock(type="text", text="done")],
                        usage=mocker.Mock(input_tokens=50, output_tokens=5, server_tool_use=None))
    tracker = TokenTracker(db=mocker.Mock(), api_key="x")
    tracker.client = mocker.Mock()
    tracker.client.messages.create.side_effect = [paused, paused, done]  # max_continuations=2 default in this test
    result = tracker.research("m", "op", "prompt", 1000, max_continuations=2)
    assert result == "done"
    assert tracker.client.messages.create.call_count == 3

def test_research_loop_error_not_retried(mocker):
    tracker = TokenTracker(db=mocker.Mock(), api_key="x")
    tracker.client = mocker.Mock()
    stuck = mocker.Mock(stop_reason="pause_turn", content=[],
                         usage=mocker.Mock(input_tokens=1, output_tokens=1, server_tool_use=None))
    tracker.client.messages.create.return_value = stuck
    with pytest.raises(ResearchLoopError):
        tracker.research("m", "op", "prompt", 1000, max_continuations=0)
    # exactly 1 call (0 continuations allowed -> first pause already breaches) — not retried 3x
    assert tracker.client.messages.create.call_count == 1
```

- **Integration** (real API, small scale, gated — do not run in normal CI given real dollar cost): one live `research()` call with `max_uses` set to 1/1 and a trivial prompt ("what is today's date"), run manually or behind an explicit opt-in flag/env var, to confirm the tool type strings (`web_search_20260209`, `web_fetch_20260209`) and `allowed_callers: ["direct"]` are accepted by the live API with no 400, and that a real `pause_turn` (if triggered) resumes correctly. One live `generate()` call confirming the `thinking: {"type": "disabled"}` param is accepted (no 400) and a normal call still returns real text.
- **Cross-engine validation:** required at L-GATE_VALIDATE per Iron Rule #1 — the validator engine (Sonnet, per the parent mandate) must differ from whichever engine (Grok/Cursor) builds this WP. Validator specifically re-checks: the date-boundary arithmetic in `calculate_cost` (AC-01–AC-04), that no code path constructs a `temperature`/`top_p`/`top_k` key, that `thinking` is present on every request, that `web_fetch`'s `max_uses` can never be omitted, and that the `ResearchLoopError` vs. generic-retry split (§2.6) is implemented exactly as specified (this is the single easiest place for a corner-cutting builder to quietly simplify away the safety property).

## 8. Consuming team sign-off
> I confirm this spec is executable and unambiguous. All open questions are resolved.
> **Signature:** familynewsletter_build | [PENDING — sign at L-GATE_SPEC]

---

## Cross-Engine Validation — Iron Rule

Documents at LOD400+ require cross-engine validation at L-GATE_VALIDATE.
**The validator engine MUST differ from the builder engine — IRON RULE.**
No exception. No waiver. See `gates/L-GATE_VALIDATE_VALIDATE_AND_LOCK.md`.
