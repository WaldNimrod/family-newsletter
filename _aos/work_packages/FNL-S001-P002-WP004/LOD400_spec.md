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

# editor.py — Editorial Voice & Structured Content Generator — LOD400 Implementation Spec

**work_package_id:** FNL-S001-P002-WP004
**parent_lod200:** _aos/work_packages/FNL-S001-P001-WP001/LOD200.md
**parent_lod300:** N/A — Track A only
**approved_by:** [PENDING — familynewsletter_build sign-off at L-GATE_SPEC]
**approved_at:** [PENDING]

## 1. Scope reminder

This WP creates **`src/editor.py`** (new file, does not exist yet) — the single module that produces every piece of *editorial voice* content in the newsletter: the opener, the closer, 2–3 discovery bridges between family members, Tzlil's hard puzzle (plus a reveal of last week's answer), a "today in history" item, the question-of-the-week (designed as a WhatsApp-poll shape), and the WhatsApp teaser caption. Per **REVIVAL_PLAN_2026-07-22.md §3** (pipeline sketch, quoted verbatim below), all of this comes from **exactly one** Claude call — no tools, structured JSON output — made through the already-specified `llm.complete()` (sibling **FNL-S001-P002-WP001**, `src/llm.py`):

> **מקור: REVIVAL_PLAN_2026-07-22.md §3, "הארכיטקטורה החדשה"**
> ```
> ├─ 1× editorial  ── claude-sonnet-5, בלי כלים, structured output
> │     פתיח/סגיר, גשרי גילוי (2–3), חידה לצליל, היום בהיסטוריה,
> │     שאלת השבוע, וטקסט הטיזר לוואטסאפ
> ```
> and **§4, Phase A step 3:** *"3. `token_tracker` מעודכן + `researcher.py` + `editor.py` (כולל מצב `--mock`)"*

This module **replaces** the eight separate small LLM calls `src/m3_normalizer.py` used to make one field at a time (`_generate_opener`, `_generate_closer`, `_generate_puzzle`, `_generate_bridges`, `_generate_survey`, `_generate_history`, plus the two `_en` variants) with **one** combined structured call. `m3_normalizer.py` itself is slated for archival per REVIVAL_PLAN's keep/archive table (`archive/legacy/`) — this WP does not edit or archive it, but its existing functions are the **shape precedent** this spec salvages intent/voice from, not code to import.

**Section mapping to the parent contract.** LOD200 §2's numbered MUST-contain list (13 sections) assigns this module's output to sections **2, 6, 9, 11, 12, 13**:

| LOD200 §2 item | Section | This module's field(s) |
|---|---|---|
| 2 | פתיח / Opener | `opener` |
| 6 | גשר גילוי / Discovery | `discovery_bridges` |
| 9 | חידה / Puzzle | `puzzle` |
| 11 | היום בהיסטוריה / Today in history | `today_in_history` |
| 12 | סקר / Survey | `question_of_the_week` |
| 13 | סגירה / Closer + Footer | `closer`, `editor_credit` |

**LOD200 §2 item 8 ("שולחן שישי" / family-table conversation-starter) is explicitly NOT this module's output.** It is a *researched, selected* item (its own open conversation-question comes bundled with it) belonging to WP003 (`researcher.py`) — confirmed by `profiles/family.md`: *"מה עושה פריט 'שולחן שישי' טוב... מגיע עם שאלה פתוחה טובה"* (a good open question, distinct from the poll). Do not conflate the two: `question_of_the_week` (this module, §2 item 12, a **poll**) and the family-table item's own open question (WP003, §2 item 8, **not** a poll) are two different questions in two different sections of the same edition.

**Question-of-the-week is a POLL, not an open question.** This is a direct, sourced editorial decision, not this spec's invention — `profiles/family.md`: *"סקרים ומועצות משפחה = מנגנון ההשתתפות המוכח... שאלת השבוע בגיליון תהיה סקר וואטסאפ, לא שאלה פתוחה"* (polls are the proven engagement mechanism in the family WhatsApp history; the weekly question will be a WhatsApp poll, not an open question). This module's job is to **shape the data** as a poll (question + fixed options); actually **sending** it as a native WhatsApp poll via WAHA is explicitly Phase C (LOD200 §7: *"WAHA poll for survey (Phase C)"*) — see §1 Assumption 2.

### Assumptions (where the brief was silent — flag these at L-GATE_VALIDATE if wrong)

1. **`research_highlights` (this WP's own input contract for weekly grounding) is a provisional, minimal shape** — `WP003 (researcher.py)` does not exist yet at spec-authoring time (no LOD400 for it in `_aos/work_packages/`). Rather than block this WP on an undefined upstream shape, §2.3 defines the smallest useful contract this module needs: `dict[str, list[str]] | None` — `{member_id: [short topic/highlight strings]}`. When WP003 lands, if its real return shape differs, adapting WP003's output into this minimal shape is the integration WP's job (orchestrator wiring, out of scope here — see §6), mirroring how WP001 (§1 Assumption 5) took a documented, provisional dependency on WP002's `token_tracker.generate()` signature without blocking on it landing first.
2. **The WhatsApp-poll option count (3–5 requested in the prompt, 2–6 accepted by validation) is an editorial-quality judgment call by this spec, not a verified WhatsApp/WAHA platform limit.** No source material available at spec-authoring time states WAHA's actual native-poll option ceiling (or whether WAHA Core vs Plus even supports sending polls — REVIVAL_PLAN §3 flags `sendImage` support as still-to-verify, and says nothing about poll-send support). Since native poll delivery is Phase C (LOD200 §7), this is inert for edition-1: this module only needs to produce a well-formed `poll_question` + `poll_options`. Verify WAHA's real constraint before Phase C wires actual poll sending.
3. **This module does not extend `token_tracker.py`'s `_mock_generate()` operation-dispatch table.** That file is WP002's exclusive territory (its own scope statement: *"This WP updates the existing `src/token_tracker.py`"*), and its existing `_mock_generate()` returns **per-operation, hand-written canned strings** keyed by `operation` (e.g. `elif operation == 'puzzle': return "..."`) — a pattern built for the OLD architecture's many small single-field calls, not this WP's one combined structured-JSON call. WP002 §2.3 itself sets the precedent for why: *"the exact JSON/text shape `_mock_research()` returns... WP003 defines what shape real (and therefore meaningfully-mockable) research output should take."* Following that same precedent, **this module owns its own mock shape** (§2.7) and never depends on `llm.py`'s or `token_tracker.py`'s generic mock text — see §1 Assumption 4 below for why relying on them would actively break.
4. **Relying on `llm.complete()`'s own (upstream) mock plumbing instead of a local mock would not work, and this is a verified, not speculative, finding.** Reading `src/token_tracker.py`'s current `_mock_generate()` (lines 120–147) confirms it dispatches on `operation` to hand-written strings, with no case that would produce anything matching this module's specific JSON schema — a request through the real `llm.complete()` path with the global `mock=True` config would receive that generic mock text, fail `expect_json=True` parsing (or parse into a JSON object missing every field this module requires), exhaust `llm.py`'s own one JSON-retry, and then fail this module's own schema validation and its one schema-retry too — a guaranteed, wasteful failure loop for every mock build. §2.7's `mock` parameter therefore short-circuits **before** `llm.complete()` is ever called, exactly mirroring `TokenTracker.generate()`/`research()`'s own "mock short-circuits before any network call" pattern, just one layer up.
5. **`editor_credit` ("עורכת: צליל") is emitted unconditionally by this module's Python code (not asked of the LLM) on every edition-1 call, regardless of whether Tzlil has actually engaged with the pipeline yet.** There is a real, sourced tension here: REVIVAL_PLAN §3.5.3 says the credit belongs *"מהגיליון הראשון שבו השתתפה"* (from the first edition she actually participated in) — but LOD200 §2 item 13 lists the credit as a **mandatory edition-1 footer element** with no participation gate, and this WP's own module-scope brief is explicit: *"her real involvement is HOPED-FOR... edition-1 generates in her editorial voice without depending on her live participation."* LOD200 is the approved, higher-authority contract (*"the SSOT the P002 LOD400 build specs derive from"*) and this WP's brief independently confirms the same resolution — so LOD200 wins: the credit and the editorial voice are unconditional from edition #1. Flag for team_00 if this reading is wrong.
6. **This WP does not edit `src/models.py`.** `GeneratedContent`/`NEO` are existing dataclasses this module's output will eventually feed, but no WP currently charters editing `models.py` for this purpose, and editing a shared file outside this WP's one-new-file scope would risk colliding with whatever future integration WP does own that change (mirroring WP001's own restraint: *"Wiring `llm.py` into `orchestrator.py`... — separate WPs"*). This module returns a plain `dict` (§2.2, §4) and §3 documents a **non-binding mapping table** onto `GeneratedContent`/`NEO`'s existing fields for that future WP's benefit — it is documentation, not a code change this WP performs.
7. **`{EDITION_LINK}` (the teaser-caption link placeholder, §2.1) is a new literal-string convention invented by this spec** — no prior WP defines one. Whichever future WP sends the WhatsApp teaser (`publisher.py`/`whatsapp.py`, out of scope here) is responsible for `str.replace(editor.TEASER_LINK_PLACEHOLDER, real_url)` before sending.
8. **`ai.editorial_max_tokens` default of 2500 is this spec's own estimate**, not verified against a live run: opener + closer + up to 3 bridges + puzzle (intro/question/answer/reveal) + history (fact/callout) + poll (preamble/question/options) + teaser caption + editor's-choice note, in Hebrew (tokenizes ~30% more than 4.6 per the engine-env-canon memory) plus JSON structural overhead, with `thinking_enabled` left at `generate()`'s own default of `False` (no thinking-token headroom needed — WP001 §1 Assumption 5). Tunable via `settings.ai.get('editorial_max_tokens', ...)`; re-baseline after the first live edition.

## 2. Technical specification

This WP creates one new file, `src/editor.py`. Implement the following components **in this exact order within that one file** — later components reference constants/functions defined earlier.

### 2.1 Module foundations — imports, exception hierarchy, constants

**What to implement:**

1. Module docstring + imports:

```python
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
```

2. Exception hierarchy:

```python
class EditorError(Exception):
    """Base class for all editor.py errors."""


class EditorSchemaError(EditorError):
    """Raised when the editorial LLM response still fails required-field
    validation after the one reinforced schema retry (§2.5, §2.7). Every
    other llm.complete() failure (LLMConfigError, LLMJsonError,
    LLMAllDriversFailedError) is NOT wrapped — it propagates unchanged;
    see §5."""
```

3. Module-level constants:

```python
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
```

**Acceptance criteria:**
- [ ] AC-01: `from src import editor` (or `import src.editor as editor`) succeeds with no import-time errors and no network/subprocess/file I/O — importing must not require `llm.configure()` to have been called.
- [ ] AC-02: `EditorError` is defined at module level; `EditorSchemaError` subclasses `EditorError`.
- [ ] AC-03: `MEMBER_TASTE_ANCHORS` has exactly the 5 keys `{"nimrod", "michal", "shaked", "maayan", "tzlil"}`, each a non-empty string. `TEASER_LINK_PLACEHOLDER == "{EDITION_LINK}"`, `EDITOR_CREDIT == "עורכת: צליל"`, `MAX_DISCOVERY_BRIDGES == 3`, `MIN_POLL_OPTIONS == 2`, `MAX_POLL_OPTIONS == 6`.

### 2.2 The structured-output JSON schema (documentation — referenced by §2.3, §2.4, §2.5)

**What to implement:** nothing executable in this subsection — it defines the contract that §2.3 (prompt), §2.4 (validation), and §4 (API contract) all implement against. Read it before writing any of those.

**Field table:**

| Field | Type | Hard-required? | Voice | Notes |
|---|---|---|---|---|
| `opener` | string | ✅ | Style A (Simaniia warm) | Limited HTML OK: `<strong>`, `<em>` only. No markdown. |
| `closer` | string | ✅ | Style A | Same HTML rule as `opener`. |
| `discovery_bridges` | array of object | soft (§2.5, §2.6) | body: Style B; closing sentence: Style A-flavored family-activity prompt | 2–3 requested; 1–3 accepted; >3 truncated. Plain text, no HTML. |
| `discovery_bridges[].from_member` | string enum | — | — | One of the 5 canonical member ids present in `family.members`. |
| `discovery_bridges[].to_member` | string enum | — | — | Same enum; must differ from `from_member`. |
| `discovery_bridges[].text` | string | — | — | Must end in a **concrete** family-activity prompt (§2.3 technique 1). |
| `puzzle.intro` | string | ✅ | Style A | 1 warm framing sentence. |
| `puzzle.question` | string | ✅ | neutral/precise | Olympiad-level, self-contained (no external references the reader can't see). |
| `puzzle.answer` | string | ✅ | neutral | **This week's** answer — never rendered in this week's edition; persisted by the caller for next week's reveal. |
| `puzzle.last_week_answer_reveal` | string | conditional (§2.4 AC-14) | Style A | Required **only** when `prior_puzzle_answer` was given as input; a first-edition framing sentence otherwise. |
| `today_in_history.fact` | string | ✅ | Style B | 2–3 sentences, per STYLE_GUIDE §4 item 10. |
| `today_in_history.family_idea_callout` | string | soft (§2.6 fallback) | Style A-flavored | Short prompt tying the fact to a family activity (DESIGN_FISH technique 2). |
| `question_of_the_week.preamble` | string | soft | Style A | 1 short lead-in sentence. |
| `question_of_the_week.poll_question` | string | ✅ | Style A | Short — this is a poll question, not an essay prompt. |
| `question_of_the_week.poll_options` | array of string | ✅ | Style A | 3–5 requested; 2–6 accepted (§1 Assumption 2). Deduplicated in §2.6. |
| `teaser_caption` | string | ✅ | Style A, punchy | Must contain the literal substring `{EDITION_LINK}` exactly once (§2.4 AC-16). WhatsApp message text — plain text, no HTML. |
| `editors_choice.ref` | string | soft | — | Free-text label of what it refers to (e.g. `"bridge_1"`). |
| `editors_choice.note` | string | soft (§2.6 fallback) | Tzlil's own voice, peer tone | "בחירת העורכת" — DESIGN_FISH / tzlil.md's named corner, generated (not sourced from her live input) per module scope. |

`editor_credit` is **not** part of this table — it is added by Python code after validation (§2.6), never requested from the LLM (§1 Assumption 5).

**Canonical example (also §2.7's mock return value — see there for the literal object):**

```json
{
  "opener": "בוקר טוב, בית ולד! השבוע מלא בגילויים...",
  "closer": "זהו לשבוע הזה, בית ולד!...",
  "discovery_bridges": [
    {"from_member": "nimrod", "to_member": "tzlil", "text": "..."},
    {"from_member": "michal", "to_member": "maayan", "text": "..."}
  ],
  "puzzle": {
    "intro": "החידה השבועית של צליל — הכינו את המוח!",
    "question": "...",
    "answer": "6",
    "last_week_answer_reveal": "תשובת השבוע שעבר הייתה..."
  },
  "today_in_history": {
    "fact": "...",
    "family_idea_callout": "..."
  },
  "question_of_the_week": {
    "preamble": "השבוע אנחנו רוצים לדעת:",
    "poll_question": "...",
    "poll_options": ["...", "...", "...", "..."]
  },
  "teaser_caption": "📰 בית ולד השבועי הגיע!... {EDITION_LINK}",
  "editors_choice": {"ref": "bridge_1", "note": "בחירת העורכת: ..."}
}
```

**Validation JSON Schema (informational — `_validate_editorial`, §2.4, implements exactly this; not passed to the API, since `llm.complete()` has no `output_config.format` parameter — see §4):**

```json
{
  "type": "object",
  "required": ["opener", "closer", "puzzle", "today_in_history",
               "question_of_the_week", "teaser_caption"],
  "properties": {
    "opener": {"type": "string", "minLength": 1},
    "closer": {"type": "string", "minLength": 1},
    "discovery_bridges": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["from_member", "to_member", "text"],
        "properties": {
          "from_member": {"type": "string"},
          "to_member": {"type": "string"},
          "text": {"type": "string", "minLength": 1}
        }
      }
    },
    "puzzle": {
      "type": "object",
      "required": ["intro", "question", "answer"],
      "properties": {
        "intro": {"type": "string", "minLength": 1},
        "question": {"type": "string", "minLength": 1},
        "answer": {"type": "string", "minLength": 1},
        "last_week_answer_reveal": {"type": "string"}
      }
    },
    "today_in_history": {
      "type": "object",
      "required": ["fact"],
      "properties": {
        "fact": {"type": "string", "minLength": 1},
        "family_idea_callout": {"type": "string"}
      }
    },
    "question_of_the_week": {
      "type": "object",
      "required": ["poll_question", "poll_options"],
      "properties": {
        "preamble": {"type": "string"},
        "poll_question": {"type": "string", "minLength": 1},
        "poll_options": {
          "type": "array",
          "minItems": 2,
          "maxItems": 6,
          "items": {"type": "string", "minLength": 1}
        }
      }
    },
    "teaser_caption": {"type": "string", "minLength": 1},
    "editors_choice": {
      "type": "object",
      "properties": {
        "ref": {"type": "string"},
        "note": {"type": "string"}
      }
    }
  }
}
```

### 2.3 System prompt — structure (outline; the builder writes the final prose)

**What to implement:** a module-level constant `EDITORIAL_SYSTEM_PROMPT: str`, fully static (no f-strings, no per-call interpolation — all dynamic content goes in the user prompt, §2.3b, so this string stays byte-identical across every call and is prompt-cacheable). Target length ~400–700 words: clear imperative prose organized under short headers, not a bare checklist dump. It must cover every point below; the exact sentences are this WP's to write, not prescribed verbatim (per task instruction — this section is documented, not fully written).

**Required content, in this order:**

1. **Persona framing.** The assistant is writing *as* Tzlil (`profiles/tzlil.md`: 13, gifted-math-track, dyslexic, "the family's scientist"), the newsletter's editor. Peer tone, never top-down — she "hates being talked down to, and as editor, no one will." State plainly that her real day-to-day participation is hoped-for but not yet live (`profiles/tzlil.md` §"החזון של אבא"; TRANSCRIPT_MINING: *"אני מקווה שהיא זו שבאמת תשתף פעולה"*) — this generation must stand on its own without depending on any input from her.
2. **The two voices**, quoting/paraphrasing STYLE_GUIDE §2 closely enough that the model treats them as fixed rules, not suggestions:
   - **Style A — "סימניה חם"**: short sentences (max 8–10 words), first names only, dinner-table warmth, no forced cleverness.
   - **Style B — "כלכליסט עובדתי"**: factual, precise, no hype, active voice, attributed when a source is named.
   - Include the field→voice assignment from §2.2's table (or close to it) so the model doesn't guess.
   - **Fold in the reasoning, not just the labels** (DESIGN_FISH §5, module scope point 4's explicit instruction): four voices were A/B-tested in April 2026 on identical content (Yedioth-tabloid, Geektime-casual, Calcalist-professional, Simaniia-warm); Simaniia won opener/closer for its warmth without try-hard cleverness, Calcalist won factual sections for clarity without dryness. State this briefly so the model internalizes *why*, which generalizes better than a bare rule.
3. **Editorial techniques ("assigned fish" — DESIGN_FISH §5, unconditionally required, not optional flourish):**
   - Every discovery bridge **must close** with a concrete, specific family-activity prompt — not a generic "maybe you'll like this too." Canonical example (quote once, then instruct the model to vary the phrasing across bridges/editions, never repeat this exact sentence): *"אולי רעיון לפרויקט משפחתי?"*
   - `today_in_history` must pair its factual core with a `family_idea_callout` — a short, concrete way the household could riff on the fact this week.
4. **Hard content guardrails** (LOD200 §5 cheap-validation checklist + `data/profile-raw/TRANSCRIPT_MINING_2026-07-22.md`, translated into generation-time instructions — enumerate all 8, this is the module-scope's "CONTENT SENSITIVITIES" requirement):
   1. Never reveal plot points for **מחזור שער המוות / Death Gate Cycle** or **Avatar: The Last Airbender** — reference only that someone is enjoying them, never events/outcomes within them.
   2. Never include political content, satire, or references to public figures/parties/news — if `research_highlights` contains anything political, ignore that item entirely rather than softening it.
   3. Never name or describe Yoyo's nail-art business as *hers* — no explicit consent signal reaches this module (see §1 Assumption 1's minimal `research_highlights` contract), so the safe default is: content about nail art / young entrepreneurship in general is fine, attributing the business to her by name is not.
   4. Shaked: no personal/private details, ever. Gender/identity themes are served only through the speculative-fiction lens he already loves, and are **never labeled** as being "about him" — content simply appears as excellent content that happens to be there.
   5. Michal: any mention is restorative, light, zero-effort in tone — "a cup of tea, not a newspaper" (`profiles/michal.md`). Never a task list, never demanding, never professional-content-as-work.
   6. The opener is warm but **never mentions health, medical topics, or any family member's recovery status** (including grandfather Rami's cardiac recovery) unless the family has explicitly supplied it as content — this is a blanket rule, not specific to one person.
   7. Extended family is **out of scope for `discovery_bridges`** — bridges connect only the 5 core members (`nimrod`, `michal`, `shaked`, `maayan`, `tzlil`); extended-family content is LOD200 §2 item 10, a separate section this module does not touch.
   8. Never fabricate a specific headline/article/event. When `research_highlights` has nothing for a member this week, fall back to their `MEMBER_TASTE_ANCHORS` entry (embedded in the user prompt, §2.3b) and keep any bridge/mention general rather than inventing a fake specific.
   - **Note the enforcement boundary explicitly (do not silently over-promise):** items 1–2 and 4–8 above are generation-time prompt instructions only — there is no reliable mechanical way to detect "contains a spoiler" or "is political" in code, and LOD200 §5's own checklist is framed as a manual, pre-send confirmation step, not an automated gate. Item 3 (Yoyo's business name) gets one extra, best-effort mechanical safety net — §2.6's `_scan_sensitive_terms` — precisely because a false negative there is the single most privacy-sensitive miss and a false positive costs nothing but a log line. This spec is honest about that asymmetry rather than pretending full automated coverage.
5. **Output format rules:** respond with **only** a single JSON object matching §2.2's schema — no prose before/after, no markdown code fences (the model should not need `llm.py`'s fence-stripping fallback, but that fallback exists as a safety net, not a license to rely on it), exact field names as given, plain text in every field except `opener`/`closer` (which may use bare `<strong>`/`<em>` only — no other tags, no markdown asterisks/underscores).
6. **Embed §2.2's schema** (the field table or the JSON Schema block) directly in the prompt text so the model has the literal shape, not just a prose description of it.

### 2.3b User prompt — `_build_user_prompt()`

**What to implement:**

```python
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
```

**Acceptance criteria:**
- [ ] AC-04: `EDITORIAL_SYSTEM_PROMPT` is a non-empty `str` module constant containing (case-insensitive) the substrings `"צליל"` and `"json"`, and containing no `"{"`/`"}"` Python format-placeholder artifacts (confirms it is fully static — no leftover `.format()`/f-string markers).
- [ ] AC-05: `_build_user_prompt(family, {"nimrod": ["מסלול קייטסינג חדש"]}, "42", "2026-07-24")` — the returned string contains the literal substring `"2026-07-24"`, contains `"מסלול קייטסינג חדש"`, contains `"42"`, and does **not** raise for any member missing from the highlights dict.
- [ ] AC-06: Same call but with `research_highlights=None` — every member's roster line falls back to `MEMBER_TASTE_ANCHORS[member.id]` (verify at least one anchor string appears verbatim in the output) and the function does not raise.
- [ ] AC-07: `prior_puzzle_answer=None` — the returned string does **not** contain the literal previous-answer-reveal instruction used in the truthy case; it contains the first-edition framing instruction instead (assert on a distinguishing substring present in one branch and not the other).
- [ ] AC-08: The returned string always contains the literal substring `"{EDITION_LINK}"` (the placeholder-token instruction to the model), regardless of other inputs.

### 2.4 Response validation — `_validate_editorial()`

**What to implement:**

```python
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
```

**Acceptance criteria:**
- [ ] AC-09: `_validate_editorial(<the §2.2 canonical example, with {EDITION_LINK} inserted into teaser_caption>)` returns `[]`.
- [ ] AC-10: Removing `opener` from the example → returned list contains an entry mentioning `"opener"`; same independently for `closer`, `puzzle` (whole key absent), `puzzle.intro`, `puzzle.question`, `puzzle.answer`, `today_in_history` (whole key absent), `today_in_history.fact`, `question_of_the_week` (whole key absent), `question_of_the_week.poll_question`, `teaser_caption` — each removal in isolation produces at least one error string, and removing an unrelated field does not.
- [ ] AC-11: `question_of_the_week.poll_options` as `["only one"]` (length 1) → error mentioning `poll_options`. As a list of 7 strings → error. As `["", "valid"]` (one empty string) → error. As a list of exactly 2 or exactly 6 non-empty strings → no `poll_options`-related error (boundary-inclusive).
- [ ] AC-12: `teaser_caption` present and non-empty but **not** containing `{EDITION_LINK}` → error mentioning the placeholder. `teaser_caption` containing it → no error.
- [ ] AC-13: `discovery_bridges` entirely absent from the input dict → `_validate_editorial` returns `[]` if every other required field is present (confirms bridges are NOT hard-required at this layer — §2.2's table).
- [ ] AC-14: A `puzzle` object missing `last_week_answer_reveal` → `_validate_editorial` reports **no** error for it (this field's requiredness is conditional on the caller's `prior_puzzle_answer` input, checked in §2.6/§2.7's normalization+entry-point layer, not here — this function only knows the schema, not the call's input context).

### 2.5 Retry-prompt builder — `_build_retry_prompt()`

**What to implement:**

```python
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
```

**Acceptance criteria:**
- [ ] AC-15: `_build_retry_prompt("ORIGINAL", ["opener: missing"])` returns a string containing both the literal substring `"ORIGINAL"` and the literal substring `"opener: missing"`.

### 2.6 Deterministic post-processing — `_normalize_editorial()` and `_scan_sensitive_terms()`

**What to implement:**

```python
_SENSITIVE_TERM_PAIRS = [
    (("יויו", "מעיין"), ("ציפורניים", "נייל", "nail")),
]


def _scan_sensitive_terms(data: dict) -> list[str]:
    """Best-effort, log-only heuristic for LOD200 §5 guardrail #3
    (Yoyo's business name) — see §2.3 point 4's note on the enforcement
    boundary. Never raises, never blocks; returns warning strings for
    the caller to log. Scans every string value in the dict (shallow +
    one level of nesting, matching this module's own schema shape)."""
    import itertools

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
    elif len(clean_bridges) < MIN_DISCOVERY_BRIDGES:
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
```

**Acceptance criteria:**
- [ ] AC-16: A `discovery_bridges` list with 5 valid entries → `_normalize_editorial(...)["discovery_bridges"]` has exactly 3 entries (the first 3, order-preserved), and a `logger.warning` call is observed.
- [ ] AC-17: A `discovery_bridges` list with exactly 1 valid entry → kept as-is (1 entry in the output), and a `logger.warning` call is observed (informational, not corrective — no truncation logic runs).
- [ ] AC-18: An entry with `from_member == to_member == "nimrod"` → dropped; an entry with `to_member == "unknown_id"` → dropped; both verified via a `logger.warning` call and the entry's absence from the output.
- [ ] AC-19: `prior_puzzle_answer="42"` and the input `puzzle` dict has no `last_week_answer_reveal` key → output's `puzzle["last_week_answer_reveal"]` contains the literal substring `"42"`. `prior_puzzle_answer=None` and no `last_week_answer_reveal` in input → output contains the literal first-edition fallback text (`"החידה הראשונה"` substring). Either case: if the LLM **did** supply `last_week_answer_reveal`, it is left untouched (fallback only fires on absence).
- [ ] AC-20: `today_in_history` with no `family_idea_callout` → output has the fallback string; `today_in_history` with one already present → left untouched.
- [ ] AC-21: `question_of_the_week.poll_options = ["a", "b", "a", "c"]` → output is `["a", "b", "c"]` (order-preserving dedupe).
- [ ] AC-22: `editors_choice` absent entirely, with 2 surviving bridges → output's `editors_choice["note"]` is non-empty and `editors_choice["ref"] == "bridge_1"`. `editors_choice` absent with 0 surviving bridges → output's `editors_choice["note"]` is still non-empty (the no-bridges fallback), `ref == ""`.
- [ ] AC-23: `result["editor_credit"] == "עורכת: צליל"` in every call, unconditionally — including when the input `data` dict already happened to contain an `editor_credit` key with a different value (this function's assignment always wins; it is not a fallback-if-missing like the other soft fields).
- [ ] AC-24: `_scan_sensitive_terms({"opener": "יויו עשתה עוד ציור ציפורניים מדהים היום"})` returns a non-empty list (both a name-term and a nails-term present). `_scan_sensitive_terms({"opener": "יויו הייתה בקרקס היום"})` returns `[]` (name present, no nails-term). Neither call raises or mutates its input.

### 2.7 Mock mode — `_mock_editorial()`

**What to implement:**

```python
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
                "last_week_answer_reveal": None,  # normalized below
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
                "poll_options": ["טירה ענקית", "עיר שלמה", "פארק שעשועים", "משהו מפתיע — תגיבו!"],
            },
            "teaser_caption": (
                "📰 בית ולד השבועי הגיע! מיינקראפט, קפוארה, וחידה "
                "שתשבור לכם את הראש מחכים לכם. הצביעו בסקר השבוע "
                f"וספרו לנו מה חשבתם 👇 {TEASER_LINK_PLACEHOLDER}"
            ),
            "editors_choice": {
                "ref": "bridge_1",
                "note": "בחירת העורכת: זה שאבא וגם אני חושבים כמו חוקרים, כל אחד בים שלו — פשוט מגניב. — צליל",
            },
        },
        family,
        prior_puzzle_answer,
    )
```

Note: the literal `"last_week_answer_reveal": None` placeholder above is intentional — it exercises `_normalize_editorial`'s fallback path (§2.6) inside the mock too, so mock output flows through the exact same normalization every real response does. `_normalize_editorial` overwrites it based on `prior_puzzle_answer`.

**Acceptance criteria:**
- [ ] AC-25: `_validate_editorial(_mock_editorial(family, None, None, "2026-07-24"))` returns `[]`.
- [ ] AC-26: Two calls to `_mock_editorial(family, None, None, "2026-07-24")` return equal (`==`) dicts (determinism — no timestamps, no randomness).
- [ ] AC-27: `_mock_editorial(family, {"nimrod": ["x"]}, "42", "2026-07-24")["puzzle"]["last_week_answer_reveal"]` contains the literal substring `"42"` (confirms the mock's `None` placeholder is correctly overwritten by `_normalize_editorial`, not left as `None`).
- [ ] AC-28: Calling `_mock_editorial(...)` makes zero calls into `llm.complete` — verified with `llm.complete` mocked/spied and asserted `call_count == 0`.

### 2.8 Public entry point — `generate_editorial()`

**What to implement:**

```python
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
```

**Acceptance criteria:**
- [ ] AC-29: `generate_editorial(family, None, None, "2026-07-24", settings, mock=True)` returns a dict for which `_validate_editorial(...) == []`, and `llm.complete` (mocked/spied) has `call_count == 0`.
- [ ] AC-30: Real path, `llm.complete` mocked to return a fully valid dict on its first call → `generate_editorial(...)` returns a normalized dict, and `llm.complete` was called exactly **once**, with `module="editor"`, `operation="editorial"`, `newsletter_date=today`, `expect_json=True`, and `max_tokens` equal to `settings.ai.get('editorial_max_tokens', DEFAULT_MAX_TOKENS)`.
- [ ] AC-31: `llm.complete` mocked to return an invalid dict (missing `opener`) on the first call and a fully valid dict on the second → `generate_editorial(...)` returns the normalized second dict; `llm.complete` was called exactly **twice**; the second call's `operation` argument equals `"editorial_schema_retry"`; the second call's `prompt`/first-positional-argument contains the literal error string produced for the missing `opener` field (i.e. traces back through `_build_retry_prompt`).
- [ ] AC-32: `llm.complete` mocked to return an invalid dict on **both** calls → `generate_editorial(...)` raises `EditorSchemaError`; `llm.complete` was called exactly **twice** (never a third time).
- [ ] AC-33: `llm.complete` mocked with `side_effect=llm.LLMAllDriversFailedError("boom")` → `generate_editorial(...)` raises `LLMAllDriversFailedError` (the exact exception instance/type from `llm.py`, not wrapped in `EditorError`/`EditorSchemaError`). Repeat for `LLMConfigError` and `LLMJsonError` — same propagate-unchanged behavior in each case.
- [ ] AC-34: `settings.ai = {"editorial_max_tokens": 4000}` → the `llm.complete` call (mocked/spied) is observed with `max_tokens=4000`. `settings.ai = {}` → observed with `max_tokens=2500` (the `DEFAULT_MAX_TOKENS` constant).

## 3. Data model changes (informational — see §1 Assumption 6: this WP does not edit `models.py`)

**No DDL, no migration.** `generate_editorial()` returns a plain `dict`; no new dataclass is added to `src/models.py` by this WP. The table below documents how this module's output *would* map onto the **existing** `GeneratedContent`/`NEO` dataclasses (`src/models.py`), for whichever future integration WP wires `editor.py` into the real pipeline (out of scope here — §6). This is documentation, not a binding contract this WP implements.

| This module's field | Existing `GeneratedContent`/`NEO` field | Notes |
|---|---|---|
| `opener` | `GeneratedContent.opener_text` | Direct match, same intent. |
| `closer` | `GeneratedContent.closer_text` | Direct match, same intent. |
| `puzzle.intro` + `puzzle.question` | `GeneratedContent.puzzle` (single `str`) | Old field was one blended string; new schema splits intro/question for rendering control. Integration WP decides final concatenation or a template-side split. |
| `puzzle.answer` | `GeneratedContent.puzzle_answer` | Direct match — **this week's** answer, persisted for next week's reveal, never rendered this week. |
| `today_in_history.fact` + `today_in_history.family_idea_callout` | `GeneratedContent.history` (single `str`) | Old field was one string; concatenation approach is the integration WP's call. |
| `question_of_the_week.preamble` + `.poll_question` | `GeneratedContent.survey_question` (single `str`) | Direct-ish; `.poll_options` has **no existing field** — a gap for the integration WP to close in `models.py`. |
| `discovery_bridges[]` | `GeneratedContent.bridges` (`list[dict]` with `from_member`/`to_member`/`nci_id`/`text`) | Shape is close, but **this module's bridges carry no `nci_id`** — they are not tied to a specific curated `NCI` item (architecture shift per REVIVAL_PLAN §3: bridges are now generated from `research_highlights`, not scored/curated content items). Integration WP must decide whether `nci_id` becomes optional/nullable or is dropped. |
| `teaser_caption` | *(none)* | New field; consumed directly by a future `publisher.py`/`whatsapp.py`/`teaser.py` (WP005, out of scope), not by `GeneratedContent`. |
| `editors_choice` | *(none)* | New field; likely rendered in the footer/opener area near the editor credit — template concern (WP007, out of scope). |
| `editor_credit` | *(none)* | New, static per §1 Assumption 5; likely a template constant that could instead read this field once wired — integration WP's call. |
| `GeneratedContent.greeting` | *(not produced by this module)* | Flagged for the integration WP: the OLD `greeting` field's role (a short standalone hello) looks superseded by the NEW architecture's richer `opener`, but this WP does not decide that — noted, not resolved. |

## 4. API contract changes

No HTTP endpoints (batch/cron pipeline). The contract is `editor.py`'s public Python surface, plus the `settings.json → ai` key it reads.

| Symbol | Kind | Signature / Shape | Notes |
|---|---|---|---|
| `generate_editorial` | function | `generate_editorial(family: FamilyConfig, research_highlights: Optional[dict[str, list[str]]], prior_puzzle_answer: Optional[str], today: str, settings: Settings, *, mock: bool = False) -> dict` | THE public entry point. §2.8. |
| `EditorError` | exception | `class EditorError(Exception)` | Base class. |
| `EditorSchemaError` | exception | `class EditorSchemaError(EditorError)` | Raised only after the one schema retry still fails validation. |
| `MODULE_NAME`, `OPERATION_EDITORIAL`, `OPERATION_EDITORIAL_RETRY` | constants | `str` | Passed to `llm.complete(module=..., operation=...)`. |
| `TEASER_LINK_PLACEHOLDER` | constant | `str` = `"{EDITION_LINK}"` | §1 Assumption 7 — future publisher WP replaces this literal substring with the real URL. |
| `EDITOR_CREDIT` | constant | `str` = `"עורכת: צליל"` | §1 Assumption 5. |

### `settings.json` — new `ai.*` key read by `generate_editorial()`

| Key | Type | Default (if key absent) | Meaning |
|---|---|---|---|
| `ai.editorial_max_tokens` | int | `2500` | `max_tokens` passed to `llm.complete()` for the editorial call. §1 Assumption 8. |

**This WP does NOT edit `config/settings.json`** — `generate_editorial()` reads via `settings.ai.get('editorial_max_tokens', DEFAULT_MAX_TOKENS)`, so it behaves correctly with or without the literal key present, mirroring WP001's identical approach to its own new `ai.*` keys.

### The structured-output JSON schema

See §2.2 in full (field table, canonical example, and the validation JSON Schema block). This is the complete contract `_validate_editorial()` implements and `EDITORIAL_SYSTEM_PROMPT` must communicate to the model.

### `llm.complete()` call shape (both calls this module ever makes)

```
llm.complete(
    <prompt>,
    system=EDITORIAL_SYSTEM_PROMPT,
    max_tokens=<settings.ai.get('editorial_max_tokens', 2500)>,
    module="editor",
    operation="editorial" | "editorial_schema_retry",
    newsletter_date=<today>,
    expect_json=True,
)
```

No `tools` argument is ever passed (defaults to `None` — this module never triggers `llm.complete()`'s `NotImplementedError` guard for `tools`, per module scope point 1: "NO tools").

## 5. Error handling requirements

| Error case | Expected behavior |
|---|---|
| `llm.complete()` raises `LLMConfigError` (e.g. `llm.configure()` never called) | Propagates unchanged out of `generate_editorial()` — NOT caught, NOT wrapped (AC-33). This is an infrastructure/setup failure, not this module's concern. |
| `llm.complete()` raises `LLMAllDriversFailedError` (every configured driver failed) | Propagates unchanged (AC-33). |
| `llm.complete()` raises `LLMJsonError` (not parseable as JSON even after `llm.py`'s own one JSON-syntax retry) | Propagates unchanged (AC-33) — this module's own schema-retry (§2.8) never runs in this case, because there is no `raw` dict to validate; `llm.complete()` already exhausted its retry budget on pure JSON syntax. |
| `llm.complete()` returns a syntactically-valid JSON dict missing/malformed required fields (§2.2 hard-required list) | `_validate_editorial()` returns non-empty errors → `generate_editorial()` retries **once** with `_build_retry_prompt()` (operation `editorial_schema_retry`) (AC-31). |
| The schema retry (previous row) **also** fails validation | `EditorSchemaError` raised, listing the remaining validation errors (AC-32). No further retry — bounded to exactly 2 total `llm.complete()` calls per `generate_editorial()` invocation. |
| `discovery_bridges` missing entirely, or has fewer than `MIN_DISCOVERY_BRIDGES` / more than `MAX_DISCOVERY_BRIDGES` entries | **Not a validation error** (§2.2, §2.4 AC-13) — a soft field. `_normalize_editorial()` truncates excess (AC-16) or logs-and-keeps a shortfall (AC-17); `generate_editorial()` never retries or raises over bridge count alone. |
| A `discovery_bridges` entry references an unknown member id, or `from_member == to_member` | Silently dropped by `_normalize_editorial()` with a `logger.warning` (AC-18) — not a validation error, no retry. |
| `puzzle.last_week_answer_reveal` missing | Not a validation error (AC-14). `_normalize_editorial()` fills a deterministic fallback conditioned on whether `prior_puzzle_answer` was supplied (AC-19). |
| `today_in_history.family_idea_callout` missing | Not a validation error. `_normalize_editorial()` fills a static fallback string (AC-20). |
| `editors_choice` missing or malformed | Not a validation error. `_normalize_editorial()` synthesizes a generic fallback from the first surviving bridge, or a static generic note if there are no bridges (AC-22). |
| Output text mentions Yoyo (`"יויו"`/`"מעיין"`) alongside a nail-art term (LOD200 §5 guardrail #3) | Best-effort, log-only: `_scan_sensitive_terms()` returns a warning string, logged via `logger.warning` in `_normalize_editorial()` — never blocks, never raises (AC-24; §2.3 point 4's documented enforcement-boundary note). |
| Spoiler content, political content, or the other LOD200 §5 guardrails not listed above | **No automated detection in this module** — prompt-level instruction only (§2.3 point 4), backstopped by LOD200 §5's manual pre-send checklist (a process step, out of scope for this WP's code). Documented, not silently assumed covered. |
| `mock=True` | `_mock_editorial()` returns deterministic, schema-valid content; zero calls into `llm.complete()` (AC-28, AC-29) — see §1 Assumption 4 for why this must never fall through to the real path even partially. |

## 6. Out of scope (explicit)

- **`researcher.py` / item selection / `research_highlights`'s real shape** — WP003, not yet spec'd at LOD400 at authoring time. This WP defines only the minimal provisional input contract it needs (§1 Assumption 1, §2.3b) and is not blocked on WP003 landing.
- **Rendering the editorial content into the newsletter HTML** — WP007 (template extension). This WP returns a `dict`; turning it into markup, applying `|safe`, choosing where `editors_choice`/`editor_credit` visually sit, is WP007's job.
- **The teaser *image*** — WP005 (`teaser.py`). This WP produces only `teaser_caption` (text). The image itself, and combining image+caption+link into an actual WAHA send, are WP005/`publisher.py`'s job.
- **Sending the WhatsApp poll as a native WAHA poll message** — LOD200 §7 explicitly defers this to Phase C. This WP only shapes `question_of_the_week.poll_question`/`poll_options` as data (§1 Assumption 2).
- **`researcher.py`'s "שולחן שישי" (family-table) item and its own open question** (LOD200 §2 item 8) — a different, WP003-owned section with its own open question, not this module's `question_of_the_week` poll. See §1's "Section mapping" note.
- **Persisting `puzzle.answer` for next week's reveal, or reading it back as next week's `prior_puzzle_answer`** — orchestrator/DB concern. `generate_editorial()` is a pure function with respect to persistence; it takes `prior_puzzle_answer` as an input and returns this week's `puzzle.answer` as output, and does no I/O itself.
- **Editing `src/models.py`, `src/token_tracker.py`, `src/orchestrator.py`, or `config/settings.json`** — §1 Assumptions 3 and 6; §3 and §4's tables are documentation for whichever future WP performs those edits.
- **Tzlil's live participation loop** (Phase B: she sends items mid-week, rates puzzle difficulty, gets a Thursday-evening preview to approve/edit) — REVIVAL_PLAN §3.5.3, module scope point 5. This WP generates content **in her voice**, unconditionally, without any live input channel from her.
- **Automated detection of spoilers, political content, or the other LOD200 §5 guardrails beyond the one best-effort Yoyo's-business-name heuristic** — §5's explicit note. Prompt-level instruction + LOD200 §5's manual pre-send checklist are the only safety nets; this WP does not attempt to build a content-moderation system.
- **A CLI entry point / `if __name__ == "__main__":` block for `editor.py`** — not requested; `mock` flows in as a plain function parameter from the orchestrator's existing `--mock` flag (`args.mock`), matching `TokenTracker(db, mock=args.mock)`'s established pattern. No standalone invocation is defined by this spec.
- **Any change to `m3_normalizer.py` or its eventual archival** — REVIVAL_PLAN's keep/archive table assigns that move elsewhere; this WP only draws on its functions as shape/intent precedent (§1).

## 7. Test requirements

- **Unit** (no real API calls — mock `llm.complete`): every AC in §2.1–§2.8 above. Priority/highest-risk targets: the mock-vs-real short-circuit (AC-28, AC-29 — the single most important behavior in this WP, per §1 Assumption 4's cost-of-getting-it-wrong), the bounded schema-retry (AC-31, AC-32 — must never exceed 2 total `llm.complete()` calls), and the `LLMError` propagate-unchanged contract (AC-33). Illustrative skeleton (pytest + pytest-mock, matching WP001's established test-stack convention):

```python
def test_generate_editorial_mock_never_calls_llm(mocker):
    from src import editor
    from src.models import FamilyConfig
    complete_spy = mocker.patch("src.editor.llm.complete")
    family = FamilyConfig(family_name="בית ולד", family_name_en="Beit Vald",
                           shared_interests={}, members=[])
    settings = mocker.Mock(ai={})

    result = editor.generate_editorial(family, None, None, "2026-07-24", settings, mock=True)

    assert editor._validate_editorial(result) == []
    complete_spy.assert_not_called()


def test_generate_editorial_retries_once_on_schema_failure(mocker):
    from src import editor
    from src.models import FamilyConfig
    family = FamilyConfig(family_name="בית ולד", family_name_en="Beit Vald",
                           shared_interests={}, members=[])
    settings = mocker.Mock(ai={})
    invalid = {"closer": "x"}  # missing opener, puzzle, today_in_history, etc.
    valid = editor._mock_editorial(family, None, None, "2026-07-24")
    complete_mock = mocker.patch("src.editor.llm.complete", side_effect=[invalid, valid])

    result = editor.generate_editorial(family, None, None, "2026-07-24", settings, mock=False)

    assert complete_mock.call_count == 2
    assert complete_mock.call_args_list[1].kwargs["operation"] == "editorial_schema_retry"
    assert result["opener"] == valid["opener"]


def test_generate_editorial_raises_editor_schema_error_after_failed_retry(mocker):
    from src import editor
    from src.models import FamilyConfig
    family = FamilyConfig(family_name="בית ולד", family_name_en="Beit Vald",
                           shared_interests={}, members=[])
    settings = mocker.Mock(ai={})
    invalid = {"closer": "x"}
    complete_mock = mocker.patch("src.editor.llm.complete", side_effect=[invalid, invalid])

    with pytest.raises(editor.EditorSchemaError):
        editor.generate_editorial(family, None, None, "2026-07-24", settings, mock=False)
    assert complete_mock.call_count == 2


def test_generate_editorial_propagates_llm_errors_unchanged(mocker):
    from src import editor, llm
    from src.models import FamilyConfig
    family = FamilyConfig(family_name="בית ולד", family_name_en="Beit Vald",
                           shared_interests={}, members=[])
    settings = mocker.Mock(ai={})
    mocker.patch("src.editor.llm.complete", side_effect=llm.LLMAllDriversFailedError("boom"))

    with pytest.raises(llm.LLMAllDriversFailedError):
        editor.generate_editorial(family, None, None, "2026-07-24", settings, mock=False)
```

- **Integration** (opt-in, real cost — do not run in default CI given LOD200 §6's `$2.50/wk` cost_cap): one live call via `generate_editorial(<a real FamilyConfig loaded from config/family.json>, None, None, "<today>", <real Settings>, mock=False)` with a real `ANTHROPIC_API_KEY`, gated behind `RUN_LIVE_LLM_TESTS=1` (matching WP001 §7's identical convention) — assert `_validate_editorial()` on the result is `[]`, and manually eyeball the output once against LOD200 §5's checklist (no automated check exists for most of it — §5, §6).

- **Cross-engine validation** (required at L-GATE_VALIDATE per Iron Rule #1 — the validator engine must differ from the builder engine): see Appendix A below for the standalone checklist.

## 8. Consuming team sign-off
> I confirm this spec is executable and unambiguous. All open questions are resolved.
> **Signature:** familynewsletter_build | [PENDING — sign at L-GATE_SPEC]

---

## Appendix A — Cross-Engine Validation Checklist

A standalone checklist for the validating engine (must differ from the building engine — Iron Rule #1: *"No team is the sole validator of its own output"*; per REVIVAL_PLAN §3.7, Grok/Cursor builds, Claude/Sonnet validates):

1. `src/editor.py` exports exactly `generate_editorial`, `EditorError`, `EditorSchemaError` as its intended public surface (private helpers prefixed `_` are implementation detail, not part of the contract).
2. `generate_editorial(..., mock=True)` makes **zero** calls into `llm.complete` under any input combination, including `research_highlights=None` and `prior_puzzle_answer=None` (edition-1's exact real-world condition) — confirm by grepping the mock branch for any code path that could reach `llm.complete(` before the `if mock: return ...` short-circuit.
3. `EDITORIAL_SYSTEM_PROMPT` is confirmed fully static — no f-string/`.format()`/`%`-interpolation of any per-call variable. All dynamic content (dates, member roster, research highlights, prior puzzle answer) enters only through `_build_user_prompt()`'s return value, never the system prompt.
4. Confirm `generate_editorial()` never passes `tools=` to `llm.complete()` (module scope point 1: "NO tools" — a regression here would silently trigger `llm.complete()`'s `NotImplementedError` guard from WP001 §2.2, not a graceful failure).
5. Confirm the schema-retry loop is hard-bounded to exactly 2 total `llm.complete()` calls per `generate_editorial()` invocation under every failure combination (both calls invalid, first invalid then second valid, first valid) — no code path can reach a 3rd call.
6. Confirm every one of LOD200 §5's 7 checklist items has *either* an explicit generation-time instruction in `EDITORIAL_SYSTEM_PROMPT` (per §2.3 point 4's 8-item guardrail list) *or* an explicit, honest "not automatable, prompt-only" note in this document (§5, §6) — no guardrail should be silently missing from both the prompt and the documentation.
7. Confirm `TEASER_LINK_PLACEHOLDER` (`"{EDITION_LINK}"`) is validated as a hard requirement (`_validate_editorial`, AC-12) — a build that lets a teaser ship without a replaceable link placeholder is a real, embarrassing failure mode (a WhatsApp message with no way to reach the edition).
8. Confirm `editor_credit` is set unconditionally by Python code in `_normalize_editorial()`, never requested from or sourced out of the LLM's JSON response (§1 Assumption 5, AC-23) — grep `EDITORIAL_SYSTEM_PROMPT`'s content for the literal credit string; it should not instruct the model to produce this field.
9. Confirm `git diff` for this WP touches only `src/editor.py` (plus test files, if added) — no incidental edits to `llm.py`, `token_tracker.py`, `models.py`, `db.py`, `config/settings.json`, or `orchestrator.py` (§1 Assumptions 3/6, §6).

---

## Cross-Engine Validation — Iron Rule

Documents at LOD400+ require cross-engine validation at L-GATE_VALIDATE.
**The validator engine MUST differ from the builder engine — IRON RULE.**
No exception. No waiver. See `gates/L-GATE_VALIDATE_VALIDATE_AND_LOCK.md`.
