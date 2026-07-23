"""
Family Newsletter — Editor
Produces the editorial-voice content of one edition via a single
structured-JSON call to llm.complete() (no tools): opener, closer,
discovery bridges, Tzlil's puzzle, today-in-history, the question-of-
the-week (WhatsApp-poll shape), and the WhatsApp teaser caption.
Per LOD400 FNL-S001-P002-WP004.
"""

import copy
import logging
from typing import Optional

from . import llm
from .models import FamilyConfig, Settings

logger = logging.getLogger('family.editor')


# ─── Exception hierarchy ──────────────────────────────────────────────────────

class EditorError(Exception):
    """Base class for all editor.py errors."""


class EditorSchemaError(EditorError):
    """Raised when the editorial LLM response still fails required-field
    validation after the one reinforced schema retry (§2.5, §2.7). Every
    other llm.complete() failure (LLMConfigError, LLMJsonError,
    LLMAllDriversFailedError) is NOT wrapped — it propagates unchanged;
    see §5."""


# ─── Module-level constants ───────────────────────────────────────────────────

MODULE_NAME = "editor"
OPERATION_EDITORIAL = "editorial"
OPERATION_EDITORIAL_RETRY = "editorial_schema_retry"

DEFAULT_MAX_TOKENS = 2500  # UNVERIFIED estimate — see §1 Assumption 8

EDITOR_CREDIT = "עורכת: צליל"  # unconditional on edition #1 — §1 Assumption 5
TEASER_LINK_PLACEHOLDER = "{EDITION_LINK}"  # new convention — §1 Assumption 7

MIN_DISCOVERY_BRIDGES = 1   # soft floor — warn only, never fatal
MAX_DISCOVERY_BRIDGES = 3   # hard cap — extra entries truncated in §2.6
MIN_POLL_OPTIONS = 2        # hard validation floor (§2.4)
MAX_POLL_OPTIONS = 6        # hard validation ceiling (§2.4) — prompt asks for 3-5

# Per-member "stable taste anchor" — static, hand-authored fallback
# flavor for discovery bridges/opener when research_highlights has
# nothing for that member this week (§2.2, §2.3). Sourced from LOD200
# §4 + profiles/<member>.md. Deliberately NOT derived from
# FamilyConfig.members[].interests (that field is the OLD keyword-list
# shape REVIVAL_PLAN §3's keep/archive table is retiring in favor of
# the profiles/*.md prose files) — this constant is this module's own
# stable, hand-curated digest of that prose, not a live read of it.
MEMBER_TASTE_ANCHORS = {
    "nimrod": "הים על כל צורותיו (קייט, שייט), AI כמעצים של בונה-יחיד, "
              "הגינה כמטע עונתי (ליצ'י/מנגו). לעולם לא פוליטיקה.",
    "michal": "קפוארה תמיד (רודה, ברימבאו), לשחרר ומיינדפולנס. הפינה שלה "
              "היא מתנה לא עיתון — קצר, חם, מרגיע, בלי עומס.",
    "shaked": "Progression fantasy/LitRPG, מדע בדיוני קשה, שרת המיינקראפט "
              "המשפחתי. ENGLISH ONLY. לעולם לא פרטים אישיים.",
    "maayan": "קרקס ואומנויות אוויר (טרפז, aerial silks), ויזואלי וקצר. "
              "לעולם לא בעסק הציפורניים שלה בלי אישור מראש.",
    "tzlil": "מתמטיקה ברמת אולימפיאדה, פודקאסטים היסטוריה/מדע, מחזור "
             "שער המוות (בלי ספוילרים!), שרת המיינקראפט.",
}


# ─── System prompt (fully static — no f-strings, no per-call interpolation) ──
#
# All dynamic content (dates, member roster, research highlights, prior puzzle
# answer) goes only in _build_user_prompt()'s return value so this block stays
# byte-identical across every call and is prompt-cacheable.
#
# P0 BUILD_DIRECTIVE: Shaked English rule is UNCONDITIONAL and lives here in
# the system prompt — not only in the empty-highlights fallback of the user
# prompt. This guarantees it fires regardless of research_highlights content.
#
# P1: Nimrod no-farm-business guardrail added to the system-level guardrail
# list, not just the taste anchor comment.

EDITORIAL_SYSTEM_PROMPT = (
    "## PERSONA\n"
    "You are writing as Tzlil (צליל) — 13 years old, gifted mathematics track "
    "(olympiad level), dyslexic, and the family scientist-editor. She is the "
    "newsletter's editor: peer tone throughout, never top-down, never "
    "condescending. She hates being talked down to, and as editor, no one will. "
    "Her real day-to-day participation in writing this newsletter is hoped-for but "
    "not yet live — this generation stands entirely on its own without depending on "
    "any live input from her.\n\n"

    "## THE TWO VOICES\n"
    "Four editorial voices were A/B-tested in April 2026 on identical content "
    "(Yedioth-tabloid, Geektime-casual, Calcalist-professional, Simaniia-warm). "
    "Simaniia won opener/closer: warmth without try-hard cleverness. Calcalist won "
    "factual sections: clarity without dryness. This is why — not just a rule — "
    "the two voices are fixed:\n\n"
    "Style A — Simaniia-warm: short sentences (max 8-10 words), first names only, "
    "dinner-table warmth, no forced cleverness. Use for: opener, closer, puzzle.intro, "
    "teaser_caption, question_of_the_week fields, editors_choice.note, and the closing "
    "sentence of each discovery bridge.\n\n"
    "Style B — Calcalist-factual: factual, precise, active voice, attributed when a "
    "source is named. No hype, no tabloid sensationalism. Use for: "
    "discovery_bridges body text, today_in_history.fact.\n\n"

    "## EDITORIAL TECHNIQUES (REQUIRED — NOT OPTIONAL FLOURISH)\n"
    "1. Every discovery bridge must close with a concrete, specific family-activity "
    "prompt — not a generic suggestion. The canonical example (vary the phrasing "
    "across bridges and editions, never repeat this exact sentence verbatim): "
    "'אולי רעיון לפרויקט משפחתי?' — make it specific and actionable.\n"
    "2. today_in_history must pair its factual core with a family_idea_callout: a "
    "short, concrete way the household can riff on that fact this week.\n\n"

    "## HARD CONTENT GUARDRAILS — ALL NINE ARE MANDATORY\n"
    "1. SPOILERS: Never reveal plot points for מחזור שער המוות / Death Gate Cycle "
    "or Avatar: The Last Airbender. Reference only that someone is enjoying them — "
    "never events, outcomes, or character fates within them.\n"
    "2. NO POLITICS: Never include political content, satire, or references to public "
    "figures, parties, or news events. If research highlights contain anything "
    "political, ignore that item entirely — do not soften it, ignore it.\n"
    "3. MAAYAN BUSINESS PRIVACY: Never name or describe Yoyo's nail-art business as "
    "hers without explicit consent. Nail art or young entrepreneurship in general is "
    "fine; attributing the specific business to her by name is not.\n"
    "4. SHAKED — ABSOLUTE LANGUAGE RULE (UNCONDITIONAL): ANY content mentioning, "
    "referencing, or directed at Shaked must be written entirely in English — never "
    "Hebrew. This rule applies unconditionally: whether or not research highlights "
    "are provided for him, whether his bridge appears, whether he is named in any "
    "field. English only, always. Gender and identity themes may be served only "
    "through speculative-fiction lenses he already enjoys, and are never labeled as "
    "being about him — the content simply appears as excellent content. Never any "
    "personal or private details about him.\n"
    "5. MICHAL: Any content mentioning Michal is restorative, light, zero-effort in "
    "tone — a cup of tea, not a newspaper. Never a task list, never demanding, never "
    "professional content framed as work she must engage with.\n"
    "6. NO HEALTH OR MEDICAL: The opener and all fields are warm but never mention "
    "health, medical topics, recovery status, or wellbeing concerns for any family "
    "member. This is a blanket rule — omit these topics entirely unless the family "
    "has explicitly supplied them as content.\n"
    "7. BRIDGES — CORE MEMBERS ONLY: discovery_bridges connect only the five core "
    "members: nimrod, michal, shaked, maayan, tzlil. Extended family members are out "
    "of scope for bridges entirely.\n"
    "8. NO FABRICATION: Never invent a specific headline, article, event, or source. "
    "When research highlights are absent for a member, use the taste anchor from the "
    "user prompt and keep content general rather than inventing fake specifics.\n"
    "9. NIMROD — NO COMMERCIAL OR FARM ANGLE: Nimrod's garden is a home hobby; he "
    "grows for household consumption only. His NimrodGarden store is closed. Never "
    "frame his gardening as a business, farm, commercial venture, or professional "
    "agricultural activity. Seasonal home-growing and fruit trees only — no farm "
    "business angle, ever.\n\n"

    "## OUTPUT FORMAT\n"
    "Respond with ONLY a single JSON object — no prose before or after, no markdown "
    "code fences, no explanation. Use the exact field names listed in the schema "
    "below. Plain text in all fields except opener and closer (those may use bare "
    "<strong> and <em> HTML tags only — no other HTML, no markdown asterisks). "
    "All other fields: plain text only.\n\n"

    "## REQUIRED JSON SCHEMA\n"
    "Your entire response must be a single JSON object. Required top-level fields:\n"
    "  opener         — string, Style A, Hebrew, <strong>/<em> allowed\n"
    "  closer         — string, Style A, Hebrew, <strong>/<em> allowed\n"
    "  puzzle         — object with sub-fields:\n"
    "    intro              — string, Style A, one warm framing sentence\n"
    "    question           — string, olympiad-level math puzzle, self-contained\n"
    "    answer             — string, this week's answer (never shown this week)\n"
    "    last_week_answer_reveal — string, reveal or first-edition welcome\n"
    "  today_in_history — object with sub-fields:\n"
    "    fact               — string, Style B, 2-3 factual sentences\n"
    "    family_idea_callout — string, Style A, concrete family activity idea\n"
    "  question_of_the_week — object with sub-fields:\n"
    "    preamble           — string, Style A, one lead-in sentence\n"
    "    poll_question      — string, Style A, short WhatsApp poll question\n"
    "    poll_options       — array of 3-5 strings (2-6 accepted), Style A\n"
    "  teaser_caption — string, Style A, punchy plain text for WhatsApp;\n"
    "                   must contain the link placeholder token exactly once\n"
    "                   (the placeholder is specified in the user prompt)\n"
    "Optional fields:\n"
    "  discovery_bridges — array of 2-3 objects, each with:\n"
    "    from_member — one of: nimrod, michal, shaked, maayan, tzlil\n"
    "    to_member   — one of: nimrod, michal, shaked, maayan, tzlil (differs from from_member)\n"
    "    text        — string, Style B body closing with Style A activity prompt\n"
    "  editors_choice — object with:\n"
    "    ref  — string label (e.g. bridge_1)\n"
    "    note — string, Tzlil's peer voice, starts with 'בחירת העורכת: ...'\n\n"

    "All Hebrew content in Hebrew; all content for or about Shaked in English."
)


# ─── User prompt builder ──────────────────────────────────────────────────────

def _build_user_prompt(
    family: FamilyConfig,
    research_highlights: Optional[dict[str, list[str]]],
    prior_puzzle_answer: Optional[str],
    today: str,
) -> str:
    """Builds the dynamic (volatile) half of the editorial prompt — every
    part of the request that changes week to week. Kept separate from
    EDITORIAL_SYSTEM_PROMPT (static) so the system block stays cacheable
    (see prompt-caching guidance: stable content first, volatile last).
    research_highlights may be None or missing entries for some/all
    members — every member falls back to MEMBER_TASTE_ANCHORS (§2.1).
    """
    highlights = research_highlights or {}

    roster_lines = []
    for member in family.members:
        member_highlights = highlights.get(member.id) or []
        if member_highlights:
            highlight_str = "; ".join(member_highlights)
        else:
            highlight_str = (
                f"(אין דגשים מהמחקר השבוע — היצמד לעוגן הטעם) "
                f"{MEMBER_TASTE_ANCHORS.get(member.id, '')}"
            )
        roster_lines.append(
            f"- {member.nickname_newsletter} ({member.id}, "
            f"{member.language_preference}): {highlight_str}"
        )
    roster_block = "\n".join(roster_lines)

    if prior_puzzle_answer:
        puzzle_context = (
            f"תשובת החידה משבוע שעבר (לשקף בחום ב-"
            f"last_week_answer_reveal): {prior_puzzle_answer}"
        )
    else:
        puzzle_context = (
            "זו החידה הראשונה — אין תשובה קודמת לחשוף. נסחו "
            "last_week_answer_reveal כהודעת פתיחה חמה על החידה "
            "השבועית החדשה (למשל: 'זו החידה הראשונה שלנו!'), לא "
            "כחשיפת תשובה."
        )

    return (
        f"תאריך המהדורה: {today}\n\n"
        f"חברי המשפחה ודגשי המחקר השבועי:\n{roster_block}\n\n"
        f"{puzzle_context}\n\n"
        f"החזירו אך ורק אובייקט JSON יחיד התואם בדיוק לסכימה שקיבלתם "
        f"בהנחיות המערכת. placeholder הקישור בטיזר חייב להופיע "
        f"בדיוק כפי שהוא: {TEASER_LINK_PLACEHOLDER}"
    )


# ─── Validation ──────────────────────────────────────────────────────────────

def _validate_editorial(data: dict) -> list[str]:
    """Checks ONLY the hard-required fields/types/shapes from §2.2's
    schema. Returns a list of human-readable error strings (empty list
    = valid). Never raises. Soft fields (discovery_bridges quality,
    editors_choice, family_idea_callout, last_week_answer_reveal when
    no prior answer exists) are NOT checked here — see §2.6."""
    errors = []

    def _require_str(value, path):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{path}: missing or empty string")

    _require_str(data.get("opener"), "opener")
    _require_str(data.get("closer"), "closer")

    puzzle = data.get("puzzle")
    if not isinstance(puzzle, dict):
        errors.append("puzzle: missing or not an object")
    else:
        _require_str(puzzle.get("intro"), "puzzle.intro")
        _require_str(puzzle.get("question"), "puzzle.question")
        _require_str(puzzle.get("answer"), "puzzle.answer")

    history = data.get("today_in_history")
    if not isinstance(history, dict):
        errors.append("today_in_history: missing or not an object")
    else:
        _require_str(history.get("fact"), "today_in_history.fact")

    qow = data.get("question_of_the_week")
    if not isinstance(qow, dict):
        errors.append("question_of_the_week: missing or not an object")
    else:
        _require_str(qow.get("poll_question"), "question_of_the_week.poll_question")
        options = qow.get("poll_options")
        if not isinstance(options, list) or not (
            MIN_POLL_OPTIONS <= len(options) <= MAX_POLL_OPTIONS
        ):
            errors.append(
                f"question_of_the_week.poll_options: must be a list of "
                f"{MIN_POLL_OPTIONS}-{MAX_POLL_OPTIONS} strings, got "
                f"{options!r}"
            )
        elif not all(isinstance(o, str) and o.strip() for o in options):
            errors.append("question_of_the_week.poll_options: all entries must be non-empty strings")

    caption = data.get("teaser_caption")
    if not isinstance(caption, str) or not caption.strip():
        errors.append("teaser_caption: missing or empty string")
    elif TEASER_LINK_PLACEHOLDER not in caption:
        errors.append(f"teaser_caption: missing required placeholder {TEASER_LINK_PLACEHOLDER!r}")

    return errors


# ─── Retry-prompt builder ─────────────────────────────────────────────────────

def _build_retry_prompt(original_user_prompt: str, errors: list[str]) -> str:
    """Appends a correction instruction to the original user prompt,
    listing exactly what validation found wrong. Used for the ONE
    schema-level retry in generate_editorial() (§2.7) — a DIFFERENT
    retry from llm.complete()'s own JSON-syntax-only retry (WP001 §2.3):
    that one fires when the response isn't parseable JSON at all; this
    one fires when it parsed fine but is missing/malformed required
    fields."""
    error_list = "\n".join(f"- {e}" for e in errors)
    return (
        f"{original_user_prompt}\n\n"
        f"התגובה הקודמת שלך לא כללה את כל השדות הנדרשים. תקנו והחזירו "
        f"מחדש אובייקט JSON שלם:\n{error_list}"
    )


# ─── Sensitive-term scanner ───────────────────────────────────────────────────

_SENSITIVE_TERM_PAIRS = [
    (("יויו", "מעיין"), ("ציפורניים", "נייל", "nail")),
]


def _scan_sensitive_terms(data: dict) -> list[str]:
    """Best-effort, log-only heuristic for LOD200 §5 guardrail #3
    (Yoyo's business name) — see §2.3 point 4's note on the enforcement
    boundary. Never raises, never blocks; returns warning strings for
    the caller to log. Scans every string value in the dict (shallow +
    one level of nesting, matching this module's own schema shape)."""
    def _all_strings(obj):
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for v in obj.values():
                yield from _all_strings(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from _all_strings(v)

    haystack = " ".join(_all_strings(data)).lower()
    warnings = []
    for names, terms in _SENSITIVE_TERM_PAIRS:
        if any(n.lower() in haystack for n in names) and any(t.lower() in haystack for t in terms):
            warnings.append(
                f"possible LOD200 §5 guardrail #3 hit: output mentions "
                f"{names!r} alongside {terms!r} — review before send"
            )
    return warnings


# ─── Deterministic post-processing ───────────────────────────────────────────

def _normalize_editorial(data: dict, family: FamilyConfig,
                          prior_puzzle_answer: Optional[str]) -> dict:
    """Applies deterministic, non-LLM fixups AFTER _validate_editorial()
    has passed. Never raises — this function only repairs soft
    field issues and adds Python-owned metadata."""
    result = copy.deepcopy(data)
    valid_ids = {m.id for m in family.members}

    # Discovery bridges: drop self-referential or unknown-member-id
    # entries, then cap at MAX_DISCOVERY_BRIDGES.
    bridges = result.get("discovery_bridges") or []
    clean_bridges = []
    for b in bridges:
        if not isinstance(b, dict):
            continue
        frm, to = b.get("from_member"), b.get("to_member")
        if frm not in valid_ids or to not in valid_ids or frm == to:
            logger.warning(f"[editor] dropping malformed discovery bridge: {b!r}")
            continue
        clean_bridges.append(b)
    if len(clean_bridges) > MAX_DISCOVERY_BRIDGES:
        logger.warning(
            f"[editor] {len(clean_bridges)} discovery bridges returned, "
            f"truncating to {MAX_DISCOVERY_BRIDGES}"
        )
        clean_bridges = clean_bridges[:MAX_DISCOVERY_BRIDGES]
    elif len(clean_bridges) <= MIN_DISCOVERY_BRIDGES:
        logger.warning(f"[editor] only {len(clean_bridges)} usable discovery bridges")
    result["discovery_bridges"] = clean_bridges

    # Puzzle: fill last_week_answer_reveal fallback only when the LLM
    # omitted it AND a prior answer existed to reveal.
    puzzle = result.setdefault("puzzle", {})
    if prior_puzzle_answer and not puzzle.get("last_week_answer_reveal"):
        puzzle["last_week_answer_reveal"] = (
            f"אגב — תשובת החידה משבוע שעבר הייתה {prior_puzzle_answer}!"
        )
    elif not prior_puzzle_answer and not puzzle.get("last_week_answer_reveal"):
        puzzle["last_week_answer_reveal"] = "זו החידה הראשונה שלנו — בהצלחה!"

    # today_in_history: fallback family_idea_callout.
    history = result.setdefault("today_in_history", {})
    if not history.get("family_idea_callout"):
        history["family_idea_callout"] = "אולי רעיון לשיחה השבוע?"

    # question_of_the_week: dedupe poll_options, preserving order.
    qow = result.setdefault("question_of_the_week", {})
    options = qow.get("poll_options") or []
    seen = set()
    deduped = []
    for o in options:
        if o not in seen:
            seen.add(o)
            deduped.append(o)
    qow["poll_options"] = deduped

    # editors_choice: fallback to a generic Tzlil-voiced note built
    # from the first surviving bridge, or a static generic note if
    # there are no bridges at all.
    choice = result.get("editors_choice")
    if not isinstance(choice, dict) or not choice.get("note"):
        if clean_bridges:
            choice = {
                "ref": "bridge_1",
                "note": "בחירת העורכת: זה שאני, צליל, בחרתי השבוע.",
            }
        else:
            choice = {"ref": "", "note": "בחירת העורכת: כל הגיליון השבוע!"}
    result["editors_choice"] = choice

    # Deterministic, non-LLM metadata — never asked of the model.
    result["editor_credit"] = EDITOR_CREDIT

    for warning in _scan_sensitive_terms(result):
        logger.warning(f"[editor] {warning}")

    return result


# ─── Mock mode ────────────────────────────────────────────────────────────────

def _mock_editorial(family: FamilyConfig,
                    research_highlights: Optional[dict],
                    prior_puzzle_answer: Optional[str],
                    today: str) -> dict:
    """Deterministic canned editorial content for --mock builds. Every
    invocation with the same inputs returns byte-identical output
    (no timestamps, no randomness). Passes _validate_editorial() with
    zero errors. Never calls llm.complete() — see §1 Assumption 4."""
    return _normalize_editorial(
        {
            "opener": (
                "בוקר טוב, בית ולד! השבוע מלא בגילויים: "
                "<strong>מיינקראפט חדש</strong>, קפוארה עולה דרגה, "
                "ומתמטיקה ברמה חדשה. בואו נתחיל!"
            ),
            "closer": (
                "זהו לשבוע הזה, בית ולד! ספרו לנו מה הכי אהבתם — "
                "נתראה בשישי הבא."
            ),
            "discovery_bridges": [
                {
                    "from_member": "nimrod",
                    "to_member": "tzlil",
                    "text": (
                        "נימרוד מפליג עם הרוח, וצליל פותרת בעיות עם "
                        "אותה סקרנות בדיוק — שני חוקרים, שני ימים "
                        "שונים. אולי רעיון לפרויקט משפחתי: מסלול "
                        "ניווט מתמטי לשייט הבא?"
                    ),
                },
                {
                    "from_member": "michal",
                    "to_member": "maayan",
                    "text": (
                        "מיכל מלמדת רודה, יויו מלמדת טרפז — שתיהן "
                        "בונות קהילה סביב תנועה באוויר. אולי כדאי "
                        "להשוות טכניקות איזון בפעם הבאה שנפגשים?"
                    ),
                },
            ],
            "puzzle": {
                "intro": "החידה השבועית של צליל — הכינו את המוח!",
                "question": (
                    "בקופסה יש כדורים אדומים וכחולים, 10 בסך הכול. "
                    "מוציאים 2 כדורים בלי החזרה, וההסתברות ששניהם "
                    "אדומים היא בדיוק 1/3. כמה כדורים אדומים יש "
                    "בקופסה?"
                ),
                "answer": "6",
                "last_week_answer_reveal": None,  # normalized by _normalize_editorial
            },
            "today_in_history": {
                "fact": (
                    "ב-22 ביולי 1969 חזרו אפולו 11 והנחיתו את הירח על "
                    "מפת ההיסטוריה — ניל ארמסטרונג הפך לאדם הראשון "
                    "שדרך עליו. מדע ואומץ, יחד."
                ),
                "family_idea_callout": "אולי ערב צפייה בסרטון שיגור אמיתי מתאים השבוע?",
            },
            "question_of_the_week": {
                "preamble": "השבוע אנחנו רוצים לדעת:",
                "poll_question": "מה כדאי לבנות בשרת המיינקראפט המשפחתי?",
                "poll_options": [
                    "טירה ענקית",
                    "עיר שלמה",
                    "פארק שעשועים",
                    "משהו מפתיע — תגיבו!",
                ],
            },
            "teaser_caption": (
                "📰 בית ולד השבועי הגיע! מיינקראפט, קפוארה, וחידה "
                "שתשבור לכם את הראש מחכים לכם. הצביעו בסקר השבוע "
                f"וספרו לנו מה חשבתם 👇 {TEASER_LINK_PLACEHOLDER}"
            ),
            "editors_choice": {
                "ref": "bridge_1",
                "note": (
                    "בחירת העורכת: זה שאבא וגם אני חושבים כמו חוקרים, "
                    "כל אחד בים שלו — פשוט מגניב. — צליל"
                ),
            },
        },
        family,
        prior_puzzle_answer,
    )


# ─── Public entry point ───────────────────────────────────────────────────────

def generate_editorial(
    family: FamilyConfig,
    research_highlights: Optional[dict[str, list[str]]],
    prior_puzzle_answer: Optional[str],
    today: str,
    settings: Settings,
    *,
    mock: bool = False,
) -> dict:
    """THE public entry point. Produces one edition's full editorial
    content as a plain dict matching §2.2's schema plus the
    editor_credit key (§2.6). mock=True short-circuits before
    llm.complete() is ever called (§1 Assumption 4, §2.7) — no llm
    driver, no network call, deterministic.

    Real path: exactly one llm.complete() call, and — only if
    _validate_editorial() finds required fields missing or malformed —
    exactly one additional reinforced-prompt retry (a SEPARATE
    top-level call from llm.complete()'s own internal JSON-syntax
    retry, WP001 §2.3). If the retry also fails validation, raises
    EditorSchemaError. Any LLMError raised by llm.complete() itself
    (LLMConfigError, LLMJsonError, LLMAllDriversFailedError) is NOT
    caught here — it propagates to the caller unchanged (§5).
    """
    if mock:
        return _mock_editorial(family, research_highlights, prior_puzzle_answer, today)

    max_tokens = settings.ai.get('editorial_max_tokens', DEFAULT_MAX_TOKENS)
    user_prompt = _build_user_prompt(family, research_highlights, prior_puzzle_answer, today)

    raw = llm.complete(
        user_prompt,
        system=EDITORIAL_SYSTEM_PROMPT,
        max_tokens=max_tokens,
        module=MODULE_NAME,
        operation=OPERATION_EDITORIAL,
        newsletter_date=today,
        expect_json=True,
    )

    errors = _validate_editorial(raw)
    if errors:
        logger.warning(f"[editor] editorial response failed validation, retrying once: {errors}")
        retry_prompt = _build_retry_prompt(user_prompt, errors)
        raw = llm.complete(
            retry_prompt,
            system=EDITORIAL_SYSTEM_PROMPT,
            max_tokens=max_tokens,
            module=MODULE_NAME,
            operation=OPERATION_EDITORIAL_RETRY,
            newsletter_date=today,
            expect_json=True,
        )
        retry_errors = _validate_editorial(raw)
        if retry_errors:
            raise EditorSchemaError(
                f"editorial response still invalid after 1 retry: {retry_errors}"
            )

    return _normalize_editorial(raw, family, prior_puzzle_answer)
