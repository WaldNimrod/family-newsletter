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

# researcher.py — Per-Member Two-Step Research + Screen-Scout — LOD400 Implementation Spec

**work_package_id:** FNL-S001-P002-WP003
**parent_lod200:** _aos/work_packages/FNL-S001-P001-WP001/LOD200.md
**parent_lod300:** N/A — Track A only
**approved_by:** [PENDING — familynewsletter_build sign-off at L-GATE_SPEC]
**approved_at:** [PENDING]

## 1. Scope reminder

This WP creates **`src/researcher.py`** (new file) plus small, explicit, surgical additions to `src/models.py`, `src/m1_profiles.py`, and `src/db.py` (§3) that `researcher.py` depends on. The module implements REVIVAL_PLAN §3.5 Layer 4's two-step research: for each of the 5 family members, `research_member()` makes **one call** to `token_tracker.research()` (WP002) whose prompt instructs Claude to (a) gather ~8 real candidate items via up to 8 `web_search` calls, then (b) — within the **same** turn — critique and narrow to exactly 3 using three explicit tests, returning structured JSON. `research_all_members()` runs this for all 5 members and never lets one member's failure block the others. `screen_scout()` implements REVIVAL_PLAN §3.5.1's "🍿 מה רואים השבוע": one family-wide pick + one rotating personal pick, each independently verified — via real search, in the same call — for Netflix-IL/Prime-IL availability **and** Hebrew subtitles before it is ever accepted. Both entry points call `token_tracker.research()` directly (never `llm.complete()`) — WP001's `complete(..., tools=...)` explicitly raises `NotImplementedError`, and modifying `llm.py` is out of this WP's scope (§6) — so this module has a **hard, direct dependency on WP002 landing first** (§1 Assumption 1). Every accepted item is persisted immediately: research items into the existing `content_archive` table (the dedup blocklist source for future runs), viewing picks into a **new** `watchlist` table (§3) — so the 45-day dedup blocklist is self-sustaining without depending on any other, not-yet-built WP.

### Assumptions (where the brief was silent — flag these at L-GATE_VALIDATE if wrong)

1. **Hard dependency on WP002's `token_tracker.research()` — no reduced-functionality fallback.** Unlike WP001 (`llm.py`), whose `anthropic` driver works with zero dependency on the not-yet-verified `cursor` driver, `researcher.py` has no meaningful degraded mode if `TokenTracker.research()` doesn't exist yet — its entire job is calling that method. Pure unit tests (mocking `tt.research`) can and must proceed independently of WP002's landing status; end-to-end testing cannot.
2. **`research_member()`/`screen_scout()` call `token_tracker.research()` directly, never `llm.complete()`.** The task brief's "researcher calls token_tracker.research() for web-search work and/or llm.complete() for critique" is resolved in favor of a **single `research()` call per member/scout run**, per REVIVAL_PLAN §3.5 Layer 4's literal wording — "מחקר לכל בן משפחה בשני צעדים **באותה קריאה**" ("research for each family member in two steps, **in the same call**"). `llm.complete()` is not used anywhere in this module for v1: it cannot accept `tools` yet (WP001 §1 Assumption 4), and wiring tool-support through `llm.py` is explicitly out of THIS WP's scope (§6). This closes the brief's "and/or" ambiguity definitively.
3. **The 45-day dedup blocklist is GLOBAL, not per-member.** Sourced from the existing `content_archive.url` / `content_archive.content_hash` columns (already exactly what `Database.get_recent_hashes()` reads, just reused with `days=45`). A per-member-scoped blocklist would require either a new `member_id` column on `content_archive` (schema change to a table REVIVAL_PLAN §3 marks "שמור" / keep-as-is, and not requested by this task's DATA MODEL instructions) or an indirect join through `newsletter_items` (populated by the editor/orchestrator stage, not yet built — see Assumption 4). A global blocklist is simpler, requires zero schema changes to `content_archive`, and the cost of the simplification (an item picked for one member 3 weeks ago is not offered to a *different* member either) is low: cross-member duplicate hits are rare in practice since each member's taste profile is distinct, and LOD200 §3 explicitly accepts "~70% on-target" content quality.
4. **`research_member()` and `screen_scout()` persist their own accepted output immediately** — research items into `content_archive` (via a new `Database.archive_researched_item()`, §2.10), viewing picks into `watchlist` (via `Database.insert_watchlist_pick()`, §2.10) — rather than deferring persistence to the orchestrator or editor (neither exists yet as of this WP). This is necessary for the dedup loop (Assumption 3) and the personal-pick rotation (§2.12) to be self-sustaining across weekly runs within this WP's own boundary, without an undocumented dependency on a future WP correctly wiring persistence for a feature (dedup) this WP's own acceptance criteria must be able to test end-to-end.
5. **`MemberProfile` (`models.py`) and `load_profiles()` (`m1_profiles.py`) gain one new field: `media_sources: list[dict]`.** `researcher.py` needs each member's `family.json` `media_sources` array — REVIVAL_PLAN §3 explicitly repurposes it as "רמזי מקורות מועדפים" ("preferred source hints") for the LLM researcher — but the current `MemberProfile` dataclass does not expose it (the loader silently drops the key). `FamilyConfig.shared_interests` is already a raw, unfiltered `dict` populated directly from `family.json`'s `shared_interests` object, so `family.shared_interests["bookshelf"]["books"]` is **already** accessible with **zero** changes required there.
6. **Mock mode (`tt.mock is True`) bypasses the real prompt/parse pipeline entirely**, via small deterministic local mock-item generators (§2.7) — mirroring `TokenTracker._mock_generate()`'s existing per-operation canned-response pattern. Reason: `TokenTracker._mock_research()` (WP002 §2.3) returns a fixed **non-JSON** placeholder string (`f"[Mock research response for {operation}]"`). Left unhandled, every `--mock` build would have `_parse_json_response()` fail on that string for every member, every week, silently producing 0 items always — defeating the entire purpose of `--mock` (cheaply smoke-testing full pipeline wiring, including the `content_archive`/`watchlist` insert paths).
7. **Content-shortfall is never a raised exception — only a genuinely missing `profiles/<id>.md` file, or an unresolvable `member_id`, raises.** Fewer than 3 valid items after one retry, or a viewing pick that fails verification twice, are logged and returned as partial/`None` results, never exceptions. A single member's research shortfall (content scarcity, guardrail rejections, a flaky search) must never crash the other 4 members' research or the weekly build. `_call_research` (§2.8) therefore catches `Exception` broadly and deliberately — a wider catch than `llm.py`'s typed-exception approach, because `researcher.py` sits one layer above `token_tracker.research()` and does not need to distinguish *why* a call failed, only whether usable text came back.
8. **Guardrails are layered, and the split between prompt-only and code-enforced is explicit, not accidental.** The primary control for every rule (§2.5) is the prompt instruction. A small, explicitly best-effort, keyword-based code filter is added **only** where a rule is reliably keyword-detectable: self-reference by a member's own full name, a fixed political-terms list, and disallowed streaming content ratings. Spoiler-avoidance (Death Gate Cycle, Avatar) and Shaked's "never labeled" gender/identity framing rule are **prompt-only** — not reliably checkable by a keyword filter — and this limitation is stated explicitly in §5, not silently left unhandled.

## 2. Technical specification

This WP creates one new file, `src/researcher.py`, plus edits to three existing files. Implement `src/researcher.py`'s components **in this exact order within that one file** (later components reference names defined earlier — e.g. `research_member` at §2.10 references the prompt builder at §2.9, which references the guardrails at §2.5).

### 2.0 Prerequisite edits — `src/models.py` and `src/m1_profiles.py`

**What to implement:**

1. In `src/models.py`, add one new field to the `MemberProfile` dataclass — append it as the **last** field (after `preferred_format`), with a default, so it does not break dataclass field-ordering rules (all other `MemberProfile` fields are non-default):

```python
@dataclass
class MemberProfile:
    id: str
    name: str
    name_en: str
    nickname: str
    nickname_newsletter: str
    role: str  # "parent" | "child"
    phone: Optional[str]
    email: Optional[str]
    language_preference: str  # "he" | "en" | "both"
    interests: list[Interest]
    max_items_per_day: int
    preferred_format: str  # "summary" | "headline"
    media_sources: list[dict] = field(default_factory=list)  # NEW — FNL-S001-P002-WP003
```

   `field` is already imported at the top of `models.py` (`from dataclasses import dataclass, field`) — no new import required.

2. In `src/m1_profiles.py`, `load_profiles()`, add one line to the `MemberProfile(...)` construction (the existing call already spans multiple keyword arguments — add this as the new last argument):

```python
        members.append(MemberProfile(
            id=m['id'],
            name=m['name'],
            name_en=m.get('name_en', m['name']),
            nickname=m.get('nickname', m['name']),
            nickname_newsletter=m.get('nickname_newsletter', m.get('nickname', m['name'])),
            role=m.get('role', 'child'),
            phone=m.get('phone'),
            email=m.get('email'),
            language_preference=m['language_preference'],
            interests=interests,
            max_items_per_day=prefs.get('max_items_per_day', 3),
            preferred_format=prefs.get('preferred_format', 'summary'),
            media_sources=m.get('media_sources', []),  # NEW — FNL-S001-P002-WP003
        ))
```

No other change to either file. `FamilyConfig.shared_interests` needs no change (§1 Assumption 5).

**Acceptance criteria:**
- [ ] AC-01: `MemberProfile` has a `media_sources` field of type `list[dict]`, defaulting to `[]` when omitted from a constructor call.
- [ ] AC-02: `load_profiles("config/")` on the real `config/family.json` returns a `FamilyConfig` whose `nimrod` member has `media_sources` containing 8 entries (matching the file's current `nimrod.media_sources` array — spot-check the first entry is `{"type": "rss", "url": "https://www.yachtingworld.com/feed", "name": "Yachting World"}`).
- [ ] AC-03: A member whose `family.json` entry has no `media_sources` key at all loads with `media_sources == []` (no `KeyError`).
- [ ] AC-04: `git diff` for this WP's `models.py`/`m1_profiles.py` edits touches only the lines shown above — no reformatting, no reordering of existing fields.

### 2.1 `src/researcher.py` — module foundations: imports, exceptions, constants

**What to implement:**

1. Module docstring + imports:

```python
"""
Family Newsletter — Researcher
Two-step (gather + critique) content research per family member, plus the
weekly "🍿 מה רואים השבוע" screen-scout. Per LOD400 FNL-S001-P002-WP003.
"""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Optional

from .db import Database
from .models import FamilyConfig, MemberProfile, MemberNotFound
from .m1_profiles import get_member_by_id
from .token_tracker import TokenTracker

logger = logging.getLogger('family.researcher')
```

2. Exception hierarchy:

```python
class ResearcherError(Exception):
    """Base class for all researcher.py errors."""


class TasteProfileMissingError(ResearcherError):
    """Raised when profiles/<member_id>.md does not exist, or exists but is
    empty/whitespace-only. This is a deployment/config bug (a required input
    file is missing), NOT a content-quality issue — unlike a content
    shortfall (handled by returning fewer items, never raising; §1
    Assumption 7), research_member()/screen_scout() cannot even construct a
    prompt without this file, so it is not recoverable inside this module."""
```

3. Module-level constants:

```python
DEFAULT_DEDUP_DAYS = 45
DEFAULT_MAX_WEB_SEARCHES_RESEARCH = 8
DEFAULT_MAX_WEB_SEARCHES_SCOUT = 3
DEFAULT_TARGET_ITEM_COUNT = 3
DEFAULT_RESEARCH_MAX_TOKENS = 4096
DEFAULT_SCOUT_MAX_TOKENS = 2048
DEFAULT_WEB_FETCH_MAX_USES_RESEARCH = 3
DEFAULT_WEB_FETCH_MAX_USES_SCOUT = 2

_MAX_CANDIDATES_CONSIDERED = 10   # safety cap on how many "items" entries in
                                  # one LLM response are even inspected, in
                                  # case the model ignores the "exactly N" ask
_MAX_BLOCKLIST_URLS_SHOWN = 60    # caps the DO-NOT-REPEAT block's size as
                                  # content_archive grows over months —
                                  # a direct, deliberate token/cost guardrail
```

**Acceptance criteria:**
- [ ] AC-05: `from src import researcher` succeeds with no import-time errors, no network calls, no DB/file I/O beyond its own definitions.
- [ ] AC-06: `ResearcherError` and `TasteProfileMissingError` are defined at module level; `TasteProfileMissingError` subclasses `ResearcherError`, which subclasses `Exception`.
- [ ] AC-07: All 9 constants in item 3 above exist at module level with exactly the values shown.

### 2.2 Taste-profile loading + member/language helpers

**What to implement:**

```python
def _load_taste_profile(member_id: str, profiles_dir: str = "profiles/") -> str:
    """Read profiles/<member_id>.md verbatim — the free-prose taste profile
    that is the PRIMARY research input per REVIVAL_PLAN §3.5 Layer 1 ("לחוקר-
    LLM פרוזה עשירה עדיפה דרמטית על רשימות מילים"). family.json's structural
    fields (name, language_preference, media_sources) supplement this; they
    do not replace it. Raises TasteProfileMissingError if the file is
    missing or empty/whitespace-only."""
    path = Path(profiles_dir) / f"{member_id}.md"
    if not path.exists():
        raise TasteProfileMissingError(f"Taste profile not found: {path}")
    text = path.read_text(encoding='utf-8').strip()
    if not text:
        raise TasteProfileMissingError(f"Taste profile is empty: {path}")
    return text


def _member_language(member: MemberProfile) -> str:
    """Returns 'en' or 'he'. Only an explicit language_preference of 'en'
    (Shaked, per family.json and per LOD200 §4 'Shaked — English only')
    yields English; 'he' and 'both' both yield Hebrew, matching every other
    member's profiles/*.md, which are written in Hebrew regardless of
    family.json's 'both' setting for Nimrod (he consumes both languages of
    SOURCE material; his newsletter copy is Hebrew, per STYLE_GUIDE's
    Hebrew-primary RTL design)."""
    return "en" if member.language_preference == "en" else "he"
```

**Acceptance criteria:**
- [ ] AC-08: `_load_taste_profile("nimrod", "profiles/")` against the real repo returns a non-empty string starting with `"# נימרוד"`.
- [ ] AC-09: `_load_taste_profile("nobody", "profiles/")` raises `TasteProfileMissingError` whose message contains the attempted path.
- [ ] AC-10: A profile file that exists but contains only whitespace raises `TasteProfileMissingError` (not silently treated as a valid empty profile).
- [ ] AC-11: `_member_language(member)` returns `"en"` when `member.language_preference == "en"`, and `"he"` for both `"he"` and `"both"`.

### 2.3 Prompt-context formatting helpers

**What to implement:**

```python
def _format_source_hints(member: MemberProfile) -> str:
    """Renders family.json's per-member media_sources array (repurposed per
    REVIVAL_PLAN §3 as 'preferred source hints') as a bullet list for the
    prompt. Covers the 'surface YouTube items where relevant' requirement —
    a member's known-good YouTube channels appear here as ordinary
    media_sources entries (type='youtube'), with no special-casing needed."""
    if not member.media_sources:
        return "(no specific preferred sources on file — rely on general web search)"
    lines = []
    for s in member.media_sources:
        name = s.get('name', '?')
        stype = s.get('type', 'web')
        url = s.get('url', '')
        lines.append(f"- {name} ({stype}): {url}" if url else f"- {name} ({stype})")
    return "\n".join(lines)


def _format_bookshelf(family: FamilyConfig, member_id: str) -> str:
    """Renders config/family.json shared_interests.bookshelf.books, filtered
    to the subset whose themes are flagged relevant to this member in
    shared_interests.bookshelf.profile_insights.relevance (currently curated
    for 'nimrod', 'michal', and 'shared' only — members with no curated
    relevance list yield the 'no specifically relevant' fallback rather than
    dumping all 15 books indiscriminately). Satisfies the 'surface מהמדף שלנו
    / From Our Shelf content' requirement (task MODULE SCOPE item 4)."""
    bookshelf = family.shared_interests.get("bookshelf", {})
    books = bookshelf.get("books", [])
    relevance = bookshelf.get("profile_insights", {}).get("relevance", {})
    relevant_themes = set(relevance.get(member_id, [])) | set(relevance.get("shared", []))
    if not relevant_themes:
        return "(no specifically relevant family bookshelf titles on file for this member)"
    lines = []
    for b in books:
        themes = set(b.get("themes", []))
        if themes & relevant_themes:
            title_he = b.get('title_he', '')
            title_en = b.get('title_en', '')
            category = b.get('category', '')
            lines.append(f"- \"{title_he}\" / \"{title_en}\" ({category}) — themes: {', '.join(sorted(themes))}")
    return "\n".join(lines) if lines else "(no specifically relevant family bookshelf titles on file for this member)"


def _format_blocklist(urls: set[str], limit: int = _MAX_BLOCKLIST_URLS_SHOWN) -> str:
    """Renders the dedup blocklist for the prompt. Capped at `limit` entries
    (most-recent-agnostic — plain sorted order, since content_archive has no
    reliable single sort key that means 'most relevant to omit' beyond
    fetched_at, and the DB query already scopes to the last N days) to keep
    the prompt — and therefore cost — bounded as content_archive grows."""
    if not urls:
        return "(none yet)"
    shown = sorted(urls)[:limit]
    return "\n".join(f"- {u}" for u in shown)
```

**Acceptance criteria:**
- [ ] AC-12: `_format_source_hints(member)` for a member with `media_sources == []` returns the literal fallback string shown above.
- [ ] AC-13: `_format_source_hints(member)` for Tzlil's real `media_sources` (5 entries) returns a 5-line bullet string, each line containing that entry's `name` and `url`.
- [ ] AC-14: `_format_bookshelf(family, "nimrod")` against real `config/family.json` includes the "קטן זה יפה" / "Small is Beautiful" entry (its themes include `"sustainability"`, which is in `relevance.nimrod`) and does NOT include "סופה של אליס" / "Alice's Storm" (category `israeli-literature`, no overlapping theme).
- [ ] AC-15: `_format_bookshelf(family, "shaked")` (no curated `relevance.shaked` entry) returns the "no specifically relevant" fallback string.
- [ ] AC-16: `_format_blocklist(set())` returns `"(none yet)"`. `_format_blocklist({f"https://example.com/{i}" for i in range(100)}, limit=60)` returns exactly 60 lines.

### 2.4 JSON response parsing (self-contained — does not import from `llm.py`)

**What to implement:** a local, self-contained JSON-extraction helper. `token_tracker.research()` (WP002) returns raw `str` with **no** JSON-parsing robustness of its own — unlike `llm.complete()` (WP001 §2.3), which has this built in. Since `researcher.py` calls `tt.research()` directly (§1 Assumption 2), not `llm.complete()`, it needs its own copy. This deliberately duplicates the *shape* of `llm.py`'s `_strip_code_fence`/`_extract_outer_json`/`_try_parse_json` (same robustness contract, same "top-level object only, not an array" convention) rather than importing `llm.py`'s private (`_`-prefixed) functions across a module boundary — a small, stable, easily-copy-verified utility is cheaper here than that coupling.

```python
_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    """Strip a single leading/trailing markdown code fence, if the ENTIRE
    trimmed string is wrapped in one. Returns the input unchanged (just
    whitespace-trimmed) otherwise."""
    text = text.strip()
    m = _FENCE_RE.match(text)
    return m.group(1).strip() if m else text


def _extract_outer_json(text: str) -> str:
    """Find the outermost {...} span (first '{' to the LAST '}') and return
    that slice — recovers a JSON object embedded in leading/trailing prose.
    Unlike llm.py's version, this does NOT also look for a leading '[' —
    researcher.py's contract is always a top-level JSON *object*
    ({"items": [...]} or {"family_pick": ..., "personal_pick": ...} or
    {"pick": ...}), never a bare top-level array."""
    start = text.find("{")
    if start == -1:
        return text
    end = text.rfind("}")
    if end == -1 or end < start:
        return text
    return text[start:end + 1]


def _parse_json_response(raw_text: Optional[str]) -> Optional[dict]:
    """Best-effort parse of an LLM response into a JSON object (dict).
    Returns None (never raises) if raw_text is None/empty or cannot be
    parsed as a top-level JSON object after code-fence stripping and
    outer-brace extraction."""
    if not raw_text:
        return None
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

**Acceptance criteria:**
- [ ] AC-17: `_parse_json_response('{"items": []}')` returns `{"items": []}`.
- [ ] AC-18: `_parse_json_response('```json\n{"items": []}\n```')` returns `{"items": []}`.
- [ ] AC-19: `_parse_json_response('Here you go:\n{"items": []}\nEnjoy!')` returns `{"items": []}`.
- [ ] AC-20: `_parse_json_response('[1, 2, 3]')` returns `None` (bare top-level array is a parse failure under this contract, same convention as `llm.py`).
- [ ] AC-21: `_parse_json_response(None)` and `_parse_json_response("")` both return `None` with no exception.
- [ ] AC-22: `_parse_json_response("not json")` returns `None`.

### 2.5 Content guardrails

**What to implement:**

```python
# Per-member "never surface content ABOUT the member themselves" guard.
# researcher.py's job is finding THIRD-PARTY content matching a member's
# taste, never content about the member personally. This is the concrete,
# keyword-checkable core of two LOD200 §4/§5 rules: "Yoyo's nail business
# NOT named without consent" (she is never named alongside business/nail-art
# content — third-party nail-art content itself remains fully researchable)
# and Shaked's "no personal framing" (his own name should never appear in
# content selected FOR him). Applied to every member, not only Yoyo/Shaked,
# for consistency and because it is a sound rule generally.
SELF_NAME_TERMS = {
    "nimrod": ["נימרוד ולד"],
    "michal": ["מיכל ולד", "מיכל בן-צבי", "מיכל בן צבי"],
    "shaked": ["שקד ולד", "Shaked Wald"],
    "maayan": ["מעיין ולד", "יויו ולד", "yuyu_m2569"],
    "tzlil": ["צליל ולד"],
}

# Best-effort, NON-EXHAUSTIVE keyword guard — global, applies to every
# member's every item. This is a defense-in-depth layer only, backstopping
# the "no politics" prompt instruction (§2.9); it is not a substitute for
# it and will not catch subtle political framing. Documented limitation
# (§1 Assumption 8, §5): this mechanism cannot and does not attempt to catch
# spoilers or Shaked's "never labeled" framing rule — those are prompt-only.
POLITICAL_KEYWORDS = [
    "כנסת", "ח\"כ", "חבר כנסת", "ראש הממשלה", "בחירות", "קואליציה",
    "אופוזיציה", "נתניהו",
    "knesset", "election", "parliament", "prime minister",
    "president biden", "president trump",
]

# Streaming content ratings treated as too old for this household (a
# household including a 13-year-old) — used only by screen_scout's viewing-
# pick validation (§2.11), not by research_member. A DENYLIST (not an
# allowlist) because Israeli Netflix/Prime surface inconsistent rating
# vocabularies (MPAA, TV Parental Guidelines, and local age labels) and a
# denylist of clearly-adult markers is more robust to that variance than
# trying to enumerate every acceptable rating string. Matches
# profiles/family.md's explicit "עד 16+ זה בסדר" (up to 16+ is fine) policy —
# only ratings ABOVE that ceiling need to be caught.
DISALLOWED_CONTENT_RATINGS = {"r", "nc-17", "tv-ma", "18+", "unrated", "x"}


def _apply_content_guardrails(item: dict, member_id: str) -> Optional[str]:
    """Returns None if `item` passes all code-level guardrails, else a short
    string reason (for logging) explaining why it was dropped. Checks
    title + summary + share_note (case-insensitive substring match)."""
    haystack = " ".join([
        item.get('title', ''), item.get('summary', ''), item.get('share_note', ''),
    ]).lower()
    for term in SELF_NAME_TERMS.get(member_id, []):
        if term.lower() in haystack:
            return f"self-reference guard: contains '{term}'"
    for term in POLITICAL_KEYWORDS:
        if term.lower() in haystack:
            return f"political-keyword guard: contains '{term}'"
    return None


def _rating_allowed(content_rating: Optional[str]) -> bool:
    """True if content_rating is missing/unknown, OR is not in the
    disallowed set. An unknown rating is allowed to pass THIS check — the
    availability/subtitle verification checks (§2.11) still gate the pick
    independently, so an unrated-but-otherwise-valid title is not rejected
    on rating alone."""
    if not content_rating or not isinstance(content_rating, str):
        return True
    return content_rating.strip().lower() not in DISALLOWED_CONTENT_RATINGS


def _as_bool(value) -> Optional[bool]:
    """Normalizes a JSON-decoded value that is SUPPOSED to be a boolean.
    Accepts a real bool as-is; defensively also accepts the strings "true"/
    "false" (case-insensitive) since LLMs occasionally emit quoted booleans
    despite explicit prompt instructions to use JSON boolean literals.
    Returns None for anything else (caller must treat None as "not
    confirmed", i.e. fail closed, never as True)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v == "true":
            return True
        if v == "false":
            return False
    return None
```

**Acceptance criteria:**
- [ ] AC-23: `_apply_content_guardrails({"title": "מעיין ולד עושה ציפורניים", "summary": "", "share_note": ""}, "maayan")` returns a non-`None` reason containing `"self-reference"`.
- [ ] AC-24: `_apply_content_guardrails({"title": "עסקים בנייל ארט צעירים", "summary": "כתבה על יזמות", "share_note": ""}, "maayan")` (third-party nail-art content, no self-reference) returns `None` — confirms researching the TOPIC remains allowed.
- [ ] AC-25: An item mentioning `"ראש הממשלה"` in its summary returns a non-`None` reason containing `"political-keyword"`, for every `member_id`.
- [ ] AC-26: `_rating_allowed("PG-13")`, `_rating_allowed("13+")`, `_rating_allowed(None)`, and `_rating_allowed("")` all return `True`. `_rating_allowed("TV-MA")` and `_rating_allowed("R")` both return `False`. `_rating_allowed("tv-ma")` (lowercase) also returns `False` (case-insensitive).
- [ ] AC-27: `_as_bool(True) is True`, `_as_bool(False) is False`, `_as_bool("true") is True`, `_as_bool("FALSE") is False`, `_as_bool("maybe") is None`, `_as_bool(1) is None` (integers are not accepted — only real bools or the two exact strings).

### 2.6 Research-item validation

**What to implement:**

```python
_URL_RE = re.compile(r'^https?://\S+$')
_REQUIRED_ITEM_KEYS = ("title", "summary", "url", "source", "category", "share_note")
_ITEM_MAX_LEN = {"title": 150, "summary": 800, "source": 80, "category": 40, "share_note": 300}


def _validate_research_item(candidate) -> Optional[dict]:
    """Validates and normalizes one candidate item dict against the
    title/summary/url/source/category/share_note contract. Returns a clean
    dict (all fields stripped, over-length text fields TRUNCATED — not
    rejected, since a slightly-too-long summary is still usable content) on
    success, or None if `candidate` is not a dict, is missing any required
    key, has a non-string or empty-after-strip value for any required key,
    or has a url that does not match _URL_RE (a malformed URL cannot be
    salvaged by truncation, so THAT is a hard reject, unlike text length)."""
    if not isinstance(candidate, dict):
        return None
    out = {}
    for key in _REQUIRED_ITEM_KEYS:
        val = candidate.get(key)
        if not isinstance(val, str) or not val.strip():
            return None
        val = val.strip()
        max_len = _ITEM_MAX_LEN.get(key)
        if max_len and len(val) > max_len:
            val = val[:max_len].rstrip()
        out[key] = val
    if not _URL_RE.match(out["url"]):
        return None
    return out


def _parse_and_validate_items(raw_text: Optional[str], member_id: str,
                               blocklist_urls: set[str],
                               blocklist_hashes: set[str]) -> list[dict]:
    """End-to-end: parse raw_text as {"items": [...]}, then for each
    candidate (capped at _MAX_CANDIDATES_CONSIDERED), validate shape, drop
    duplicates (against the DB blocklist, AND against earlier items already
    accepted from this SAME batch), then apply content guardrails. Returns
    only the items that survive every check, in the order the model
    returned them. Never raises."""
    parsed = _parse_json_response(raw_text)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("items"), list):
        return []

    valid = []
    seen_urls_this_batch = set()
    for candidate in parsed["items"][:_MAX_CANDIDATES_CONSIDERED]:
        item = _validate_research_item(candidate)
        if item is None:
            continue
        if item["url"] in blocklist_urls or item["url"] in seen_urls_this_batch:
            logger.warning(f"[researcher] dropped duplicate item for {member_id}: {item['url']}")
            continue
        content_hash = hashlib.sha256((item["title"] + item["summary"]).encode()).hexdigest()[:16]
        if content_hash in blocklist_hashes:
            logger.warning(f"[researcher] dropped content-hash duplicate for {member_id}: {item['title']}")
            continue
        reason = _apply_content_guardrails(item, member_id)
        if reason:
            logger.warning(f"[researcher] dropped item for {member_id} ({reason}): {item['title']}")
            continue
        seen_urls_this_batch.add(item["url"])
        valid.append(item)
    return valid
```

**Acceptance criteria:**
- [ ] AC-28: `_validate_research_item({"title": "t", "summary": "s", "url": "https://x.com", "source": "src", "category": "cat", "share_note": "n"})` returns a dict with all 6 keys, values stripped.
- [ ] AC-29: `_validate_research_item({"title": "t", "summary": "s", "url": "not-a-url", "source": "src", "category": "cat", "share_note": "n"})` returns `None` (malformed URL, hard reject).
- [ ] AC-30: `_validate_research_item({"title": "x" * 200, "summary": "s", "url": "https://x.com", "source": "src", "category": "cat", "share_note": "n"})` returns a dict whose `title` is exactly 150 characters (truncated, not rejected).
- [ ] AC-31: `_validate_research_item({"title": "t", "summary": "s", "url": "https://x.com", "source": "src", "category": "cat"})` (missing `share_note`) returns `None`.
- [ ] AC-32: `_validate_research_item({"title": "  ", "summary": "s", "url": "https://x.com", "source": "src", "category": "cat", "share_note": "n"})` (whitespace-only title) returns `None`.
- [ ] AC-33: `_parse_and_validate_items('{"items": [{...url A...}, {...url A again...}]}', ...)` (two candidates with the identical url) returns exactly 1 item — the second is dropped as an in-batch duplicate.
- [ ] AC-34: `_parse_and_validate_items` with a candidate whose url is in `blocklist_urls` returns a list excluding that candidate, and logs a warning.
- [ ] AC-35: `_parse_and_validate_items(None, "nimrod", set(), set())` returns `[]` with no exception.
- [ ] AC-36: A raw response with 8 well-formed candidate items, one of which fails `_apply_content_guardrails`, returns exactly 7 items.

### 2.7 Mock-mode item generators

**What to implement:**

```python
_MOCK_TITLES_BY_MEMBER = {
    "nimrod": ["מסלול הפלגה חדש ביוון", "טכניקת הרכבה להידרופוניקה ביתית", "עונת הליצ'י בישראל השנה"],
    "michal": ["רודה קפוארה מרגשת מסלוודור", "פרויקט אדריכלות ירוקה בעץ", "תרגול נשימה של 10 דקות"],
    "shaked": ["A new chapter drops for a rational-fiction serial",
               "A short essay on speculative gender in modern SF",
               "Redstone build ideas for a home Minecraft server"],
    "maayan": ["וידאו טרפז שמדהים את האינטרנט", "טרנד ריקוד חדש ברשת", "סיפור הצלחה של יזמית צעירה"],
    "tzlil": ["חידה מדהימה על אינסוף", "פרק Numberphile חדש על טופולוגיה", "עובדה מפתיעה על כלכלה עולמית"],
}


def _mock_items(member_id: str, target_item_count: int) -> list[dict]:
    """Deterministic mock items for --mock builds. Bypasses tt.research()'s
    generic (non-JSON) mock string entirely (§1 Assumption 6) so --mock
    builds still exercise the full item -> content_archive -> (future)
    newsletter pipeline end-to-end, the same way TokenTracker._mock_generate
    returns operation-specific canned text instead of a generic placeholder."""
    titles = _MOCK_TITLES_BY_MEMBER.get(
        member_id, [f"פריט לדוגמה {i+1}" for i in range(target_item_count)]
    )
    items = []
    for i, title in enumerate(titles[:target_item_count]):
        items.append({
            "title": title,
            "summary": f"[MOCK] תקציר לדוגמה עבור \"{title}\".",
            "url": f"https://example.com/mock/{member_id}/{i}",
            "source": "Mock Source",
            "category": "mock",
            "share_note": "[MOCK] פריט בדיקה — לא תוכן אמיתי.",
        })
    return items


def _mock_viewing_pick(label: str) -> dict:
    """Deterministic mock viewing pick for --mock screen_scout runs."""
    return {
        "title": f"[MOCK] {label} title",
        "service": "netflix",
        "summary": f"[MOCK] summary for {label}.",
        "content_rating": "PG",
        "hebrew_subtitles_verified": True,
        "availability_verified": True,
        "verification_source_url": "https://www.justwatch.com/il/mock",
        "availability_note": "[MOCK]",
        "share_note": f"[MOCK] share note for {label}.",
    }
```

**Acceptance criteria:**
- [ ] AC-37: `_mock_items("tzlil", 3)` returns exactly 3 dicts, each with all 6 required keys, each `url` unique.
- [ ] AC-38: `_mock_items("unknown_id", 3)` (member not in `_MOCK_TITLES_BY_MEMBER`) returns 3 dicts using the generic fallback titles — no `KeyError`.
- [ ] AC-39: Every dict returned by `_mock_items` passes `_validate_research_item` unchanged (i.e. mock items are themselves schema-valid, so mock mode exercises the exact same downstream persistence code path as real items).
- [ ] AC-40: `_mock_viewing_pick("family_pick")["service"] in ("netflix", "prime")` and both `*_verified` fields are `True`.

### 2.8 Low-level research-call wrapper

**What to implement:**

```python
def _call_research(tt: TokenTracker, module: str, operation: str,
                    system: str, user_prompt: str,
                    newsletter_date: str, max_tokens: int,
                    web_search_max_uses: int,
                    web_fetch_max_uses: int = DEFAULT_WEB_FETCH_MAX_USES_RESEARCH) -> Optional[str]:
    """Thin wrapper around TokenTracker.research(): returns the raw response
    text on success, or None on ANY exception (logged at ERROR, never
    raised). Deliberately catches bare Exception — see §1 Assumption 7:
    researcher.py sits one layer above token_tracker.research() and does
    not need to distinguish a RuntimeError (retries exhausted) from a
    ResearchLoopError (pause_turn cap breach) from an SDK-not-installed
    error; all three mean the same thing to a caller here: "no usable text
    came back this attempt." """
    try:
        return tt.research(
            module=module,
            operation=operation,
            prompt=user_prompt,
            system=system,
            max_tokens=max_tokens,
            newsletter_date=newsletter_date,
            web_search_max_uses=web_search_max_uses,
            web_fetch_max_uses=web_fetch_max_uses,
        )
    except Exception as e:
        logger.error(f"[researcher] {module}/{operation} research call failed: {e}")
        return None
```

**Acceptance criteria:**
- [ ] AC-41: With a mocked `tt.research` returning a string, `_call_research(...)` returns that exact string.
- [ ] AC-42: With a mocked `tt.research` raising `RuntimeError("boom")`, `_call_research(...)` returns `None` (does not raise) and logs an ERROR containing `"boom"`.
- [ ] AC-43: With a mocked `tt.research` raising a `ResearchLoopError`-like exception, `_call_research(...)` still returns `None`, not a re-raise (confirms the broad `except Exception`, not a narrower type).
- [ ] AC-44: `tt.research` is called with keyword arguments exactly `module`, `operation`, `prompt`, `system`, `max_tokens`, `newsletter_date`, `web_search_max_uses`, `web_fetch_max_uses` — verify via the mock's captured `call_args.kwargs` (no positional arguments used).

### 2.9 `research_member()` prompt templates + builder

**What to implement:**

1. The two-step prompt template — system half (parameterized by target item count, search budget, and output language; the "two steps, same call" structure and the three explicit critique tests are hard-coded, not parameterized, per REVIVAL_PLAN §3.5 Layer 4 verbatim):

```python
_RESEARCH_MEMBER_SYSTEM = """You are the content researcher for a private, weekly family newsletter (Hebrew name: בית ולד / "Beit Vald"). You are researching for ONE family member this turn. You have web_search and web_fetch tools.

WORKFLOW — do BOTH steps in this single turn:
STEP 1 - GATHER: use web_search (up to {max_web_searches} calls) to find roughly 8 real, current candidate items that could genuinely interest this person, based on the taste profile below. Search in Hebrew and/or English as appropriate. Prefer items published or updated in roughly the last 10 days; never invent a publish date you did not actually see.
STEP 2 - CRITIQUE: from your candidates, select exactly {target_item_count} that this person would genuinely love. For EACH candidate, explicitly apply these three tests before keeping it:
  (a) Would they send this to a friend, unprompted?
  (b) Is it fresh - roughly from the last 10 days, not old evergreen filler?
  (c) Does it SHOW something (a real video, a real project, a real result, a real story) rather than just REPORT news about a category?
Drop anything that fails more than one test. Prefer items that clear all three.

OUTPUT - return ONLY a single JSON object, no prose, no markdown code fence, shaped exactly as:
{{"items": [{{"title": "...", "summary": "...", "url": "...", "source": "...", "category": "...", "share_note": "..."}}, ...]}}
- Return exactly {target_item_count} objects in "items".
- "url" must be a real URL you actually found via search this turn - never invent one.
- "summary": 2-3 sentences, factual, in {language_label}.
- "share_note": one sentence, in {language_label}, explaining why THIS item earns its place for this specific person.
- "category": a short 1-3 word topic label, in {language_label}.
- All text fields in {language_label} - do not mix languages within one field.

HARD CONTENT RULES - apply to every item, no exceptions:
- No politics, no partisan content, no election coverage, ever.
- If an item touches "Death Gate Cycle" (Weis & Hickman) or "Avatar: The Last Airbender": describe only the general premise or setting - never reveal plot events, character fates, or endings. Treat as strictly spoiler-free.
- Never research, name, or reference the family member's own private business, medical, financial, legal, or relationship details - you are finding THIRD-PARTY content that matches their taste, never content about them personally.
- Never propose an item whose url is already listed in the DO-NOT-REPEAT list in the user message.
"""

_RESEARCH_MEMBER_USER = """FAMILY MEMBER: {display_name} ({member_id})

TASTE PROFILE (authoritative - this is who they are right now):
---
{taste_profile}
---

PREFERRED SOURCE HINTS (known-good starting points - not exhaustive, search beyond them too):
{source_hints}

FAMILY BOOKSHELF (use ONLY if a book is genuinely relevant to a current obsession above - do not force it):
{bookshelf_hints}

DO-NOT-REPEAT (already shown in the last {dedup_days} days - never propose any of these URLs again):
{blocklist}

Today's reference date: {newsletter_date}.

Now do STEP 1 (gather) and STEP 2 (critique) as instructed, and return the JSON object."""

_RESEARCH_MEMBER_RETRY_USER_SUFFIX = """

NOTE: this is a follow-up request. Your previous attempt returned {previous_count} usable item(s) (listed below only so you do not repeat them), but {missing_count} MORE, DIFFERENT item(s) are needed. Do not repeat anything listed here or in the DO-NOT-REPEAT list above:
{previous_urls}"""
```

2. The builder function:

```python
def _build_research_member_prompt(
    member: MemberProfile, family: FamilyConfig, taste_profile: str,
    blocklist_urls: set[str], target_item_count: int, max_web_searches: int,
    newsletter_date: str, *, retry_context: Optional[dict] = None,
) -> tuple[str, str]:
    """Builds (system, user) for one research_member() LLM call.
    retry_context, when given, must be a dict with keys previous_count (int),
    missing_count (int), and previous_urls (str, pre-formatted bullet list) -
    the caller (research_member, §2.10) is responsible for setting
    target_item_count to the MISSING count (not the original target) when
    retry_context is supplied, so the prompt asks for exactly what is
    needed."""
    language_label = "English" if _member_language(member) == "en" else "Hebrew"
    system = _RESEARCH_MEMBER_SYSTEM.format(
        max_web_searches=max_web_searches,
        target_item_count=target_item_count,
        language_label=language_label,
    )
    user = _RESEARCH_MEMBER_USER.format(
        display_name=member.nickname_newsletter or member.name,
        member_id=member.id,
        taste_profile=taste_profile,
        source_hints=_format_source_hints(member),
        bookshelf_hints=_format_bookshelf(family, member.id),
        dedup_days=DEFAULT_DEDUP_DAYS,
        blocklist=_format_blocklist(blocklist_urls),
        newsletter_date=newsletter_date,
    )
    if retry_context:
        user += _RESEARCH_MEMBER_RETRY_USER_SUFFIX.format(**retry_context)
    return system, user
```

**Acceptance criteria:**
- [ ] AC-45: `_build_research_member_prompt(...)` for Shaked (`language_preference="en"`) produces a system prompt containing `"in English"` and not containing the literal substring `"in Hebrew"`.
- [ ] AC-46: `_build_research_member_prompt(...)` for Tzlil produces a system prompt containing all three literal critique-test sentences (a)/(b)/(c) verbatim as written above.
- [ ] AC-47: The system prompt, formatted with `target_item_count=3`, contains the literal substring `"exactly 3"` (appearing twice — once in STEP 2's instruction, once in OUTPUT's instruction).
- [ ] AC-48: With `retry_context={"previous_count": 1, "missing_count": 2, "previous_urls": "- https://x.com"}`, the returned user prompt ends with the retry suffix containing `"1 usable item(s)"` and `"2 MORE"`.
- [ ] AC-49: Without `retry_context` (default `None`), the returned user prompt does NOT contain the substring `"follow-up request"`.
- [ ] AC-50: The user prompt contains the member's `nickname_newsletter` (e.g. `"יויו"` for `maayan`, never `"מעיין"`).

### 2.10 `research_member()` and `research_all_members()` — public entry points

**What to implement:**

```python
def research_member(
    tt: TokenTracker,
    db: Database,
    family: FamilyConfig,
    member_id: str,
    newsletter_date: str,
    *,
    profiles_dir: str = "profiles/",
    dedup_days: int = DEFAULT_DEDUP_DAYS,
    max_web_searches: int = DEFAULT_MAX_WEB_SEARCHES_RESEARCH,
    target_item_count: int = DEFAULT_TARGET_ITEM_COUNT,
    max_tokens: int = DEFAULT_RESEARCH_MAX_TOKENS,
) -> list[dict]:
    """THE per-member two-step researcher. Returns 0..target_item_count
    validated item dicts (title/summary/url/source/category/share_note).
    Never raises for content-shortfall reasons (§1 Assumption 7) - only
    MemberNotFound (bad member_id) or TasteProfileMissingError (missing
    profiles/<id>.md) propagate. Every returned item has ALREADY been
    persisted to content_archive (via db.archive_researched_item) before
    this function returns, so next week's dedup blocklist reflects it."""
    member = get_member_by_id(family, member_id)  # raises MemberNotFound
    taste_profile = _load_taste_profile(member_id, profiles_dir)  # raises TasteProfileMissingError

    if tt.mock:
        items = _mock_items(member_id, target_item_count)
    else:
        blocklist_urls = db.get_recent_content_urls(days=dedup_days)
        blocklist_hashes = db.get_recent_hashes(days=dedup_days)

        system, user = _build_research_member_prompt(
            member, family, taste_profile, blocklist_urls,
            target_item_count, max_web_searches, newsletter_date,
        )
        raw = _call_research(
            tt, "researcher", f"research_member_{member_id}", system, user,
            newsletter_date, max_tokens, max_web_searches,
        )
        items = _parse_and_validate_items(raw, member_id, blocklist_urls, blocklist_hashes) if raw else []

        if len(items) < target_item_count:
            missing = target_item_count - len(items)
            retry_context = {
                "previous_count": len(items),
                "missing_count": missing,
                "previous_urls": _format_blocklist({i["url"] for i in items}) if items else "(none)",
            }
            retry_blocklist = blocklist_urls | {i["url"] for i in items}
            retry_system, retry_user = _build_research_member_prompt(
                member, family, taste_profile, retry_blocklist,
                missing, max_web_searches, newsletter_date,
                retry_context=retry_context,
            )
            raw2 = _call_research(
                tt, "researcher", f"research_member_{member_id}_retry", retry_system, retry_user,
                newsletter_date, max_tokens, max_web_searches,
            )
            if raw2:
                more_items = _parse_and_validate_items(raw2, member_id, retry_blocklist, blocklist_hashes)
                items = items + more_items[:missing]

        if len(items) < target_item_count:
            logger.warning(
                f"[researcher] research_member({member_id}): only {len(items)}/{target_item_count} "
                f"valid items after 1 retry"
            )

    items = items[:target_item_count]
    for item in items:
        try:
            db.archive_researched_item(
                url=item["url"], title=item["title"], source_name=item["source"],
                raw_text=item["summary"], tags=[item["category"], f"member:{member_id}"],
                language=_member_language(member),
            )
        except Exception as e:
            logger.error(f"[researcher] failed to archive item for {member_id} ({item['url']}): {e}")

    return items


def research_all_members(
    tt: TokenTracker,
    db: Database,
    family: FamilyConfig,
    newsletter_date: str,
    **kwargs,
) -> dict:
    """Calls research_member() once per member in family.members, in the
    order they appear there. A single member's ResearcherError/MemberNotFound
    (missing profile file, bad id) is caught, logged, and recorded as an
    empty list - it never stops the other members' research or propagates
    to the caller. Returns {member_id: list[dict]}, always with exactly
    len(family.members) keys."""
    results = {}
    for member in family.members:
        try:
            results[member.id] = research_member(tt, db, family, member.id, newsletter_date, **kwargs)
        except (ResearcherError, MemberNotFound) as e:
            logger.error(
                f"[researcher] research_member({member.id}) raised "
                f"{type(e).__name__}: {e} - recording 0 items"
            )
            results[member.id] = []
    return results
```

**Acceptance criteria:**
- [ ] AC-51: With `tt.mock=True`, `research_member(tt, db, family, "tzlil", "2026-07-24")` returns exactly 3 items (from `_mock_items`), calls `tt.research` **zero** times, and calls `db.archive_researched_item` exactly 3 times.
- [ ] AC-52: With `tt.mock=False` and a mocked `tt.research` returning a well-formed JSON string with exactly 3 valid items, `research_member(...)` returns those 3 items, calls `tt.research` exactly once (no retry needed), and calls `db.archive_researched_item` exactly 3 times with `url`/`title`/`source_name` matching each item.
- [ ] AC-53: With a mocked `tt.research` returning only 1 valid item on the first call and 2 valid (different-url) items on the second call, `research_member(...)` calls `tt.research` exactly twice and returns 3 items total.
- [ ] AC-54: With a mocked `tt.research` returning 0 valid items on BOTH calls, `research_member(...)` calls `tt.research` exactly twice (not a third time), returns `[]`, and logs a warning — does not raise.
- [ ] AC-55: With a mocked `tt.research` raising an exception on every call, `research_member(...)` still returns `[]` (via `_call_research`'s catch, §2.8) rather than propagating the exception.
- [ ] AC-56: `research_member(tt, db, family, "not_a_real_member", "2026-07-24")` raises `MemberNotFound` — verified BEFORE any `tt.research` call is attempted (mock/spy shows zero calls).
- [ ] AC-57: If `profiles/tzlil.md` is (in a test fixture) absent, `research_member(...)` raises `TasteProfileMissingError` before any `tt.research` call.
- [ ] AC-58: `research_all_members(tt, db, family, "2026-07-24")` returns a dict with exactly 5 keys (`nimrod`, `michal`, `shaked`, `maayan`, `tzlil`) when `family` is loaded from the real `config/family.json`.
- [ ] AC-59: If `research_member` is monkeypatched to raise `TasteProfileMissingError` for `"shaked"` only, `research_all_members(...)` still returns non-empty/attempted results for the other 4 members (i.e. the loop does not `break`/`return` early), and `results["shaked"] == []`.
- [ ] AC-60: A failed `db.archive_researched_item` call (mocked to raise) for one item does not prevent the remaining items in the same `research_member()` call from being archived, and does not affect the function's return value (the item still appears in the returned list — persistence failure is logged, not surfaced as a dropped item).

### 2.11 Viewing-pick validation

**What to implement:**

```python
def _validate_viewing_pick(candidate, recent_titles: set[str]) -> Optional[dict]:
    """Validates one family_pick/personal_pick candidate dict. Returns a
    clean, normalized dict on success, or None if any required key is
    missing/wrong-typed, the title collides with recent_titles (case-
    insensitive), service is not exactly 'netflix'/'prime', either
    *_verified flag does not normalize to True via _as_bool (§2.5) - i.e.
    an ABSENT, unparseable, or explicitly False flag all fail closed the
    same way - the verification_source_url is not a valid http(s) URL, or
    the content_rating (if present) fails _rating_allowed. Never raises."""
    if not isinstance(candidate, dict):
        return None
    required = ("title", "service", "summary", "hebrew_subtitles_verified",
                "availability_verified", "verification_source_url", "share_note")
    for key in required:
        if key not in candidate:
            return None

    title = candidate["title"]
    if not isinstance(title, str) or not title.strip() or len(title) > 150:
        return None
    title = title.strip()
    if title.lower() in recent_titles:
        return None

    if candidate.get("service") not in ("netflix", "prime"):
        return None

    if _as_bool(candidate.get("hebrew_subtitles_verified")) is not True:
        return None
    if _as_bool(candidate.get("availability_verified")) is not True:
        return None

    source_url = candidate.get("verification_source_url")
    if not isinstance(source_url, str) or not _URL_RE.match(source_url.strip()):
        return None

    if not _rating_allowed(candidate.get("content_rating")):
        return None

    summary = candidate.get("summary")
    share_note = candidate.get("share_note")
    if not isinstance(summary, str) or not summary.strip():
        return None
    if not isinstance(share_note, str) or not share_note.strip():
        return None

    return {
        "title": title,
        "service": candidate["service"],
        "summary": summary.strip()[:800],
        "content_rating": candidate.get("content_rating"),
        "hebrew_subtitles_verified": True,
        "availability_verified": True,
        "verification_source_url": source_url.strip(),
        "availability_note": (candidate.get("availability_note") or "").strip()[:300],
        "share_note": share_note.strip()[:300],
    }
```

**Acceptance criteria:**
- [ ] AC-61: A fully well-formed candidate (all 7 required keys, `service="netflix"`, both `*_verified` flags `True`, valid `verification_source_url`) validates successfully and the returned dict's `hebrew_subtitles_verified`/`availability_verified` are exactly `True` (bool, not string).
- [ ] AC-62: A candidate with `hebrew_subtitles_verified: false` returns `None`.
- [ ] AC-63: A candidate with `hebrew_subtitles_verified` KEY ABSENT entirely returns `None` (fails the initial required-keys check, not merely the `_as_bool` check).
- [ ] AC-64: A candidate with `hebrew_subtitles_verified: "true"` (string, not bool) validates successfully (via `_as_bool`'s string-normalization, §2.5 AC-27), demonstrating the defensive-parsing path is actually exercised end-to-end here, not just in isolation.
- [ ] AC-65: A candidate with `service: "hulu"` returns `None`.
- [ ] AC-66: A candidate whose `title.lower()` exactly matches an entry in `recent_titles` returns `None`.
- [ ] AC-67: A candidate with `content_rating: "TV-MA"` returns `None` even if both verification flags are `True`.
- [ ] AC-68: A candidate with `verification_source_url: "not a url"` returns `None`.

### 2.12 Personal-pick rotation

**What to implement:**

```python
def _next_personal_pick_member(db: Database, family: FamilyConfig) -> str:
    """Determines who gets this week's screen_scout personal pick.
    Rotation order = family.members' natural order (family.json's
    top-level "members" array order: nimrod, michal, shaked, maayan,
    tzlil, as of this writing) - deliberately NOT hardcoded as a
    separate list, so adding/removing/reordering members in family.json
    is automatically reflected here with no code change. If no personal
    pick has ever been recorded, or the last one's for_whom is not a
    current member id (e.g. a member was removed), rotation restarts at
    index 0."""
    order = [m.id for m in family.members]
    if not order:
        raise ResearcherError("family.members is empty - cannot rotate personal pick")
    last = db.get_last_personal_pick()
    if not last or last["for_whom"] not in order:
        return order[0]
    idx = order.index(last["for_whom"])
    return order[(idx + 1) % len(order)]
```

**Acceptance criteria:**
- [ ] AC-69: With `db.get_last_personal_pick()` mocked to return `None`, `_next_personal_pick_member(db, family)` returns `family.members[0].id`.
- [ ] AC-70: With `db.get_last_personal_pick()` mocked to return `{"for_whom": "michal", ...}` and the real 5-member family, `_next_personal_pick_member(...)` returns `"shaked"` (the next id after `"michal"` in `[nimrod, michal, shaked, maayan, tzlil]`).
- [ ] AC-71: With `db.get_last_personal_pick()` mocked to return `{"for_whom": "tzlil", ...}` (the LAST member in rotation order), `_next_personal_pick_member(...)` wraps around and returns `"nimrod"`.
- [ ] AC-72: With `db.get_last_personal_pick()` mocked to return `{"for_whom": "someone_removed", ...}` (not in `order`), `_next_personal_pick_member(...)` returns `family.members[0].id` (safe restart, not a `ValueError` from `.index()`).

### 2.13 `screen_scout()` prompt templates + builders

**What to implement:**

1. Templates:

```python
_SCREEN_SCOUT_SYSTEM = """You are the "🍿 מה רואים השבוע" (What We're Watching This Week) screen-scout for a private Israeli family's weekly newsletter. You have web_search and web_fetch tools. You must select TWO viewing picks and, for EACH, verify - via real search THIS turn, never from memory - that it is:
  1. Actually available to stream RIGHT NOW on the specified service in ISRAEL (Netflix Israel or Prime Video Israel), and
  2. Actually has Hebrew subtitles available on that service.
An unavailable or un-subtitled recommendation breaks the family's trust - do not guess. If you cannot confirm BOTH facts via search this turn, do not propose that title; search for a different one instead.

PICK 1 - FAMILY PICK: one title the whole family (from age 13 up to the parents) can watch together. Must be age-appropriate for a 13-year-old - content_rating no higher than roughly "16+"/"TV-14" - never an 18+/R/TV-MA/NC-17 title. Prefer genres that fit this family: cross-generational fantasy/sci-fi, nature, adventure, warm dramedy.

PICK 2 - PERSONAL PICK: one title specifically for {personal_display_name}, based on their taste profile below. The same age ceiling applies (their household includes a 13-year-old).

OUTPUT - return ONLY a single JSON object, no prose, no markdown fence, shaped exactly as:
{{"family_pick": {{"title": "...", "service": "netflix"|"prime", "summary": "...", "content_rating": "...", "hebrew_subtitles_verified": true|false, "availability_verified": true|false, "verification_source_url": "...", "share_note": "..."}}, "personal_pick": {{"title": "...", "service": "netflix"|"prime", "summary": "...", "content_rating": "...", "hebrew_subtitles_verified": true|false, "availability_verified": true|false, "verification_source_url": "...", "share_note": "..."}}}}
- "service": exactly the lowercase string "netflix" or "prime".
- "hebrew_subtitles_verified" / "availability_verified": JSON boolean literals (true/false), true ONLY if actually confirmed via search this turn.
- "verification_source_url": the URL of the page (e.g. JustWatch, or the service's own title page) where you confirmed availability and subtitles.
- "summary": 2-3 sentences, factual, in Hebrew.
- "share_note": one sentence in Hebrew on why this pick fits this week.
- Never propose a title listed in the DO-NOT-REPEAT list in the user message.
"""

_SCREEN_SCOUT_USER = """PERSONAL PICK TARGET: {personal_display_name} ({personal_member_id})

TASTE PROFILE for the personal pick:
---
{personal_taste_profile}
---

DO-NOT-REPEAT (already recommended in the last {dedup_days} days):
{blocklist}

Today's reference date: {newsletter_date}.

Find and verify both picks now, and return the JSON object."""

_SCREEN_SCOUT_RETRY_SYSTEM = """You are the "🍿 מה רואים השבוע" screen-scout for a private Israeli family's weekly newsletter, doing a FOLLOW-UP search. Your previous candidate for the "{slot_label}" pick ("{previous_title}") could not be confirmed (reason: {reason}). Find ONE different title and verify, via real search this turn, that it is:
  1. Actually available to stream RIGHT NOW on Netflix Israel or Prime Video Israel, and
  2. Actually has Hebrew subtitles on that service.
{slot_instructions}

OUTPUT - return ONLY a single JSON object, no prose, shaped exactly as:
{{"pick": {{"title": "...", "service": "netflix"|"prime", "summary": "...", "content_rating": "...", "hebrew_subtitles_verified": true|false, "availability_verified": true|false, "verification_source_url": "...", "share_note": "..."}}}}
(Same field rules as before: service is "netflix" or "prime" lowercase; booleans are true only if actually confirmed this turn; summary/share_note in Hebrew.)

DO-NOT-REPEAT (already recommended in the last {dedup_days} days, plus your own rejected candidate "{previous_title}"):
{blocklist}
"""
```

2. Helper + builders:

```python
def _slot_instructions(slot: str, personal_member: MemberProfile, personal_taste: str) -> str:
    if slot == "family_pick":
        return ("This is the FAMILY PICK: must suit the whole family (age 13 up to parents), "
                "content_rating no higher than roughly \"16+\"/\"TV-14\" (never 18+/R/TV-MA/NC-17). "
                "Prefer cross-generational fantasy/sci-fi, nature, adventure, or warm dramedy.")
    display = personal_member.nickname_newsletter or personal_member.name
    return (f"This is the PERSONAL PICK for {display}. Taste profile:\n---\n{personal_taste}\n---\n"
            "The same age ceiling applies (household includes a 13-year-old).")


def _build_screen_scout_prompt(
    family: FamilyConfig, personal_member: MemberProfile, personal_taste: str,
    recent_titles: set[str], newsletter_date: str,
) -> tuple[str, str]:
    display = personal_member.nickname_newsletter or personal_member.name
    system = _SCREEN_SCOUT_SYSTEM.format(personal_display_name=display)
    user = _SCREEN_SCOUT_USER.format(
        personal_display_name=display,
        personal_member_id=personal_member.id,
        personal_taste_profile=personal_taste,
        dedup_days=DEFAULT_DEDUP_DAYS,
        blocklist=_format_blocklist(recent_titles),
        newsletter_date=newsletter_date,
    )
    return system, user


def _build_screen_scout_retry_prompt(
    slot: str, previous_title: str, reason: str,
    personal_member: MemberProfile, personal_taste: str,
    recent_titles: set[str],
) -> tuple[str, str]:
    slot_label = "family_pick" if slot == "family_pick" else "personal_pick"
    system = _SCREEN_SCOUT_RETRY_SYSTEM.format(
        slot_label=slot_label,
        previous_title=previous_title,
        reason=reason,
        slot_instructions=_slot_instructions(slot, personal_member, personal_taste),
    )
    user = _SCREEN_SCOUT_USER.format(
        personal_display_name=personal_member.nickname_newsletter or personal_member.name,
        personal_member_id=personal_member.id,
        personal_taste_profile=personal_taste,
        dedup_days=DEFAULT_DEDUP_DAYS,
        blocklist=_format_blocklist(recent_titles | {previous_title.lower()}),
        newsletter_date="(see above)",
    )
    return system, user
```

**Acceptance criteria:**
- [ ] AC-73: `_build_screen_scout_prompt(...)`'s system prompt contains the member's `nickname_newsletter` and the literal substring `"content_rating no higher than roughly"`.
- [ ] AC-74: `_slot_instructions("family_pick", ...)` returns a string containing `"FAMILY PICK"` and does NOT contain the personal member's taste profile text.
- [ ] AC-75: `_slot_instructions("personal_pick", member, "TASTE TEXT HERE")` returns a string containing the literal substring `"TASTE TEXT HERE"`.
- [ ] AC-76: `_build_screen_scout_retry_prompt("family_pick", "Some Show", "rating too high", ...)` produces a system prompt containing `"Some Show"` and `"rating too high"`, and a user-prompt blocklist that includes `"some show"` (lowercased) even if it was not already in `recent_titles`.

### 2.14 `screen_scout()` — public entry point

**What to implement:**

```python
def screen_scout(
    tt: TokenTracker,
    db: Database,
    family: FamilyConfig,
    newsletter_date: str,
    *,
    profiles_dir: str = "profiles/",
    dedup_days: int = DEFAULT_DEDUP_DAYS,
    max_web_searches: int = DEFAULT_MAX_WEB_SEARCHES_SCOUT,
    max_tokens: int = DEFAULT_SCOUT_MAX_TOKENS,
) -> dict:
    """The weekly "🍿 מה רואים השבוע" scout. Returns
    {"family_pick": dict|None, "personal_pick": dict|None,
     "personal_pick_member_id": str}. A pick is None if it could not be
    validated after one retry (§1 Assumption 7 - never raises for this).
    Every non-None pick has ALREADY been persisted to the watchlist table
    (status='recommended') before this function returns."""
    personal_member_id = _next_personal_pick_member(db, family)
    personal_member = get_member_by_id(family, personal_member_id)
    personal_taste = _load_taste_profile(personal_member_id, profiles_dir)

    result = {"family_pick": None, "personal_pick": None,
              "personal_pick_member_id": personal_member_id}

    if tt.mock:
        result["family_pick"] = _mock_viewing_pick("family_pick")
        result["personal_pick"] = _mock_viewing_pick("personal_pick")
    else:
        recent_titles = db.get_recent_watchlist_titles(days=dedup_days)
        system, user = _build_screen_scout_prompt(
            family, personal_member, personal_taste, recent_titles, newsletter_date,
        )
        raw = _call_research(
            tt, "researcher", "screen_scout", system, user, newsletter_date,
            max_tokens, max_web_searches, web_fetch_max_uses=DEFAULT_WEB_FETCH_MAX_USES_SCOUT,
        )
        parsed = _parse_json_response(raw) if raw else None

        for slot in ("family_pick", "personal_pick"):
            candidate = parsed.get(slot) if isinstance(parsed, dict) else None
            pick = _validate_viewing_pick(candidate, recent_titles) if candidate else None

            if pick is None:
                previous_title = (
                    candidate.get("title") if isinstance(candidate, dict) and isinstance(candidate.get("title"), str)
                    else "(no candidate returned)"
                )
                reason = "missing or invalid fields" if candidate else "no candidate returned in first attempt"
                logger.warning(f"[researcher] screen_scout: {slot} failed validation ({reason}), retrying once")
                retry_system, retry_user = _build_screen_scout_retry_prompt(
                    slot, previous_title, reason, personal_member, personal_taste, recent_titles,
                )
                raw2 = _call_research(
                    tt, "researcher", f"screen_scout_{slot}_retry", retry_system, retry_user,
                    newsletter_date, max_tokens, max_web_searches,
                    web_fetch_max_uses=DEFAULT_WEB_FETCH_MAX_USES_SCOUT,
                )
                parsed2 = _parse_json_response(raw2) if raw2 else None
                candidate2 = parsed2.get("pick") if isinstance(parsed2, dict) else None
                pick = _validate_viewing_pick(candidate2, recent_titles) if candidate2 else None
                if pick is None:
                    logger.warning(f"[researcher] screen_scout: {slot} could not be verified after 1 retry - leaving unset")

            result[slot] = pick

    pick_type_map = {"family_pick": "family", "personal_pick": "personal"}
    for_whom_map = {"family_pick": "family", "personal_pick": personal_member_id}
    for slot in ("family_pick", "personal_pick"):
        pick = result[slot]
        if pick:
            try:
                db.insert_watchlist_pick(
                    title=pick["title"], service=pick["service"],
                    for_whom=for_whom_map[slot], pick_type=pick_type_map[slot],
                    recommended_date=newsletter_date,
                    hebrew_subtitles=pick["hebrew_subtitles_verified"],
                    availability_note=pick.get("availability_note", ""),
                    source_url=pick["verification_source_url"],
                )
            except Exception as e:
                logger.error(f"[researcher] failed to insert watchlist pick for {slot}: {e}")

    return result
```

**Acceptance criteria:**
- [ ] AC-77: With `tt.mock=True`, `screen_scout(...)` returns non-`None` `family_pick`/`personal_pick`, calls `tt.research` zero times, and calls `db.insert_watchlist_pick` exactly twice.
- [ ] AC-78: With `tt.mock=False` and a mocked `tt.research` returning a fully valid `{"family_pick": {...}, "personal_pick": {...}}` on the first call, `screen_scout(...)` calls `tt.research` exactly once, both picks are non-`None`, and `db.insert_watchlist_pick` is called exactly twice — once with `pick_type="family"`/`for_whom="family"`, once with `pick_type="personal"`/`for_whom=<rotated member id>`.
- [ ] AC-79: With a mocked `tt.research` whose first call returns a valid `family_pick` but an INVALID `personal_pick` (e.g. `availability_verified: false`), and whose second call (the retry) returns a valid `{"pick": {...}}`, `screen_scout(...)` calls `tt.research` exactly twice total, and both `result["family_pick"]` and `result["personal_pick"]` end up non-`None`.
- [ ] AC-80: If BOTH the first attempt and the retry fail to produce a valid `personal_pick`, `result["personal_pick"] is None`, `result["family_pick"]` is unaffected (still validated independently), and `db.insert_watchlist_pick` is called only once (for the family pick).
- [ ] AC-81: `result["personal_pick_member_id"]` always equals the value `_next_personal_pick_member(db, family)` would have returned, regardless of whether the personal pick itself succeeded or ended up `None`.
- [ ] AC-82: A failed `db.insert_watchlist_pick` call (mocked to raise) for one pick does not prevent the other pick's insert from being attempted, and does not change `screen_scout`'s return value (the failed-to-persist pick is still returned as non-`None` — persistence failure is logged, not surfaced as a validation failure).

### 2.15 Database layer additions (`src/db.py`)

**What to implement:** add the `watchlist` table to `_init_schema()`'s `executescript(...)` call (append after the existing `scan_log` table definition, before the `CREATE INDEX` statements — or add new indexes alongside the existing ones; exact placement within the script is not order-sensitive since `CREATE TABLE IF NOT EXISTS` statements have no cross-table dependencies here), plus five new methods on `Database`.

1. DDL (add to the `executescript` string):

```sql
CREATE TABLE IF NOT EXISTS watchlist (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT NOT NULL,
    service             TEXT NOT NULL CHECK(service IN ('netflix','prime')),
    for_whom            TEXT NOT NULL,
    pick_type           TEXT NOT NULL CHECK(pick_type IN ('family','personal')),
    recommended_date    TEXT NOT NULL,
    hebrew_subtitles    INTEGER NOT NULL DEFAULT 0,
    availability_note   TEXT,
    source_url          TEXT,
    status              TEXT NOT NULL DEFAULT 'recommended'
                        CHECK(status IN ('recommended','watched','reaction')),
    reaction_text       TEXT,
    reaction_rating     TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_watchlist_date ON watchlist(recommended_date);
CREATE INDEX IF NOT EXISTS idx_watchlist_status ON watchlist(status);
```

   Notes on the schema (for the builder, so no field is "corrected" away by accident): `for_whom` holds either a real `member_id` (personal picks) or the literal string `'family'` (family picks) — deliberately `TEXT NOT NULL` with **no** `CHECK` restricting it to known member ids, matching the existing, identical convention already used by `newsletter_items.member_id` elsewhere in this same file (application-code validates membership, not SQL). `pick_type` is a small, deliberate redundancy with `for_whom == 'family'` — it exists so query code never has to string-compare against the `'family'` sentinel to tell the two kinds of row apart. `status`/`reaction_text`/`reaction_rating` exist now (per the task's exact column ask) but are only ever written by this WP as `status='recommended'` with the two reaction fields left `NULL` — the `watched`/`reaction` transitions are Phase B (§6), not built here.

2. New `Database` methods (add in a new `# ─── Watchlist / Research Dedup ─────` section, after the existing `# ─── Scan Log ───` section and before `# ─── Utility ───`):

```python
    # ─── Content Archive (dedup + researcher-item persistence) ─

    def get_recent_content_urls(self, days: int = 45) -> set[str]:
        """URLs archived in the last N days — the URL half of the
        research_member() dedup blocklist (§1 Assumption 3). Mirrors the
        existing get_recent_hashes() query shape exactly, just selecting a
        different column."""
        rows = self.conn.execute(
            "SELECT url FROM content_archive WHERE fetched_at > date('now', ?)",
            (f'-{days} days',)
        ).fetchall()
        return {r['url'] for r in rows}

    def archive_researched_item(self, *, url: str, title: str, source_name: str,
                                 raw_text: str, tags: list[str], language: str,
                                 image_url: Optional[str] = None) -> str:
        """Inserts a researcher-produced item into content_archive
        (source_type='web', is_submission=0, source_trust=0.7 default,
        published_at=NULL — the LLM's claimed publish date is not
        independently verified, so it is deliberately not stored as a
        trusted field here). Uses the SAME id/content_hash derivation as
        the legacy NCI factory (sha256(url)[:16] / sha256(title+raw_text)
        [:16]) but does NOT depend on models.NCI (slated for removal in a
        future BACKFILL WP per REVIVAL_PLAN §3's keep/replace table).
        INSERT OR IGNORE semantics: if url already exists (UNIQUE
        constraint), the existing row is left untouched; the id returned is
        always the correct id for that url either way (freshly-inserted or
        pre-existing) since the id is a pure function of the url."""
        item_id = hashlib.sha256(url.encode()).hexdigest()[:16]
        content_hash = hashlib.sha256((title + raw_text).encode()).hexdigest()[:16]
        fetched_at = datetime.now(timezone.utc).isoformat()
        self.conn.execute("""
            INSERT OR IGNORE INTO content_archive
            (id, url, title, source_name, source_type, source_url, source_trust,
             published_at, fetched_at, language, raw_text, tags, image_url,
             content_hash, is_submission, submitted_by)
            VALUES (?, ?, ?, ?, 'web', ?, 0.7, NULL, ?, ?, ?, ?, ?, ?, 0, NULL)
        """, (item_id, url, title, source_name, url, fetched_at, language,
              raw_text, json.dumps(tags, ensure_ascii=False), image_url, content_hash))
        self.conn.commit()
        return item_id

    # ─── Watchlist ────────────────────────────────────────────

    def get_recent_watchlist_titles(self, days: int = 45) -> set[str]:
        """Lower-cased titles recommended in the last N days — the
        screen_scout() dedup blocklist."""
        rows = self.conn.execute(
            "SELECT title FROM watchlist WHERE recommended_date > date('now', ?)",
            (f'-{days} days',)
        ).fetchall()
        return {r['title'].strip().lower() for r in rows}

    def get_last_personal_pick(self) -> Optional[dict]:
        """Most recent pick_type='personal' row, or None if none exists yet
        (first-ever run). Used by _next_personal_pick_member() (§2.12) for
        rotation."""
        row = self.conn.execute(
            "SELECT * FROM watchlist WHERE pick_type = 'personal' "
            "ORDER BY recommended_date DESC, id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def insert_watchlist_pick(self, *, title: str, service: str, for_whom: str,
                               pick_type: str, recommended_date: str,
                               hebrew_subtitles: bool, availability_note: str,
                               source_url: str) -> int:
        """Inserts one watchlist row with status='recommended'. Returns the
        new row's id (sqlite3 lastrowid)."""
        cur = self.conn.execute("""
            INSERT INTO watchlist
            (title, service, for_whom, pick_type, recommended_date,
             hebrew_subtitles, availability_note, source_url, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'recommended')
        """, (title, service, for_whom, pick_type, recommended_date,
              int(hebrew_subtitles), availability_note, source_url))
        self.conn.commit()
        return cur.lastrowid
```

   `datetime`/`timezone` are already imported at the top of `db.py` (`from datetime import datetime`) — add `timezone` to that existing import line (`from datetime import datetime, timezone`). `json` and `hashlib` — `json` is already imported at the top of `db.py`; add `import hashlib` as a new top-level import.

**Acceptance criteria:**
- [ ] AC-83: After `_init_schema()` runs on a fresh DB, `PRAGMA table_info(watchlist)` lists exactly the 13 columns shown in the DDL, in that order.
- [ ] AC-84: Inserting a row with `service='hulu'` raises `sqlite3.IntegrityError` (the `CHECK` constraint fires).
- [ ] AC-85: Inserting a row with `pick_type='family'` and `status` omitted defaults to `status='recommended'`.
- [ ] AC-86: `db.get_recent_content_urls(days=45)` returns a `set[str]`; after `db.archive_researched_item(url="https://x.com", title="t", source_name="s", raw_text="r", tags=["cat"], language="he")`, that exact URL appears in `db.get_recent_content_urls(days=45)`.
- [ ] AC-87: Calling `db.archive_researched_item(url="https://x.com", ...)` TWICE with the same `url` (different `title`) does not raise (`INSERT OR IGNORE`), and `content_archive` contains exactly one row for that URL (the first call's data, unchanged by the second).
- [ ] AC-88: `db.get_recent_watchlist_titles(days=45)` reflects titles inserted via `db.insert_watchlist_pick(...)`, lower-cased.
- [ ] AC-89: `db.get_last_personal_pick()` on an empty `watchlist` table returns `None`. After inserting 2 personal-pick rows on different `recommended_date`s, it returns the one with the LATER `recommended_date`.
- [ ] AC-90: `db.insert_watchlist_pick(...)` returns an `int` matching the inserted row's `id` (verified by re-querying `watchlist` for that id).

## 3. Data model changes

**New table** (full DDL — see §2.15 for rationale/notes):

```sql
CREATE TABLE IF NOT EXISTS watchlist (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT NOT NULL,
    service             TEXT NOT NULL CHECK(service IN ('netflix','prime')),
    for_whom            TEXT NOT NULL,
    pick_type           TEXT NOT NULL CHECK(pick_type IN ('family','personal')),
    recommended_date    TEXT NOT NULL,
    hebrew_subtitles    INTEGER NOT NULL DEFAULT 0,
    availability_note   TEXT,
    source_url          TEXT,
    status              TEXT NOT NULL DEFAULT 'recommended'
                        CHECK(status IN ('recommended','watched','reaction')),
    reaction_text       TEXT,
    reaction_rating     TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_watchlist_date ON watchlist(recommended_date);
CREATE INDEX IF NOT EXISTS idx_watchlist_status ON watchlist(status);
```

**Existing table reused, unchanged:** `content_archive` (no column added, no column removed, no `CHECK` touched). `researcher.py` writes to it via a new method, `archive_researched_item()`, that does not depend on `models.NCI`.

**New `Database` methods** (full code in §2.15):

| Method | Returns | Purpose |
|---|---|---|
| `get_recent_content_urls(days=45)` | `set[str]` | URL half of `research_member()`'s dedup blocklist |
| `archive_researched_item(url, title, source_name, raw_text, tags, language, image_url=None)` | `str` (id) | Persists an accepted research item into `content_archive` |
| `get_recent_watchlist_titles(days=45)` | `set[str]` | `screen_scout()`'s dedup blocklist |
| `get_last_personal_pick()` | `Optional[dict]` | Feeds `_next_personal_pick_member()`'s rotation |
| `insert_watchlist_pick(title, service, for_whom, pick_type, recommended_date, hebrew_subtitles, availability_note, source_url)` | `int` (row id) | Persists an accepted viewing pick, `status='recommended'` |

**`get_recent_hashes(days=30)`** (existing method, unchanged) — reused by `research_member()` with an explicit `days=45` call-site argument; no code change to the method itself.

**`models.py` / `m1_profiles.py`:** `MemberProfile` gains `media_sources: list[dict] = field(default_factory=list)`; `load_profiles()` populates it from `family.json`'s existing per-member `media_sources` key. Full diff in §2.0.

## 4. API contract changes

No HTTP endpoints exist in this project. The relevant contract is `researcher.py`'s public Python surface:

| Symbol | Kind | Signature | Notes |
|---|---|---|---|
| `research_member` | function | `research_member(tt, db, family, member_id, newsletter_date, *, profiles_dir="profiles/", dedup_days=45, max_web_searches=8, target_item_count=3, max_tokens=4096) -> list[dict]` | Per-member two-step research. See §2.10. |
| `research_all_members` | function | `research_all_members(tt, db, family, newsletter_date, **kwargs) -> dict` | Loops `research_member()` over all of `family.members`; never raises. See §2.10. |
| `screen_scout` | function | `screen_scout(tt, db, family, newsletter_date, *, profiles_dir="profiles/", dedup_days=45, max_web_searches=3, max_tokens=2048) -> dict` | Weekly viewing picks. See §2.14. |
| `ResearcherError` | exception | `class ResearcherError(Exception)` | Base class. |
| `TasteProfileMissingError` | exception | `class TasteProfileMissingError(ResearcherError)` | Missing/empty `profiles/<id>.md`. |

`research_member()`'s returned item dict shape:

| Key | Type | Notes |
|---|---|---|
| `title` | `str` | ≤150 chars (truncated if longer) |
| `summary` | `str` | ≤800 chars |
| `url` | `str` | matches `^https?://\S+$` |
| `source` | `str` | ≤80 chars |
| `category` | `str` | ≤40 chars |
| `share_note` | `str` | ≤300 chars |

`screen_scout()`'s returned dict shape: `{"family_pick": <pick|None>, "personal_pick": <pick|None>, "personal_pick_member_id": str}`, where `<pick>` is:

| Key | Type | Notes |
|---|---|---|
| `title` | `str` | ≤150 chars |
| `service` | `str` | exactly `"netflix"` or `"prime"` |
| `summary` | `str` | ≤800 chars |
| `content_rating` | `Optional[str]` | as self-reported; may be `None` |
| `hebrew_subtitles_verified` | `bool` | always `True` in a returned (non-`None`) pick |
| `availability_verified` | `bool` | always `True` in a returned (non-`None`) pick |
| `verification_source_url` | `str` | matches `^https?://\S+$` |
| `availability_note` | `str` | ≤300 chars, may be `""` |
| `share_note` | `str` | ≤300 chars |

Callers depending on this WP: `editor.py` (WP004, not yet built) consumes `research_member()`'s/`research_all_members()`'s returned items to write final headlines/summaries/positions into `newsletter_items`. `orchestrator.py` (rewiring, separate WP) is expected to call `research_all_members()` and `screen_scout()` once each per weekly build, passing the same `tt`/`db` instances it already constructs (`tt = TokenTracker(db, mock=args.mock)`, existing pattern in `cmd_weekly_build`).

## 5. Error handling requirements

| Error case | Expected behavior |
|---|---|
| `member_id` not found in `family.members` | `MemberNotFound` (existing exception, `models.py`) raised immediately by `get_member_by_id()`, before any `tt.research` call (AC-56). `research_all_members()` catches it per-member and records `[]` (AC-59). |
| `profiles/<member_id>.md` missing or empty | `TasteProfileMissingError` raised immediately, before any `tt.research` call (AC-57). `research_all_members()` catches it per-member and records `[]` (AC-59). |
| `tt.research()` raises any exception (rate limit exhausted, `ResearchLoopError`, SDK unavailable, network error) | Caught broadly inside `_call_research` (§2.8), logged at ERROR, returns `None` — never propagates. Triggers this module's own single retry (below), not `tt.research()`'s internal retry (which has already run its course by the time it raises). |
| `tt.research()` succeeds but the response is not parseable JSON, or lacks the expected top-level key(s) | `_parse_json_response`/`_parse_and_validate_items` return `None`/`[]` — treated identically to "0 valid items", triggering the same single retry. |
| Fewer than `target_item_count` valid items after the first `research_member()` attempt | Exactly ONE reinforced retry, asking only for the missing count, explicitly excluding URLs already accepted this run (§2.10). Not a driver-style fallback chain — always the same call shape, once. |
| Fewer than `target_item_count` valid items after the retry too | Returns whatever valid items exist (0, 1, or 2) — logs a WARNING (not ERROR: usually content scarcity, not a bug). Never raises. The overall-edition "every member ≥1 item" hard rule (LOD200 §2) is the orchestrator's/editor's concern to enforce with a canned fallback, out of scope here (§6). |
| A candidate item fails `_validate_research_item` (bad shape, malformed URL, empty required field) | Silently dropped (logged at WARNING with the reason) — counts toward the "fewer than target" shortfall above, does not raise. |
| A candidate item's `url`/content-hash matches the dedup blocklist, or duplicates another item in the same batch | Dropped, logged (AC-34, AC-33) — same shortfall handling as above. |
| A candidate item fails `_apply_content_guardrails` (self-name or political-keyword match) | Dropped, logged with the specific reason string — same shortfall handling as above. |
| `screen_scout()`: a pick candidate fails `_validate_viewing_pick` (missing key, unverified availability/subtitles, disallowed rating, bad URL, title collision) | Exactly ONE retry for that slot only, using the lighter single-pick `{"pick": {...}}` schema (§2.13). If the retry also fails validation, that slot's result is `None` — logged at WARNING, never raised. The other slot is validated fully independently and is unaffected. |
| `db.archive_researched_item()` / `db.insert_watchlist_pick()` raises (DB locked, disk full, etc.) | Caught per-item/per-pick, logged at ERROR, does NOT remove the item from `research_member()`'s/`screen_scout()`'s return value — the caller still receives the (unpersisted) item; only the future dedup-blocklist benefit is lost for that one item (AC-60, AC-82). |
| `family.members` is empty (misconfigured `family.json`) | `_next_personal_pick_member()` raises `ResearcherError` explicitly (not a silent `IndexError`) — this is a deployment bug, not a content issue, consistent with the `TasteProfileMissingError`/`MemberNotFound` treatment. |
| An LLM response's `hebrew_subtitles_verified`/`availability_verified` field is present but not a recognizable boolean (e.g. `"yes"`, `1`, `null`) | `_as_bool()` returns `None` for anything other than a real bool or the exact strings `"true"`/`"false"` — treated as **not confirmed** (fails closed), never coerced to `True` (AC-27, AC-63/64). |

## 6. Out of scope (explicit)

- **Editorial writing** — headline/summary polish, discovery-bridge text, opener/closer, the "🍽️ שולחן שישי / Family Table" section, and the "👨‍👩‍👧 מהמשפחה המורחבת / Extended Family" section — **WP004** (`editor.py`). `research_member()`'s `share_note` field is the editorial *hook* `editor.py` builds from; it is not itself final newsletter copy.
- **Rendering** — HTML template changes, teaser image generation, character/mascot art selection (the `SVG_MODULE_SPEC.md` topic→scene→character lookup table) — **WP007**/**WP005**. `research_member()`'s `category` field is a short free-text hint only; it is NOT matched against any controlled vocabulary in this WP.
- **Weather and Hebrew-date assembly** — deterministic, no-LLM-call assembly (Open-Meteo, Hebrew calendar) — the orchestrator (a separate, not-yet-built rewiring WP), per the task brief's explicit framing.
- **Writing to `newsletters` / `newsletter_items`** — edition-assembly with final headline/summary/position/score is the orchestrator's/editor's job; this WP writes only to `content_archive` and `watchlist`.
- **`llm.py` changes** — `researcher.py` never imports from or calls `llm.py`; WP001's `tools` support remains `NotImplementedError` (§1 Assumption 2). Wiring `research()`'s tool-use through `llm.py`'s driver abstraction, if ever done, is a separate future WP.
- **`config/settings.json` edits** — this WP's tunables (`dedup_days`, `max_web_searches`, `target_item_count`, `max_tokens`, …) are plain Python keyword-argument defaults (§2.1), not settings-file-sourced, consistent with WP001's identical choice not to touch `settings.json`. A future orchestrator-wiring WP may thread `settings.ai.*` values into these calls.
- **Phase B**: reply/reaction ingestion, `watchlist.status` transitions to `'watched'`/`'reaction'`, the monthly profile-editor that proposes `profiles/*.md` diffs — all explicitly deferred per LOD200 §7. This WP only ever writes `status='recommended'`.
- **Independent re-verification of the LLM's self-reported availability/Hebrew-subtitle claims** — e.g., `researcher.py` itself re-fetching `verification_source_url` to double-check. v1 trusts the grounded self-report from the SAME tool-enabled turn that performed the search (a materially stronger guarantee than an ungrounded claim, but still not independently re-verified by this module's own code). A Phase C hardening pass could add that.
- **WAHA / WhatsApp delivery, FTP publishing** — WP003(server)/OPS and `publisher.py`, unrelated layers.
- **Any change to `token_tracker.py` beyond what WP002 already specifies** — this WP calls `tt.research()` exactly as WP002 defines it; no new keyword arguments or behavior are requested of `token_tracker.py`.
- **A CLI entry point for `researcher.py`** — not requested; the orchestrator-wiring WP is expected to import and call `research_all_members()`/`screen_scout()` directly, matching the existing `cmd_weekly_build` pattern (`tt = TokenTracker(db, mock=args.mock)` already built once there).

## 7. Test requirements

- **Unit** (no real API calls, no real network — mock `TokenTracker.research`, `Database`, and the filesystem where needed): every AC in §2.0–§2.15 above. Priority/highest-risk targets: the single-retry mechanics for both `research_member()` (AC-52–AC-55) and `screen_scout()`'s per-slot retry (AC-78–AC-80), the content-guardrail keyword checks (AC-23–AC-26), the `_as_bool` fail-closed behavior feeding into `_validate_viewing_pick` (AC-62–AC-64), the personal-pick rotation wraparound (AC-69–AC-72), and the mock-mode bypass never calling `tt.research` (AC-51, AC-77). Illustrative skeletons (pytest + pytest-mock, matching WP001/WP002's established convention):

```python
def test_research_member_mock_mode_never_calls_research(mocker):
    from src import researcher
    tt = mocker.Mock(mock=True)
    db = mocker.Mock()
    family = mocker.Mock(members=[mocker.Mock(id="tzlil", language_preference="he",
                                               nickname_newsletter="צליל", name="צליל",
                                               media_sources=[])])
    mocker.patch("src.m1_profiles.get_member_by_id", return_value=family.members[0])
    mocker.patch.object(researcher, "_load_taste_profile", return_value="some taste profile")

    items = researcher.research_member(tt, db, family, "tzlil", "2026-07-24")

    assert len(items) == 3
    tt.research.assert_not_called()
    assert db.archive_researched_item.call_count == 3


def test_research_member_retries_once_then_gives_up(mocker):
    from src import researcher
    tt = mocker.Mock(mock=False)
    db = mocker.Mock(get_recent_content_urls=mocker.Mock(return_value=set()),
                      get_recent_hashes=mocker.Mock(return_value=set()))
    member = mocker.Mock(id="tzlil", language_preference="he", nickname_newsletter="צליל",
                          name="צליל", media_sources=[])
    family = mocker.Mock(members=[member], shared_interests={})
    mocker.patch("src.m1_profiles.get_member_by_id", return_value=member)
    mocker.patch.object(researcher, "_load_taste_profile", return_value="taste")
    tt.research.side_effect = ['{"items": []}', '{"items": []}']

    items = researcher.research_member(tt, db, family, "tzlil", "2026-07-24")

    assert items == []
    assert tt.research.call_count == 2


def test_next_personal_pick_wraps_around(mocker):
    from src import researcher
    db = mocker.Mock()
    db.get_last_personal_pick.return_value = {"for_whom": "tzlil"}
    family = mocker.Mock(members=[mocker.Mock(id=i) for i in
                                   ["nimrod", "michal", "shaked", "maayan", "tzlil"]])
    assert researcher._next_personal_pick_member(db, family) == "nimrod"
```

- **Integration** (real API, real search cost, gated — do not run in default CI given LOD200 §6's `$2.50/wk` cost cap): one live `research_member()` call for a single member (e.g. `tzlil`) against a real `.env` `ANTHROPIC_API_KEY` and a scratch/temp SQLite DB, behind an explicit opt-in (e.g. `RUN_LIVE_RESEARCH_TESTS=1`), asserting: exactly ≤3 items returned, each passes `_validate_research_item` unchanged, and `content_archive` gained the corresponding rows. One live `screen_scout()` call, same gating, asserting both picks (if non-`None`) have `hebrew_subtitles_verified is True` and `availability_verified is True`, and that `watchlist` gained the corresponding rows.
- **Cross-engine validation** (required at L-GATE_VALIDATE per Iron Rule #1 — the validator engine must differ from the builder engine): confirm `src/researcher.py` exports exactly `research_member`, `research_all_members`, `screen_scout`, `ResearcherError`, `TasteProfileMissingError` as its public (non-`_`-prefixed) surface; confirm `research_member`/`screen_scout` call `tt.research(...)` and **never** `llm.complete(...)` anywhere in the file (`grep -n "llm\." src/researcher.py` should return nothing); confirm the retry logic is EXACTLY one retry in both `research_member()` and each `screen_scout()` slot — never zero, never unbounded (re-check AC-53/AC-54 and AC-79/AC-80's call-count assertions specifically); confirm every accepted item/pick is persisted (`archive_researched_item`/`insert_watchlist_pick`) before the function returns, and that a persistence failure never removes an already-accepted item from the return value (AC-60, AC-82 — this is the single easiest place for a corner-cutting builder to accidentally couple "persisted" with "returned"); confirm the `SELF_NAME_TERMS`/`POLITICAL_KEYWORDS`/`DISALLOWED_CONTENT_RATINGS` guardrail lists are actually wired into `_apply_content_guardrails`/`_rating_allowed` and actually called from `_parse_and_validate_items`/`_validate_viewing_pick` (not merely defined and unused); confirm `git diff` for this WP touches only `src/researcher.py`, `src/models.py` (the one `media_sources` field), `src/m1_profiles.py` (the one `media_sources` line), and `src/db.py` (the `watchlist` DDL + 5 new methods + the two import-line additions) — no incidental edits to `token_tracker.py`, `llm.py`, `orchestrator.py`, `config/settings.json`, or any `templates/`/`prompts/` file.

## 8. Consuming team sign-off
> I confirm this spec is executable and unambiguous. All open questions are resolved.
> **Signature:** familynewsletter_build | [PENDING — sign at L-GATE_SPEC]

---

## Cross-Engine Validation — Iron Rule

Documents at LOD400+ require cross-engine validation at L-GATE_VALIDATE.
**The validator engine MUST differ from the builder engine — IRON RULE.**
No exception. No waiver. See `gates/L-GATE_VALIDATE_VALIDATE_AND_LOCK.md`.
