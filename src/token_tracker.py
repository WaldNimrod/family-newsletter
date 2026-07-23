"""
Family Newsletter — Token Tracker
Wraps Claude API calls, logs token usage per LOD400 §11.
WP002: claude-sonnet-5 pricing, research() with server tools + pause_turn.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import date, datetime, timezone
from typing import Optional

from .db import Database

logger = logging.getLogger('family.tokens')

# Pricing per million tokens (USD) — sonnet-5 date-gated intro/standard
SONNET_5_INTRO_PRICING_CUTOFF = date(2026, 9, 1)
SONNET_5_TOKENIZER_INFLATION_VS_4_6 = 1.30
WEB_SEARCH_COST_PER_1K = 10.00

PRICING = {
    "claude-sonnet-5": {
        "intro": {"input": 2.0, "output": 10.0},
        "standard": {"input": 3.0, "output": 15.0},
    },
}


class ResearchLoopError(RuntimeError):
    """Raised when research() hits an unrecoverable loop / tool_use / continuation cap."""


class TokenTracker:
    """Wraps Anthropic client. Logs every API call to token_usage table."""

    def __init__(self, db: Database, api_key: Optional[str] = None, mock: bool = False):
        self.db = db
        self.mock = mock
        self.client = None

        if not mock:
            api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
            if api_key:
                try:
                    import anthropic
                    self.client = anthropic.Anthropic(api_key=api_key)
                except ImportError:
                    logger.warning("anthropic SDK not available, falling back to requests")
                    self._api_key = api_key
            else:
                logger.warning("No ANTHROPIC_API_KEY, falling back to mock mode")
                self.mock = True

    def generate(self, module: str, operation: str,
                 prompt: str, max_tokens: int,
                 model: str = "claude-sonnet-5",
                 newsletter_date: Optional[str] = None,
                 system: Optional[str] = None,
                 thinking_enabled: bool = False) -> str:
        """Call Claude API and log usage. Returns response text."""
        if self.mock:
            return self._mock_generate(module, operation, prompt, model, newsletter_date)

        for attempt in range(3):
            try:
                if self.client:
                    return self._call_sdk(
                        module, operation, prompt, max_tokens,
                        model, newsletter_date, system, thinking_enabled,
                    )
                else:
                    return self._call_http(
                        module, operation, prompt, max_tokens,
                        model, newsletter_date, system, thinking_enabled,
                    )
            except Exception as e:
                wait = 2 ** (attempt + 1)
                logger.warning(
                    f"[TokenTracker] Attempt {attempt+1} failed: {e}. Retrying in {wait}s"
                )
                time.sleep(wait)

        logger.error(f"[TokenTracker] All retries failed for {module}/{operation}")
        raise RuntimeError(f"Claude API failed after 3 retries: {module}/{operation}")

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
        """Server-tool research loop (web_search + web_fetch) with pause_turn resume.

        Cloud builds must mock client.messages.create — no live Anthropic.
        allowed_callers omitted pending Mac live-smoke verification.
        """
        if self.mock:
            return self._mock_research(
                module, operation, prompt, model, newsletter_date
            )

        if not self.client:
            raise RuntimeError(
                "research() requires the anthropic SDK client "
                "(no HTTP fallback for server tools)."
            )

        last_err: Optional[Exception] = None
        for attempt in range(3):
            try:
                return self._research_once(
                    module, operation, prompt, max_tokens, model,
                    newsletter_date, system,
                    web_search_max_uses, web_fetch_max_uses,
                    web_fetch_max_content_tokens, max_continuations,
                    thinking_enabled,
                )
            except ResearchLoopError:
                raise
            except Exception as e:
                last_err = e
                wait = 2 ** (attempt + 1)
                logger.warning(
                    f"[TokenTracker.research] Attempt {attempt+1} failed: {e}. "
                    f"Retrying in {wait}s"
                )
                time.sleep(wait)

        raise RuntimeError(
            f"research() failed after 3 retries: {module}/{operation}: {last_err}"
        )

    def _research_once(
        self, module, operation, prompt, max_tokens, model,
        newsletter_date, system,
        web_search_max_uses, web_fetch_max_uses,
        web_fetch_max_content_tokens, max_continuations,
        thinking_enabled,
    ) -> str:
        # BUILD_DIRECTIVE: omit allowed_callers until Mac live smoke confirms.
        tools = [
            {
                "type": "web_search_20260209",
                "name": "web_search",
                "max_uses": web_search_max_uses,
            },
            {
                "type": "web_fetch_20260209",
                "name": "web_fetch",
                "max_uses": web_fetch_max_uses,
                "max_content_tokens": web_fetch_max_content_tokens,
            },
        ]

        messages = [{"role": "user", "content": prompt}]
        total_input_tokens = 0
        total_output_tokens = 0
        total_web_search_requests = 0
        continuations = 0

        while True:
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
                "tools": tools,
                "thinking": {
                    "type": "enabled" if thinking_enabled else "disabled",
                },
            }
            if system:
                kwargs["system"] = system

            response = self.client.messages.create(**kwargs)

            usage = response.usage
            total_input_tokens += getattr(usage, "input_tokens", 0) or 0
            total_output_tokens += getattr(usage, "output_tokens", 0) or 0
            stu = getattr(usage, "server_tool_use", None)
            if stu is not None:
                total_web_search_requests += (
                    getattr(stu, "web_search_requests", 0) or 0
                )

            # Client-side tool_use is unexpected for server tools — hard fail.
            for block in response.content or []:
                if getattr(block, "type", None) == "tool_use":
                    self._log_research_cost(
                        module, operation, model,
                        total_input_tokens, total_output_tokens,
                        total_web_search_requests, newsletter_date,
                    )
                    raise ResearchLoopError(
                        f"research() received client tool_use block in "
                        f"{module}/{operation} — not supported"
                    )

            if response.stop_reason == "pause_turn":
                continuations += 1
                if continuations > max_continuations:
                    self._log_research_cost(
                        module, operation, model,
                        total_input_tokens, total_output_tokens,
                        total_web_search_requests, newsletter_date,
                    )
                    raise ResearchLoopError(
                        f"research() exceeded max_continuations="
                        f"{max_continuations} pause_turn resumes for "
                        f"{module}/{operation}"
                    )
                # P0: REPLACE message state (do NOT append) — each pause_turn
                # response.content is the full assistant turn needed to resume.
                # Appending prior assistant turns re-bills already-paid tokens
                # → O(N²) cost / cost-cap risk. (Corrected AC-25.)
                messages = [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": response.content},
                ]
                continue

            text = self._extract_text_sdk(response)
            self._log_research_cost(
                module, operation, model,
                total_input_tokens, total_output_tokens,
                total_web_search_requests, newsletter_date,
            )
            return text

    def _log_research_cost(
        self, module, operation, model,
        input_tokens, output_tokens, web_search_requests, newsletter_date,
    ) -> None:
        cost = self.calculate_cost(
            model, input_tokens, output_tokens, newsletter_date
        )
        self._log(
            module, operation, model,
            input_tokens, output_tokens, cost, newsletter_date,
        )
        if web_search_requests and web_search_requests > 0:
            search_cost = round(
                (web_search_requests / 1000.0) * WEB_SEARCH_COST_PER_1K, 6
            )
            self._log(
                module, "web_search", "web_search_20260209",
                0, 0, search_cost, newsletter_date,
            )

    def _mock_research(self, module, operation, prompt, model, newsletter_date) -> str:
        self._log(module, operation, model, 100, 50, 0.001, newsletter_date)
        return json.dumps({
            "items": [
                {
                    "title": f"[MOCK research] {operation}",
                    "url": "https://example.com/mock",
                    "blurb": "Mock research item for Cloud pytest.",
                }
            ]
        }, ensure_ascii=False)

    def _call_sdk(self, module, operation, prompt, max_tokens, model,
                  newsletter_date, system, thinking_enabled=False):
        """Call via anthropic SDK."""
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "thinking": {
                "type": "enabled" if thinking_enabled else "disabled",
            },
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        text = self._extract_text_sdk(response)
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = self.calculate_cost(
            model, input_tokens, output_tokens, newsletter_date
        )

        self._log(
            module, operation, model,
            input_tokens, output_tokens, cost, newsletter_date,
        )
        return text

    def _call_http(self, module, operation, prompt, max_tokens, model,
                   newsletter_date, system, thinking_enabled=False):
        """Call via HTTP requests (fallback if SDK unavailable)."""
        import requests

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "thinking": {
                "type": "enabled" if thinking_enabled else "disabled",
            },
        }
        if system:
            body["system"] = system

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers, json=body, timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        text = self._extract_text_http(data)
        input_tokens = data["usage"]["input_tokens"]
        output_tokens = data["usage"]["output_tokens"]
        cost = self.calculate_cost(
            model, input_tokens, output_tokens, newsletter_date
        )

        self._log(
            module, operation, model,
            input_tokens, output_tokens, cost, newsletter_date,
        )
        return text

    @staticmethod
    def _extract_text_sdk(response) -> str:
        parts = []
        for block in response.content or []:
            if getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", "") or "")
        return "".join(parts)

    @staticmethod
    def _extract_text_http(data: dict) -> str:
        parts = []
        for block in data.get("content") or []:
            if block.get("type") == "text":
                parts.append(block.get("text") or "")
        return "".join(parts)

    def _mock_generate(self, module, operation, prompt, model, newsletter_date):
        """Return mock responses for testing."""
        mock_cost = 0.001
        self._log(module, operation, model, 100, 50, mock_cost, newsletter_date)

        if operation == 'greeting':
            return "בוקר טוב, בית ולד! ☀️ היום ב-9 באפריל 1865 הסתיימה מלחמת האזרחים האמריקנית. יום מצוין לקריאה!"
        elif operation == 'greeting_en':
            return "Good morning! On this day in 1865, the American Civil War ended. A great day for reading!"
        elif operation == 'puzzle':
            return "חידת היום 🧩\nבכיתה של צליל יש 30 תלמידים. כל תלמיד לוחץ יד לכל תלמיד אחר בדיוק פעם אחת. כמה לחיצות יד בסה\"כ?\n\n(רמז: חשבו על צירופים)\n\nתשובת אתמול: 42"
        elif operation == 'puzzle_answer':
            return "435 (30×29÷2)"
        elif operation == 'survey':
            return "מה הכתבה שהכי הפתיעה אתכם היום? למה?"
        elif operation == 'survey_en':
            return "What article surprised you most today? Why?"
        elif operation == 'summary':
            return _mock_summary(prompt)
        elif operation == 'headline':
            return _mock_headline(prompt)
        elif operation == 'submission_edit':
            return json.dumps(
                {"headline": "ידיעה מהמשפחה", "summary": "תוכן שנשלח על ידי בן משפחה."},
                ensure_ascii=False,
            )
        elif operation == 'bridge':
            return "נימרוד חשב שזה יעניין אותך!"
        else:
            return f"[Mock response for {operation}]"

    def _log(self, module, operation, model, input_tokens, output_tokens, cost, newsletter_date):
        """Log token usage to DB."""
        ts = datetime.now(timezone.utc).isoformat()
        try:
            self.db.log_token_usage(
                ts, module, operation, model,
                input_tokens, output_tokens, cost, newsletter_date,
            )
        except Exception as e:
            logger.error(f"Failed to log token usage: {e}")
        logger.info(
            f"[Tokens] {module}/{operation}: {input_tokens}+{output_tokens} "
            f"tokens, ${cost:.4f}"
        )

    @staticmethod
    def calculate_cost(
        model: str,
        input_tokens: int,
        output_tokens: int,
        newsletter_date: Optional[str] = None,
    ) -> float:
        """Calculate USD cost based on Anthropic sonnet-5 pricing (date-gated)."""
        pricing_entry = PRICING.get(model)
        if pricing_entry is None:
            logger.warning(
                f"[TokenTracker] Unknown model '{model}', using claude-sonnet-5 rates"
            )
            pricing_entry = PRICING["claude-sonnet-5"]

        # Date-gate intro vs standard
        tier = "standard"
        if newsletter_date:
            try:
                d = date.fromisoformat(newsletter_date[:10])
                if d < SONNET_5_INTRO_PRICING_CUTOFF:
                    tier = "intro"
            except ValueError:
                tier = "standard"
        else:
            # No date → use today's UTC date
            if datetime.now(timezone.utc).date() < SONNET_5_INTRO_PRICING_CUTOFF:
                tier = "intro"

        rates = pricing_entry[tier]
        cost = (
            input_tokens * rates["input"] + output_tokens * rates["output"]
        ) / 1_000_000
        return round(cost, 6)


def _mock_summary(prompt: str) -> str:
    """Generate context-appropriate mock summary."""
    if 'sailing' in prompt.lower() or 'הפלגה' in prompt:
        return "מדריך מקיף למסלולי הפלגה חדשים בים התיכון, כולל עגינות חדשות ונקודות חן מוסתרות."
    elif 'kite' in prompt.lower() or 'קייט' in prompt:
        return "טכנולוגיית הידרופויל חדשה משנה את עולם הקייטסרפינג התחרותי עם מהירויות חסרות תקדים."
    elif 'architecture' in prompt.lower() or 'אדריכלות' in prompt:
        return "פרויקט בנייה ירוקה חדשני בתל אביב משלב passive house עם עיצוב ישראלי. חיסכון של 60% באנרגיה."
    elif 'chemistry' in prompt.lower():
        return "A novel catalyst enables previously impossible organic reactions at room temperature, opening new synthesis pathways."
    elif 'circus' in prompt.lower() or 'קרקס' in prompt:
        return "בית הספר CNAC בצרפת פתח הרשמה לאודישנים. הזדמנות מצוינת לאמנים צעירים."
    elif 'math' in prompt.lower() or 'מתמטיקה' in prompt:
        return "סרטון חדש של Numberphile חוקר בעיות מתמטיות שוות מיליון דולר ומסביר למה עדיין לא נפתרו."
    return "תוכן מעניין ורלוונטי שנמצא עבורך במקורות המידע שלנו."


def _mock_headline(prompt: str) -> str:
    """Generate mock headline."""
    if 'sailing' in prompt.lower():
        return "מדריך ההפלגות של 2026 בים התיכון"
    elif 'kite' in prompt.lower():
        return "טכנולוגיית פויל חדשה שוברת שיאי מהירות"
    return "כותרת לדוגמה"
