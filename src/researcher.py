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


# ─── Exceptions ───────────────────────────────────────────────────────────────

class ResearcherError(Exception):
    """Base class for all researcher.py errors."""


class TasteProfileMissingError(ResearcherError):
    """Raised when profiles/<member_id>.md does not exist, or exists but is
    empty/whitespace-only. This is a deployment/config bug (a required input
    file is missing), NOT a content-quality issue — unlike a content
    shortfall (handled by returning fewer items, never raising; §1
    Assumption 7), research_member()/screen_scout() cannot even construct a
    prompt without this file, so it is not recoverable inside this module."""


# ─── Constants ────────────────────────────────────────────────────────────────

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


# ─── §2.2 Taste-profile loading + member/language helpers ────────────────────

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


# ─── §2.3 Prompt-context formatting helpers ───────────────────────────────────

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
    / From Our Shelf content' requirement (task MODULE SCOPE item 4).

    P0 FIX: check member-specific themes BEFORE including shared, so a member
    with no curated relevance entry (e.g. shaked, maayan, tzlil) correctly
    returns the fallback even when 'shared' has themes — the OR short-circuit
    on the combined set must not absorb the empty-member case."""
    bookshelf = family.shared_interests.get("bookshelf", {})
    books = bookshelf.get("books", [])
    relevance = bookshelf.get("profile_insights", {}).get("relevance", {})
    member_themes = set(relevance.get(member_id, []))
    if not member_themes:
        return "(no specifically relevant family bookshelf titles on file for this member)"
    relevant_themes = member_themes | set(relevance.get("shared", []))
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


# ─── §2.4 JSON response parsing ───────────────────────────────────────────────

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


# ─── §2.5 Content guardrails ──────────────────────────────────────────────────

# Per-member "never surface content ABOUT the member themselves" guard.
SELF_NAME_TERMS = {
    "nimrod": ["נימרוד ולד"],
    "michal": ["מיכל ולד", "מיכל בן-צבי", "מיכל בן צבי"],
    "shaked": ["שקד ולד", "Shaked Wald"],
    "maayan": ["מעיין ולד", "יויו ולד", "yuyu_m2569"],
    "tzlil": ["צליל ולד"],
}

# Best-effort, NON-EXHAUSTIVE keyword guard — global, applies to every
# member's every item. Defense-in-depth layer only, backstopping the "no
# politics" prompt instruction (§2.9). Does not catch spoilers or Shaked's
# "never labeled" framing rule — those are prompt-only (§1 Assumption 8, §5).
POLITICAL_KEYWORDS = [
    "כנסת", "ח\"כ", "חבר כנסת", "ראש הממשלה", "בחירות", "קואליציה",
    "אופוזיציה", "נתניהו",
    "knesset", "election", "parliament", "prime minister",
    "president biden", "president trump",
]

# Streaming content ratings treated as too old for this household (includes
# a 13-year-old). Denylist, not allowlist — more robust to rating-vocabulary
# variance. Matches profiles/family.md's "עד 16+ זה בסדר" (up to 16+ is fine).
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


# ─── §2.6 Research-item validation ───────────────────────────────────────────

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


# ─── §2.7 Mock-mode item generators ──────────────────────────────────────────

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


# ─── §2.8 Low-level research-call wrapper ────────────────────────────────────

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


# ─── §2.9 research_member() prompt templates + builder ───────────────────────

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


# ─── §2.10 research_member() and research_all_members() ──────────────────────

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


# ─── §2.11 Viewing-pick validation ────────────────────────────────────────────

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


# ─── §2.12 Personal-pick rotation ────────────────────────────────────────────

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


# ─── §2.13 screen_scout() prompt templates + builders ────────────────────────

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
    newsletter_date: str,  # P1 FIX: was hardcoded "(see above)" — pass real date
) -> tuple[str, str]:
    slot_label = "family_pick" if slot == "family_pick" else "personal_pick"
    extended_blocklist = recent_titles | {previous_title.lower()}
    system = _SCREEN_SCOUT_RETRY_SYSTEM.format(
        slot_label=slot_label,
        previous_title=previous_title,
        reason=reason,
        slot_instructions=_slot_instructions(slot, personal_member, personal_taste),
        dedup_days=DEFAULT_DEDUP_DAYS,
        blocklist=_format_blocklist(extended_blocklist),
    )
    user = _SCREEN_SCOUT_USER.format(
        personal_display_name=personal_member.nickname_newsletter or personal_member.name,
        personal_member_id=personal_member.id,
        personal_taste_profile=personal_taste,
        dedup_days=DEFAULT_DEDUP_DAYS,
        blocklist=_format_blocklist(extended_blocklist),
        newsletter_date=newsletter_date,
    )
    return system, user


# ─── §2.14 screen_scout() — public entry point ───────────────────────────────

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
                    slot, previous_title, reason, personal_member, personal_taste,
                    recent_titles, newsletter_date,
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
