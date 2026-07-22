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

# orchestrator Rewire + publisher.py — Pipeline Integrator (Publish Flow, WAHA Hook, Legacy Archive, Section-Ownership Resolution) — LOD400 Implementation Spec

**work_package_id:** FNL-S001-P002-WP006
**parent_lod200:** _aos/work_packages/FNL-S001-P001-WP001/LOD200.md
**parent_lod300:** N/A — Track A only
**approved_by:** [PENDING — familynewsletter_build sign-off at L-GATE_SPEC]
**approved_at:** [PENDING]

## 1. Scope reminder

This WP is **the integrator** — it is the only WP that touches the pipeline's *seams*. It does three things: **(A)** creates **`src/publisher.py`** (new) from `src/m5_distributor.py`, keeping FTP upload + email delivery, deleting all Twilio/WhatsApp-direct-send code, and leaving WhatsApp delivery as an explicit, self-activating **HOOK** for `src/whatsapp.py` (built by `FNL-S001-P003-WP001`, OPS — not this WP). **(B)** rewires **`src/orchestrator.py`** — same 4 CLI verbs, same `run.sh`/cron — to call the six sibling modules already spec'd (`llm.py` WP001, `token_tracker.py` WP002, `researcher.py` WP003, `editor.py` WP004, `teaser.py` WP005, and the template extension WP007) in the correct sequence, with the zero-token assembly steps (weather, Hebrew date, NEO construction) that glue their outputs together. **(C)** executes **`FNL-S001-P001-WP003`'s deferred archival** — `git mv` of `src/m2_scanner.py`, `src/m3_normalizer.py`, `src/m6_feedback.py`, `config/sources.json` (plus, as this WP's own necessary addition, `src/m5_distributor.py` itself — see Assumption 10) into `archive/legacy/` — **after** extracting the three salvage shapes (`_fetch_weather`, `_format_hebrew_date`, the `_build_neo` dict shapes) into the orchestrator, per roadmap.yaml's WP006 note (quoted below). **(D)** produces the explicit content→section ownership map across all 13 LOD200 §2 sections, and — where no sibling WP's §2 actually implements a section LOD200 marks MUST-contain — **resolves what can be resolved by wiring alone, and explicitly flags the rest** as an open reconciliation item for team_00 (§1 below + §6), rather than inventing unbudgeted content-generation scope.

**Design sources (quoted verbatim, read in full before implementing):**

> **REVIVAL_PLAN_2026-07-22.md §3, keep/replace table:**
> `src/m5_distributor.py` | **שמור FTP+מייל → `publisher.py`** | למחוק את כל קוד Twilio
> `src/orchestrator.py` | **חיווט מחדש** | אותו CLI (weekly-build / weekly-send / health-check) — run.sh וה-cron לא משתנים
> `poc.py`, `src/m2_scanner.py`, `src/m3_normalizer.py`, `src/m6_feedback.py`, `config/sources.json` | **ארכיון** → `archive/legacy/` | מ-m3 מחלצים 3 דברים: `_fetch_weather`, `_format_hebrew_date`, וצורות ה-dict של `_build_neo` (חוזה התבנית)

> **`_aos/roadmap.yaml`, `FNL-S001-P002-WP006` notes field (verbatim, read 2026-07-22):**
> "CLASS=STANDARD. Edits kept code (orchestrator, m5) -> LOD400 required. **ABSORBS WP003 deferral**: archive m2_scanner/m3_normalizer/m6_feedback + config/sources.json to archive/legacy/ and extract `_fetch_weather`/`_format_hebrew_date`/`_build_neo` shapes from m3 during the rewire."

> **LOD200 §3, happy-path acceptance (why §1's section-ownership gap below is not a minor nit):**
> "- [ ] All 13 sections present; all 5 members have ≥1 item; puzzle present"

This WP has a **hard, direct dependency on all six sibling WPs' public interfaces** (WP001 `llm.py`, WP002 `token_tracker.py`, WP003 `researcher.py`, WP004 `editor.py`, WP005 `teaser.py`, WP007 template extension + `m4_renderer.render()`'s new `settings=` param) — every call site in §2 below is written against those specs' **exact, cited** signatures, not guesses. Where a sibling spec's own document flags an unresolved question that blocks a concrete integration decision (e.g. WP004 §3's "`GeneratedContent.greeting`... not resolved"), **this WP is where that decision finally gets made** — see the Assumptions below.

### Assumptions (where wiring choices had to be made, or a real cross-WP gap was found — flag these at L-GATE_VALIDATE if wrong)

1. **`llm.configure(db, settings.ai, mock=args.mock)` must be called once, early in `cmd_weekly_build`, before `editor.generate_editorial()` is ever invoked.** `editor.py` calls `llm.complete()` (WP004 §2.8), and `llm.complete()` raises `LLMConfigError` immediately if `llm.configure()` was never called (WP001 §2.2 AC-05). No sibling spec calls `configure()` itself — WP001 §1 Assumption 3 explicitly designed it as "one `configure()` call the orchestrator makes once per process," and WP004 assumes it has already happened. This is the single easiest cross-WP wiring step for a corner-cutting builder to forget, since skipping it produces no import-time error — only a runtime crash on the *first* editorial call, after 5 members' worth of paid research calls have already run. `researcher.py` needs no equivalent call (WP003 §1 Assumption 2: it calls `tt.research()` directly, never `llm.complete()`).
2. **The Family-Table (LOD200 §2 item 8, "🍽️ שולחן שישי") and Extended-Family (item 10, "👨‍👩‍👧 מהמשפחה המורחבת") sections have NO producer anywhere in WP001–WP005+WP007, and this is a real, cross-referenced mutual-deferral, not a hypothetical.** Quoted verbatim:
   - **WP003 (`researcher.py`) §6, Out of scope:** *"Editorial writing — headline/summary polish, discovery-bridge text, opener/closer, the '🍽️ שולחן שישי / Family Table' section, and the '👨‍👩‍👧 מהמשפחה המורחבת / Extended Family' section — **WP004** (`editor.py`)."*
   - **WP004 (`editor.py`) §1, Scope reminder:** *"LOD200 §2 item 8 ('שולחן שישי' / family-table conversation-starter) is explicitly **NOT this module's output**. It is a researched, selected item... belonging to **WP003** (`researcher.py`)"* — and separately, **§2.3 point 4, guardrail 7:** *"Extended family is out of scope for `discovery_bridges`... extended-family content is LOD200 §2 item 10, **a separate section this module does not touch**."*

   Each WP points at the other for Family-Table; neither WP claims Extended-Family at all. Neither WP's **§2 technical specification** (the only normative part of a LOD400 spec) contains any code, prompt, or function that produces either section's content. WP007 (the template, itself DRAFT, not yet built) independently confirms the gap from the render side — its §2.1 point 1 coordination note: *"no WP is currently chartered to actually populate `viewing`/`family_table_text`/`extended_family`/`shelf_pick`... until it lands, these 4 fields stay at their dataclass defaults... every section simply does not render — no error, no empty section, by construction."* **Resolution adopted by this WP** (full detail, priority, and recommended follow-up in §2.14 and §6): this WP wires `neo.metadata['family_table_text'] = ''`, `['extended_family'] = []` (both template-safe, section-suppressing defaults — matching WP007's own designed-in graceful degradation) and does **not** invent editorial content or curation logic for either, since that would silently manufacture unbudgeted, unreviewed scope inside an *integrator* WP whose own mandate (per the task brief) is wiring, not content generation. **This is flagged as an OPEN RECONCILIATION ITEM for team_00** — as currently spec'd, **edition-1 cannot satisfy LOD200 §3's "All 13 sections present" happy-path criterion** for items 8 and 10 without a follow-up WP (a small, ~15-line addition to `editor.py`'s existing single structured call is the recommended fix for item 8; a small `profiles/extended-family.md`-reading curation function *plus* a content-readiness check is recommended for item 10 — see §2.14).
   - **The bonus 14th section WP007 adds beyond LOD200's 13** — "📚 מהמדף שלנו / From Our Shelf" (`neo.metadata['shelf_pick']`) — has the identical no-producer gap (WP007 §2.5 AC-41 explicitly: content-selection is *"out of scope here"*), but since it is **not** one of LOD200's 13 MUST-contain sections (WP007 §1 calls it explicitly *"additive... not one of LOD200's 13"*), it is lower priority — this WP wires it to `{}` and recommends deferral to Phase B/C, not an urgent pre-edition-1 fix. See §2.14.
3. **`editor.py`'s `puzzle.answer` and `puzzle.last_week_answer_reveal` fields are semantically distinct, and the template's ONE rendered slot (`neo.trivia['answer']`) must receive the *reveal*, never the current secret — this corrects a latent bug in the pipeline being replaced.** The template (`templates/newsletter.html.j2`, read verbatim, unchanged by WP007 except its mascot span) renders `neo.trivia['answer']` labeled **"תשובה מהשבוע שעבר"** ("last week's answer") — but the *old* `m3_normalizer.py._generate_puzzle()` set `trivia['answer'] = generated.puzzle_answer`, which was **this week's own just-generated secret answer**, displayed under a "last week's answer" label in the *same* edition that poses the puzzle — an immediate self-spoil. (Independently confirmed in memory `family-newsletter-engine-env-canon` / `TRANSCRIPT_MINING_2026-07-22.md`: *"Old template hardcoded 'last week's answer = 42' placeholder, never cycled."*) `editor.py` (WP004 §2.2) correctly separates these: `puzzle.answer` = this week's secret (never rendered this week), `puzzle.last_week_answer_reveal` = a full, warm, already-worded reveal sentence for what was asked *last* week. This WP's `_build_neo` (§2.10) therefore maps `trivia['answer'] = editorial['puzzle']['last_week_answer_reveal']` (the reveal, rendered) and separately **persists** `editorial['puzzle']['answer']` (this week's raw secret) into `newsletters.puzzle_answer` for next week's lookup (§2.11) — **never the reverse.** **Known, accepted cosmetic residue:** the template's hardcoded label prefix ("תשובה מהשבוע שעבר: ") will sit directly in front of `last_week_answer_reveal`'s own already-worded sentence (e.g. "תשובת השבוע שעבר הייתה 6!"), producing mildly redundant but still correct and readable phrasing ("תשובה מהשבוע שעבר: תשובת השבוע שעבר הייתה 6!"). Not fixed here (would require editing WP007's template, out of this WP's file scope) — flagged in §5/§6 with a one-line recommended future template fix.
4. **`prior_puzzle_answer` (fed into `editor.generate_editorial()`, WP004's own input contract) must be read from the DB *before* `db.create_newsletter(today, 'building')` is called for today**, or a same-day re-run (e.g. after a transient failure) would read *today's own* (still-`building`, likely-null) row via `db.get_last_newsletter()` instead of last week's completed row. `db.py` has no `get_newsletter_before(date)` method and this WP does not add one (not in this WP's file scope — see §6): the safe, zero-schema-change fix is purely a **call-ordering** guarantee in `cmd_weekly_build` (§2.11) — fetch `prior_row = db.get_last_newsletter()` and check `prior_row['date'] != today` **first**, before `create_newsletter`. On the rare same-day-re-run edge case where this guard trips, `prior_puzzle_answer` degrades to `None`, which `editor.py` already handles gracefully as "first edition" framing (WP004 §2.3b) — a one-run loss of the reveal line, not a crash.
5. **A new adapter, `_map_viewing()`, is required and owned by this WP** to bridge `researcher.screen_scout()`'s real return shape (WP003 §2.14: `{family_pick, personal_pick, personal_pick_member_id}`, each pick a rich dict with `hebrew_subtitles_verified`/`availability_verified`/`service`/`share_note`/etc.) onto `neo.metadata['viewing']`'s template contract as defined by WP007 §2.3/§3 (`{family_pick: {title, platform, hebrew_subs, available_il, note}, personal_pick: {member_id, title, platform, hebrew_subs, available_il, note}}`). **Neither WP003 nor WP007 defines this mapping** — WP007 §3 lists `viewing` among the fields it marks *"not yet chartered"* to be populated, written before WP003's real `screen_scout()` output shape existed to check against. Unlike Family-Table/Extended-Family (Assumption 2), this gap is **fully closeable by wiring alone** (a pure key-rename/reshape, no editorial judgment required) — see §2.9.
6. **A new adapter, `_map_discovery_bridges()`, is required and owned by this WP** to bridge `editor.py`'s abstract bridges (WP004 §2.2: `{from_member, to_member, text}` — no item reference at all) onto the **unchanged** Discovery template block's actual requirements. Direct read of `templates/newsletter.html.j2` (lines 731–744, untouched by WP007) confirms `{% for item in neo.discovery %}` requires **`item.bridge_text`, `item.title`, `item.url`, and optionally `item.summary`** — i.e. each bridge must resolve to a real, clickable item, which `editor.py`'s bridges structurally cannot provide (WP004 §3 itself flags this: *"this module's bridges carry no `nci_id`... Integration WP must decide whether `nci_id` becomes optional/nullable or is dropped"* — this is that decision). **Resolution:** each bridge is anchored to its `from_member`'s own top-ranked researched item (`research_results[from_member][0]`) — the *same* item already shown in that member's Personal Corner, re-referenced (not re-selected) as the bridge's clickable target, which is exactly what "a bridge points at a concrete thing" means. See §2.9.
7. **`NEO.greeting` is set to a short, plain-text derivation of `editor.py`'s `opener` field — not the full opener HTML verbatim — because it has two real consumers with tight, incompatible constraints.** WP004 §3 itself left this explicitly unresolved: *"the OLD `greeting` field's role... looks superseded by the NEW architecture's richer `opener`, but this WP does not decide that — noted, not resolved."* This WP decides it: `neo.greeting` feeds **(a)** the template's cover mascot-bubble (any string renders, no constraint) and **(b)** `teaser.py`'s small speech bubble (WP005 §2.6/§2.8: max 3 wrapped lines, ~612×240px, plain text — no HTML tags) and the per-member email's opening line (`publisher._build_message`). Passing `editor.py`'s full, multi-sentence, `<strong>`/`<em>`-tagged `opener` into the teaser bubble would either overflow-truncate mid-sentence or literally draw `<strong>` as visible characters (Pillow does not parse HTML). `_short_greeting()` (§2.9) strips the two permitted tags, takes the first sentence (or a hard truncation with an ellipsis) up to 160 characters, and is used for **both** consumers — a short greeting in an email is acceptable (arguably nicer than duplicating the full opener already visible in the linked HTML edition).
8. **`m4_renderer.render()`'s internal `edition_number` computation is not changed, and `teaser.py`'s independent `edition_number` argument is obtained by duplicating that exact query** (`SELECT COUNT(*) FROM newsletters WHERE status != 'build_failed'`) once in `orchestrator.py`, per WP005 §1 Assumption 8's own requirement ("the orchestrator computes it once... and passes the identical value to both"). This is **safe by construction, not a race condition**: within one synchronous `cmd_weekly_build` run, no `newsletters` row is inserted between `render()`'s internal query and this WP's duplicate query for `teaser.generate_teaser()` — both necessarily see the same table state. Changing `render()`'s signature to accept/return `edition_number` was considered and rejected: `m4_renderer.py` is BACKFILL/kept code (REVIVAL_PLAN §3: "שמור") outside this WP's file scope (§6), and WP007 (which *does* edit `m4_renderer.py`, for `og_image_url`/`settings=`) does not touch this either — duplicating one cheap `COUNT(*)` query is far cheaper than opening a second WP's file scope for a one-line signature change.
9. **Budget-cap breach (LOD200 §6) and teaser-generation failure both escalate via a concrete, testable mechanism: a plain-text admin email**, sent through the *same* SMTP primitives `publisher.py` already owns for member delivery (`env_compat.smtp_config`/`smtp_deliver_message`) — not a bare log line. LOD200 §6 states "no silent continue — escalate to team_00"; a `logger.warning()` line on a headless cron server that nobody tails is not, in practice, an escalation. `publisher.escalate_admin_alert(subject, body, family, settings, mock)` (§2.5) resolves the recipient via a new, optional `settings.distribution.admin_email` key, falling back to the `nimrod` member's `family.json` email if unset — no new required config. **A budget breach or teaser failure does NOT abort `weekly-build` or block `weekly-send`** — by the time either is detected, the cost is already spent (aborting doesn't refund it) or the HTML edition itself (the primary deliverable) is unaffected; withholding a good-enough edition over a graphic-generation failure or an after-the-fact cost alert contradicts LOD200 §1's "completeness... ~70% on-target is ACCEPTED" philosophy. This is an escalation, not a circuit breaker.
10. **`src/m5_distributor.py` is archived to `archive/legacy/`, alongside the four files roadmap.yaml's WP006 note names, as this WP's own necessary addition (a 5th file).** The roadmap note's explicit archive list is `m2_scanner.py`, `m3_normalizer.py`, `m6_feedback.py`, `config/sources.json` — it does not mention `m5_distributor.py`, because that file's disposition falls under module scope item **A**, not the WP003-deferral item **B**. But leaving `src/m5_distributor.py` in place once `src/publisher.py` fully supersedes it (REVIVAL_PLAN §3: "שמור FTP+מייל → `publisher.py`" — kept-and-renamed, not kept-alongside) would leave a confusing, orphaned duplicate with overlapping FTP/email logic and zero remaining callers. It is archived in the same `git mv` step, for the same "historical reference, not live code" reason as the other four — see §2.13.
11. **The `webhook` CLI verb and `cmd_webhook()` are removed entirely (not one of the "same 4 verbs" — `weekly-build`/`weekly-send`/`weekly-survey`/`health-check` — the task brief names), because its sole implementation (`m6_feedback.run_webhook_server`) is archived, and REVIVAL_PLAN's own Phase B design explicitly replaces a persistent webhook server with cron-time polling.** Quoted: REVIVAL_PLAN §4 Phase B: *"polling בזמן הבנייה (שישי 08:45)... `inbox.py` (~150 שורות). **בלי webhook, בלי תהליך רץ תמידית**"* ("without webhook, without an always-running process"). Removing the `webhook` verb is therefore not incidental cleanup forced by the archival — it is the architecturally correct direction Phase B already committed to; keeping a broken verb that imports an archived module would be strictly worse. The `daily-build`/`daily-send`/`daily-survey` backward-compat aliases (which map onto the 3 real verbs, unrelated to `m6_feedback`) are kept unchanged. **`weekly-survey` is kept** (module scope explicitly names it as one of the unchanged verbs) but is demoted to a manually-triggered, email-only utility — see §2.6's `publisher.send_survey()` docstring — since REVIVAL_PLAN §3/§4's crontab lists only 09:00 build / 12:00 send (no 21:00 survey slot in the new design); the survey question itself now ships embedded in the edition via `question_of_the_week`.
12. **`neo.family_content = []` and `newsletters.submissions_count = 0` for edition-1, and this is correct, not a regression — a different deferral from Assumption 2's gap.** `neo.family_content` (family-*submitted* items, e.g. a WhatsApp photo a member sends mid-week) was populated by the now-archived `m6_feedback.py`'s webhook-ingestion pipeline; LOD200 §7 explicitly defers this whole mechanism ("Reply ingestion / per-item feedback (Phase B)"). This is unrelated to the LOD200 §2 item 8 "Family Table" *editorial conversation-starter* gap (Assumption 2) — WP007 §2.4's template code already renders `neo.family_content` defensively (empty → no render, AC-31), so `[]` is the fully-correct, already-anticipated value, not a silent omission. Similarly, the `newsletters` table's `items_fetched`/`items_selected` columns (named for the old RSS-scan-volume concept) are repurposed in this WP's `cmd_weekly_build` to mean "total researched+viewing items in this edition" — a deliberate, documented semantic shift of existing columns, not new schema. The `newsletter_items` table is confirmed (by `grep`, at spec-authoring time) to have had **zero** `INSERT` call sites anywhere in the pre-rewire pipeline either — it was already dead; this WP does not populate it, which is a continuation of existing behavior, not a new gap.
13. **This WP's `config/settings.json` edit (§2.14) is deliberately additive/merge-safe against WP002's own, separately-specified `settings.json` edit, because both WPs legitimately touch the same `ai` object.** WP002 §2.7 replaces the whole `ai` object with its own 14 keys (Sonnet-5 pricing/model/research tunables); WP001 §4 and WP004 §4 each explicitly defer adding *their* new `ai.*` keys (`provider`/`provider_fallback`/`anthropic_model`/`cursor_*`, `editorial_max_tokens`) to "whichever future WP wires things into the orchestrator" — this WP. Since WP002's and this WP's edits may be applied by different builder sessions in either order, §2.14 states the **full final merged object** (union of both WPs' keys) as the target end-state, and instructs the builder to merge key-by-key into whatever the file currently contains at edit time, never to blindly overwrite the whole `ai`/`distribution` object.
14. **No concurrency.** The 5 `research_member()` calls, `screen_scout()`, and `generate_editorial()` run strictly sequentially in `cmd_weekly_build` — no threading/async. This is a deliberate simplicity choice consistent with the project's L0/Lean profile and every sibling spec's own sequential code examples; it is not a performance requirement anyone has stated, and Friday's 09:00 build has no wall-clock deadline before 12:00's send. **`_fetch_weather()` (salvaged, §2.8) keeps the exact behavior of the code it is salvaged from: no `--mock` branch.** It always makes a real (free, keyless, Open-Meteo) network call even under `--mock` — this was already true of `m3_normalizer.py`'s original `_fetch_weather`; this WP does not add mock-awareness to it (not requested, and it costs no budget/API key either way).

## 2. Technical specification

### 2.1 `publisher.py` — module foundations

**What to implement:** create `src/publisher.py` (new file). Module docstring + imports + the two result dataclasses + module-level constants + the soft, self-activating import of `src/whatsapp.py` (which does not exist yet — see §2.4).

```python
"""
Family Newsletter — Publisher
FTP upload (index.html + teaser.png) + HTTP-200 verification + email
delivery, per LOD400 FNL-S001-P002-WP006. Replaces src/m5_distributor.py
(archived — §2.13): all Twilio/WhatsApp-direct-send code is removed.
WhatsApp delivery is now a single, family-GROUP-level HOOK for
src/whatsapp.py (WAHA), built by FNL-S001-P003-WP001 (OPS) — NOT this WP.
"""

import logging
import time
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import ftplib
import requests

from .models import NEO, FamilyConfig, Settings, MemberProfile, FTPUploadError
from .env_compat import (
    ftp_credentials,
    ftp_remote_base,
    newsletter_url_base,
    smtp_config,
    smtp_deliver_message,
)

logger = logging.getLogger('family.publisher')

# WhatsApp hook (§2.4). src/whatsapp.py does not exist yet at this WP's
# authoring time (built later by FNL-S001-P003-WP001). This import is
# deliberately soft (try/except) so publisher.py is fully correct and
# testable standalone today, and auto-activates the moment a conforming
# src/whatsapp.py is dropped in — ZERO further edits to THIS file are
# required for P003 to plug in.
try:
    from . import whatsapp as _whatsapp_module
except ImportError:
    _whatsapp_module = None

# Must match editor.TEASER_LINK_PLACEHOLDER (FNL-S001-P002-WP004 §1
# Assumption 7) EXACTLY. Duplicated here rather than imported across
# sibling modules, matching this codebase's established convention (see
# researcher.py §2.4's identical rationale for duplicating llm.py's JSON
# parsing helpers instead of importing them) — a one-string-constant
# import from editor.py into publisher.py would be a backwards, purely
# cosmetic dependency for zero real benefit.
TEASER_LINK_PLACEHOLDER = "{EDITION_LINK}"

DEFAULT_FTP_HTML_FILENAME = "index.html"
DEFAULT_FTP_TEASER_FILENAME = "teaser.png"
```

Result dataclasses (replace `m5_distributor.DistributionResult` — renamed and reshaped; see Assumption 6/§2.6 for why the old per-member "try WhatsApp then email" model no longer fits):

```python
@dataclass
class PublishResult:
    """Returned by publish() (§2.6). Replaces m5_distributor.py's
    DistributionResult. Field-by-field diff from the old shape:
      - public_url: unchanged meaning (the HTML edition's public URL).
      - ftp_success: unchanged meaning (True iff the HTML upload+verify
        succeeded) — kept so orchestrator.cmd_weekly_send's existing
        if result.ftp_success: ... branch needs no logic change, only
        the attribute name on member_results -> email_results (below).
      - teaser_public_url: NEW. None if no teaser_path was given, or its
        upload/verify failed (non-fatal — see publish()'s docstring).
      - email_results: renamed from member_results (WhatsApp is no
        longer a per-member choice in this list — see whatsapp_result).
        Same inner shape: [{member_id, channel, success, error}].
      - whatsapp_result: NEW. A single dict (not a list — WhatsApp is
        now ONE family-group send, not per-member):
        {attempted: bool, success: bool, channel: str, error: Optional[str]}.
    """
    public_url: str
    ftp_success: bool
    teaser_public_url: Optional[str] = None
    email_results: list = field(default_factory=list)
    whatsapp_result: dict = field(default_factory=dict)
```

**Acceptance criteria:**
- [ ] AC-01: `import src.publisher` succeeds with no import-time errors, no network call, whether or not `src/whatsapp.py` exists on disk.
- [ ] AC-02: `publisher._whatsapp_module is None` when `src/whatsapp.py` does not exist (the common case until P003 lands); no exception is raised at import time in that case.
- [ ] AC-03: `PublishResult()` raises (missing required `public_url`/`ftp_success` — no defaults on those two, matching the old `DistributionResult`'s non-optional core fields); `PublishResult(public_url='x', ftp_success=True)` succeeds with `teaser_public_url is None`, `email_results == []`, `whatsapp_result == {}`.
- [ ] AC-04: `TEASER_LINK_PLACEHOLDER == "{EDITION_LINK}"` (byte-identical to `editor.TEASER_LINK_PLACEHOLDER`, WP004 §2.1 — verified by cross-reading both files' literals, not by import).

### 2.2 `publisher.py` — FTP layer (generalized upload primitive + HTTP-verify-with-retry)

**What to implement:**

1. `_ftp_connect`/`_ftp_mkd_recursive` — unchanged from `m5_distributor.py`, reproduced verbatim for this file's self-containment (the source file is archived by this same WP — §2.13 — so nothing should depend on reading it afterward):

```python
def _ftp_connect(host: str, port: int) -> ftplib.FTP:
    """Unchanged from m5_distributor.py."""
    if port == 21:
        return ftplib.FTP(host, timeout=30)
    ftp = ftplib.FTP()
    ftp.connect(host, port, timeout=30)
    return ftp


def _ftp_mkd_recursive(ftp, path):
    """Unchanged from m5_distributor.py. Create remote directory
    recursively (like mkdir -p)."""
    dirs = path.strip('/').split('/')
    current = ''
    for d in dirs:
        current = f"{current}/{d}"
        try:
            ftp.mkd(current)
        except ftplib.error_perm:
            pass  # directory exists
```

2. `ftp_upload_file()` — generalizes `m5_distributor.ftp_upload()`: the remote **filename** is now a parameter (was hardcoded `index.html`), so this one function uploads either `index.html` or `teaser.png` (module scope item 1: "Keep FTP upload (index.html + teaser.png)"):

```python
def ftp_upload_file(local_path: str, remote_filename: str, date: str,
                     settings: Settings) -> str:
    """Same connect/retry/mkdir-recursive logic as m5_distributor.py's
    ftp_upload(), generalized to any remote_filename within the same
    dated directory. Returns the public URL of the uploaded file. Raises
    FTPUploadError only after settings.ftp.retry_count (default 3)
    consecutive connection/login/store failures — a hard, total
    connectivity failure, distinct from "connected fine but the URL
    later 404s," which is _verify_http_200's concern (below)."""
    host, user, passwd, port = ftp_credentials()
    remote_base = ftp_remote_base(settings)
    url_base = newsletter_url_base(settings)
    retry_count = settings.ftp.get('retry_count', 3)
    retry_delay = settings.ftp.get('retry_delay_seconds', 10)

    remote_dir = f"{remote_base}/{date}"
    remote_file = f"{remote_dir}/{remote_filename}"

    for attempt in range(retry_count):
        try:
            ftp = _ftp_connect(host, port)
            ftp.login(user, passwd)
            _ftp_mkd_recursive(ftp, remote_dir)
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_file}', f)
            ftp.quit()

            public_url = f"{url_base}/{date}/{remote_filename}"
            logger.info(f"[publisher] FTP upload success: {public_url}")
            return public_url

        except Exception as e:
            logger.warning(f"[publisher] FTP attempt {attempt+1} failed "
                            f"for {remote_filename}: {e}")
            if attempt < retry_count - 1:
                time.sleep(retry_delay)
            continue

    raise FTPUploadError(
        f"FTP upload of {remote_filename} failed after {retry_count} retries"
    )
```

3. HTTP-200 verification + the single-retry-on-non-200 rule (module scope item 2: "verify HTTP 200 at the public URL (one FTP retry on non-200)"):

```python
def _verify_http_200(url: str, timeout: int = 15) -> tuple:
    """Returns (is_200: bool, status_code: Optional[int]). status_code is
    None only for a network-level exception (DNS/timeout/connection
    refused) — kept distinct from a real non-200 HTTP response for
    clearer logging."""
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.status_code == 200, resp.status_code
    except requests.RequestException as e:
        logger.warning(f"[publisher] HTTP verification request failed for {url}: {e}")
        return False, None


def _upload_and_verify(local_path: str, remote_filename: str, date: str,
                        settings: Settings) -> Optional[str]:
    """FTP upload -> verify HTTP 200 -> on non-200 (or a verification
    request failure), exactly ONE FTP re-upload -> re-verify. Returns the
    public URL on eventual success, or None if it is still not HTTP 200
    after the retry (does NOT raise for this case — a non-200 response is
    a publish-quality problem, not a connectivity problem). Propagates
    FTPUploadError unchanged if ftp_upload_file() itself exhausts its own
    internal connection retries (a hard connectivity failure) — on EITHER
    of the two ftp_upload_file() calls in this function."""
    public_url = ftp_upload_file(local_path, remote_filename, date, settings)
    ok, status = _verify_http_200(public_url)
    if ok:
        return public_url

    logger.warning(f"[publisher] {remote_filename}: HTTP verification "
                    f"returned {status!r} (expected 200) — retrying FTP upload once")
    public_url = ftp_upload_file(local_path, remote_filename, date, settings)
    ok, status = _verify_http_200(public_url)
    if ok:
        return public_url

    logger.error(f"[publisher] {remote_filename}: still not HTTP 200 "
                 f"after 1 retry (last status: {status!r})")
    return None
```

**Acceptance criteria:**
- [ ] AC-05: `ftp_upload_file(...)` with a mocked `ftplib.FTP` that succeeds on the first `connect`/`login`/`storbinary` returns `f"{url_base}/{date}/{remote_filename}"` exactly, for both `remote_filename="index.html"` and `remote_filename="teaser.png"`.
- [ ] AC-06: `ftp_upload_file(...)` with a mocked connection that raises on every attempt raises `FTPUploadError` after exactly `settings.ftp.get('retry_count', 3)` attempts, and `time.sleep` is called `retry_count - 1` times (never after the final attempt).
- [ ] AC-07: `_verify_http_200(url)` with a mocked `requests.get` returning `status_code=200` returns `(True, 200)`; returning `404` returns `(False, 404)`; raising `requests.ConnectionError` returns `(False, None)` without raising.
- [ ] AC-08: `_upload_and_verify(...)` with the first verify returning `200` calls `ftp_upload_file` exactly once (no retry attempted).
- [ ] AC-09: `_upload_and_verify(...)` with the first verify returning `503` and the second (post-retry) verify returning `200` calls `ftp_upload_file` exactly twice and returns the (identical) public URL.
- [ ] AC-10: `_upload_and_verify(...)` with both verifies returning non-200 calls `ftp_upload_file` exactly twice and returns `None` (does not raise).
- [ ] AC-11: `_upload_and_verify(...)` with `ftp_upload_file`'s *second* call (the retry) raising `FTPUploadError` lets that exception propagate out of `_upload_and_verify` unchanged (verified via `pytest.raises`).

### 2.3 `publisher.py` — Email delivery (kept, Twilio removed — it was never present in these specific functions)

**What to implement:** `_build_message()` and `send_email()` are kept **verbatim** from `m5_distributor.py` — neither ever referenced Twilio (the per-member WhatsApp-or-email *choice* lived in the old `distribute()` loop, not in these two functions), so there is nothing to delete here, only to carry forward unchanged into the new file:

```python
def _build_message(member: MemberProfile, neo: NEO, public_url: str) -> str:
    """Unchanged from m5_distributor.py."""
    headlines = []
    for section in neo.member_sections:
        if section['member_id'] == member.id:
            for item in section['items'][:3]:
                headlines.append(f"• {item['title']}")
            break
    headlines_text = '\n'.join(headlines) if headlines else "• Check today's edition!"
    if member.language_preference == 'en':
        return (f"Hey {member.nickname_newsletter}! 🌅\n{neo.greeting}\n\n"
                f"📰 Today for you:\n{headlines_text}\n\n👉 Read: {public_url}")
    else:
        return (f"שלום {member.nickname_newsletter}! 🌅\n{neo.greeting}\n\n"
                f"📰 הנה מה שחיכה לך היום:\n{headlines_text}\n\n👉 לקריאה: {public_url}")


def send_email(member: MemberProfile, neo: NEO, public_url: str,
               settings: Settings) -> bool:
    """Unchanged from m5_distributor.py."""
    try:
        cfg = smtp_config()
        if not cfg["host"] or not cfg["password"]:
            return False
        if not member.email:
            return False

        msg_text = _build_message(member, neo, public_url)
        subject = f"📰 הניוזלטר המשפחתי — {neo.date}"

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"Family Newsletter <{cfg['from_addr']}>"
        msg['To'] = member.email
        msg.attach(MIMEText(msg_text, 'plain', 'utf-8'))
        html_body = (f'<html><body dir="rtl" style="font-family: sans-serif;">'
                     f'<p>{msg_text.replace(chr(10), "<br>")}</p></body></html>')
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        smtp_deliver_message(msg)
        logger.info(f"[publisher] Email sent to {member.nickname_newsletter}")
        return True
    except Exception as e:
        logger.error(f"[publisher] Email failed for {member.id}: {e}")
        return False


def _send_email_raw(email: str, subject: str, body: str) -> bool:
    """Unchanged from m5_distributor.py."""
    try:
        cfg = smtp_config()
        if not cfg["host"] or not cfg["password"]:
            return False
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = f"Family Newsletter <{cfg['from_addr']}>"
        msg['To'] = email
        smtp_deliver_message(msg)
        return True
    except Exception:
        return False
```

Also port `send_survey()` — kept per module scope B.4 ("SAME CLI verbs unchanged" — `weekly-survey` stays invocable), Twilio branch deleted with **no WhatsApp replacement** (see Assumption 11: it is now email-only, since the survey question already ships embedded in the edition, and it is not part of the automatic Friday flow):

```python
def send_survey(family: FamilyConfig, neo: NEO, settings: Settings,
                 mock: bool = False) -> list:
    """Kept for CLI-compatibility (weekly-survey verb, module scope B.4).
    NOT part of the automatic Friday 09:00/12:00 flow (REVIVAL_PLAN §3/§4
    schedule only build+send) — this is a manually-triggered, EMAIL-ONLY
    re-send of the survey_question already embedded in the edition. The
    old per-member Twilio WhatsApp send is removed with no replacement:
    the poll question already reaches the family via the main edition's
    WhatsApp GROUP teaser send (§2.6); a future WP may wire a standalone
    re-ping through the same WAHA hook (§2.4) if ever wanted."""
    results = []
    for member in family.members:
        if mock:
            results.append({'member_id': member.id, 'status': 'mock', 'channel': 'mock'})
            continue

        if member.language_preference == 'en':
            msg = (f"📊 Family Newsletter — Weekly Question\n\n"
                   f"{neo.survey_question}\n\n(Reply freely 🙂)")
        else:
            msg = (f"📊 הניוזלטר המשפחתי — שאלת השבוע\n\n"
                   f"{neo.survey_question}\n\n(שלחו תשובה בחופשיות 🙂)")

        success = _send_email_raw(member.email, "📊 Family Newsletter — Weekly Question", msg) \
            if member.email else False

        results.append({
            'member_id': member.id,
            'status': 'sent' if success else 'failed',
            'channel': 'email' if success else 'none',
        })
    return results
```

**Acceptance criteria:**
- [ ] AC-12: `grep -n "TWILIO\|twilio\|Twilio" src/publisher.py` returns **zero** matches — the single mechanically-checkable proof that all Twilio code (module scope item 1: "DELETE ALL Twilio code") is gone.
- [ ] AC-13: `send_email(member, neo, url, settings)` with `member.email = None` returns `False` without raising and without calling `smtp_deliver_message`.
- [ ] AC-14: `send_survey(family, neo, settings, mock=True)` returns one `{'status': 'mock', ...}` entry per member, calls `_send_email_raw` zero times.
- [ ] AC-15: `send_survey(family, neo, settings, mock=False)` for a member with `language_preference='en'` builds a message containing the literal substring `"Weekly Question"` (English branch); for `'he'`/`'both'`, containing `"שאלת השבוע"` (Hebrew branch).

### 2.4 `publisher.py` — WhatsApp WAHA hook (the plug-in contract for `FNL-S001-P003-WP001`)

**What to implement:** this is module scope item 2's explicit requirement: *"Leave the WhatsApp send as an explicit HOOK/stub for `whatsapp.py` (WAHA)... Spec the hook interface so P003 can plug in."* Per Assumption 9/REVIVAL_PLAN §3, this is deliberately **one message to the family GROUP**, not a per-member send (official APIs like Twilio/Meta Cloud cannot post into a normal WhatsApp group at all — the entire reason WAHA exists per REVIVAL_PLAN §3: *"ה-APIs הרשמיים... לא יכולים להצטרף לקבוצת וואטסאפ רגילה"*):

```python
def send_whatsapp_teaser(teaser_path: str, caption: str, settings: Settings,
                          mock: bool = False) -> dict:
    """THE WAHA hook. Sends ONE image+caption message to the family
    WhatsApp GROUP.

    CONTRACT for src/whatsapp.py (FNL-S001-P003-WP001, OPS — NOT this WP)
    to satisfy: if present, that module must expose a callable

        send_group_image(image_path: str, caption: str,
                          group_target: dict, settings: Settings,
                          mock: bool = False) -> <dict-or-object>

    returning (at minimum) success/channel/error — either a plain dict
    {'success': bool, 'channel': str, 'error': Optional[str]} or any
    object exposing those 3 as attributes (see _normalize_whatsapp_result
    below — either shape is accepted). group_target is
    {'group_name': str, 'waha_number': str}, sourced from
    settings.distribution.whatsapp_group_name / .whatsapp_number
    (§2.14). This corresponds to WAHA Core's own REST `sendImage`
    endpoint on the implementation side — a detail for P003, opaque here.

    This function is picked up via the soft `from . import whatsapp` at
    the top of this file — P003 needs ZERO edits to publisher.py; dropping
    in a conforming src/whatsapp.py is sufficient. Until it exists, this
    always returns a safe, honestly-labeled 'not implemented yet' result
    — it never raises and never blocks publish()."""
    group_target = {
        'group_name': settings.distribution.get('whatsapp_group_name', 'בית ולד 📰'),
        'waha_number': settings.distribution.get('whatsapp_number', ''),
    }

    if mock:
        logger.info(f"[publisher-MOCK] Would send WhatsApp group image to "
                    f"{group_target['group_name']!r}")
        return {'success': True, 'channel': 'mock', 'error': None}

    if _whatsapp_module is not None and hasattr(_whatsapp_module, 'send_group_image'):
        try:
            raw_result = _whatsapp_module.send_group_image(
                teaser_path, caption, group_target, settings, mock=mock)
            return _normalize_whatsapp_result(raw_result)
        except Exception as e:
            logger.error(f"[publisher] whatsapp.send_group_image() raised: {e}")
            return {'success': False, 'channel': 'whatsapp', 'error': str(e)}

    logger.info(
        f"[publisher] WhatsApp hook stub — src/whatsapp.py not present yet "
        f"(FNL-S001-P003-WP001 pending). Would have sent teaser "
        f"({teaser_path}) + caption to group {group_target['group_name']!r}."
    )
    return {'success': False, 'channel': 'whatsapp_stub',
            'error': 'whatsapp.py not implemented (P003 pending)'}


def _normalize_whatsapp_result(raw) -> dict:
    """Accepts either a dict or an object exposing .success/.channel/.error
    attributes from whatsapp.py's real implementation, normalizing to a
    plain dict — P003's builder is free to return either shape."""
    if isinstance(raw, dict):
        return {'success': bool(raw.get('success', False)),
                'channel': raw.get('channel', 'whatsapp'),
                'error': raw.get('error')}
    return {'success': bool(getattr(raw, 'success', False)),
            'channel': getattr(raw, 'channel', 'whatsapp'),
            'error': getattr(raw, 'error', None)}
```

**Acceptance criteria:**
- [ ] AC-16: With `_whatsapp_module = None` (the real state until P003 lands) and `mock=False`, `send_whatsapp_teaser(...)` returns `{'success': False, 'channel': 'whatsapp_stub', 'error': 'whatsapp.py not implemented (P003 pending)'}` exactly, and does not raise.
- [ ] AC-17: With `mock=True`, `send_whatsapp_teaser(...)` returns `{'success': True, 'channel': 'mock', 'error': None}` regardless of whether `_whatsapp_module` is set — mock mode short-circuits before the hook-dispatch branch.
- [ ] AC-18: With a mocked `_whatsapp_module` exposing `send_group_image` returning `{'success': True, 'channel': 'whatsapp', 'error': None}` (a plain dict), `send_whatsapp_teaser(...)` returns that dict unchanged (post-normalization, identical values).
- [ ] AC-19: With a mocked `_whatsapp_module.send_group_image` returning an object (not a dict) with `.success = True`, `.channel = 'whatsapp'`, `.error = None` attributes, `_normalize_whatsapp_result` correctly extracts a matching plain dict.
- [ ] AC-20: With a mocked `_whatsapp_module.send_group_image` raising an exception, `send_whatsapp_teaser(...)` catches it, returns `{'success': False, 'channel': 'whatsapp', 'error': '<the exception message>'}`, and does not propagate the exception.
- [ ] AC-21: `group_target['waha_number']` and `['group_name']` are read from `settings.distribution.get('whatsapp_number', '')` / `.get('whatsapp_group_name', 'בית ולד 📰')` respectively — verified via a settings fixture with explicit non-default values, confirming they flow through to the `group_target` dict passed to `send_group_image` (or logged, in the stub path).

### 2.5 `publisher.py` — Admin escalation (budget breach, teaser failure — LOD200 §6)

**What to implement:** the concrete mechanism behind Assumption 9.

```python
def _resolve_admin_email(family: FamilyConfig, settings: Settings) -> Optional[str]:
    """Resolves where operational alerts get emailed.
    settings.distribution.admin_email wins if set (§2.14); else falls
    back to the 'nimrod' member's family.json email; else None (caller
    then only logs — see escalate_admin_alert)."""
    configured = settings.distribution.get('admin_email', '')
    if configured:
        return configured
    for member in family.members:
        if member.id == 'nimrod' and member.email:
            return member.email
    return None


def escalate_admin_alert(subject: str, body: str, family: FamilyConfig,
                          settings: Settings, mock: bool = False) -> bool:
    """Best-effort operational escalation email (budget-cap breach —
    LOD200 §6; teaser-generation failure — orchestrator.cmd_weekly_build,
    §2.11). NEVER raises: a failed escalation attempt must not crash the
    build/send it is trying to report on. Returns True iff the email was
    (or, in mock mode, would have been) sent."""
    if mock:
        logger.info(f"[publisher-MOCK] Would escalate: {subject}")
        return True

    to_addr = _resolve_admin_email(family, settings)
    if not to_addr:
        logger.error(f"[publisher] Cannot escalate '{subject}' — no admin_email "
                      f"configured and no 'nimrod' member email on file")
        return False

    try:
        cfg = smtp_config()
        if not cfg["host"] or not cfg["password"]:
            logger.error(f"[publisher] Cannot escalate '{subject}' — SMTP not configured")
            return False

        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = f"⚠️ Family Newsletter ALERT — {subject}"
        msg['From'] = f"Family Newsletter <{cfg['from_addr']}>"
        msg['To'] = to_addr

        smtp_deliver_message(msg)
        logger.info(f"[publisher] Escalation email sent to {to_addr}: {subject}")
        return True
    except Exception as e:
        logger.error(f"[publisher] Escalation email failed: {e}")
        return False
```

**Acceptance criteria:**
- [ ] AC-22: `_resolve_admin_email(family, settings)` with `settings.distribution = {'admin_email': 'x@y.com'}` returns `'x@y.com'` regardless of `family`'s contents.
- [ ] AC-23: `_resolve_admin_email(family, settings)` with `settings.distribution = {}` and `family.members` containing a member with `id='nimrod', email='n@z.com'` returns `'n@z.com'`.
- [ ] AC-24: `_resolve_admin_email(family, settings)` with `settings.distribution = {}` and no `nimrod` member (or `nimrod.email` is `None`) returns `None`.
- [ ] AC-25: `escalate_admin_alert(..., mock=True)` returns `True` and calls neither `_resolve_admin_email`'s SMTP path nor `smtp_deliver_message`.
- [ ] AC-26: `escalate_admin_alert(..., mock=False)` with `_resolve_admin_email` returning `None` returns `False`, logs an error, and does not call `smtp_deliver_message`.
- [ ] AC-27: `escalate_admin_alert(..., mock=False)` with `smtp_deliver_message` mocked to raise an exception returns `False` (does not propagate) and logs an error.
- [ ] AC-28: `escalate_admin_alert("Weekly budget cap exceeded", "...", family, settings)`'s resulting `msg['Subject']` contains the literal substring `"Weekly budget cap exceeded"` prefixed by `"⚠️ Family Newsletter ALERT —"`.

### 2.6 `publisher.py` — `publish()` public entry point

**What to implement:** the full flow per module scope item 2: *"FTP upload → verify HTTP 200 at the public URL (one FTP retry on non-200) → email delivery"* then the WhatsApp hook.

```python
def publish(html_path: str, teaser_path: Optional[str], neo: NEO,
            family: FamilyConfig, settings: Settings,
            mock: bool = False) -> PublishResult:
    """THE public entry point — replaces m5_distributor.distribute().

    Flow: FTP-upload+verify index.html (fatal if it never reaches HTTP
    200 — nothing to link to) -> FTP-upload+verify teaser.png if given
    (degraded/non-fatal on failure — the edition still ships without a
    pretty image) -> email every family member -> WhatsApp group hook
    (§2.4), only attempted if a verified teaser is available (per
    REVIVAL_PLAN §3: image+caption+link is the WhatsApp delivery
    contract; there is nothing meaningful to send without the image)."""
    if mock:
        public_url = f"https://nimrod.bio/agents/newsletter/{neo.date}/index.html"
        teaser_public_url = (f"https://nimrod.bio/agents/newsletter/{neo.date}/teaser.png"
                              if teaser_path else None)
        logger.info(f"[publisher-MOCK] Skipping FTP, URL: {public_url}")
        email_results = [
            {'member_id': m.id, 'channel': 'mock', 'success': True, 'error': None}
            for m in family.members
        ]
        whatsapp_result = send_whatsapp_teaser(teaser_path or '', '', settings, mock=True)
        whatsapp_result = {'attempted': True, **whatsapp_result}
        return PublishResult(public_url=public_url, ftp_success=True,
                              teaser_public_url=teaser_public_url,
                              email_results=email_results,
                              whatsapp_result=whatsapp_result)

    # Step 1: HTML — fatal if it never verifies HTTP 200.
    try:
        public_url = _upload_and_verify(
            html_path, DEFAULT_FTP_HTML_FILENAME, neo.date, settings)
    except FTPUploadError as e:
        logger.critical(f"[publisher] FTP connection failed for "
                         f"{DEFAULT_FTP_HTML_FILENAME}: {e}")
        return PublishResult(
            public_url='', ftp_success=False, teaser_public_url=None,
            email_results=[], whatsapp_result={
                'attempted': False, 'success': False, 'channel': 'none',
                'error': 'ftp_connection_failed',
            })

    if public_url is None:
        logger.critical(f"[publisher] {DEFAULT_FTP_HTML_FILENAME} never "
                         f"verified HTTP 200")
        return PublishResult(
            public_url='', ftp_success=False, teaser_public_url=None,
            email_results=[], whatsapp_result={
                'attempted': False, 'success': False, 'channel': 'none',
                'error': 'html_not_200',
            })

    # Step 2: teaser — degraded, non-fatal.
    teaser_public_url = None
    if teaser_path:
        try:
            teaser_public_url = _upload_and_verify(
                teaser_path, DEFAULT_FTP_TEASER_FILENAME, neo.date, settings)
            if teaser_public_url is None:
                logger.error(f"[publisher] teaser.png never verified HTTP "
                              f"200 — continuing without it")
        except FTPUploadError as e:
            logger.error(f"[publisher] FTP connection failed for "
                          f"teaser.png: {e} — continuing without it")

    # Step 3: email — every member with an address on file.
    email_results = []
    for member in family.members:
        if not member.email:
            email_results.append({'member_id': member.id, 'channel': 'none',
                                   'success': False, 'error': 'No email on file'})
            continue
        success = send_email(member, neo, public_url, settings)
        email_results.append({'member_id': member.id, 'channel': 'email',
                               'success': success,
                               'error': None if success else 'Email send failed'})

    # Step 4: WhatsApp group hook — only if a teaser is actually live.
    if teaser_public_url:
        caption = (neo.metadata.get('teaser_caption', '') or '') \
            .replace(TEASER_LINK_PLACEHOLDER, public_url)
        hook_result = send_whatsapp_teaser(teaser_path, caption, settings, mock=mock)
        whatsapp_result = {'attempted': True, **hook_result}
    else:
        whatsapp_result = {'attempted': False, 'success': False,
                            'channel': 'whatsapp', 'error': 'no_teaser_available'}
        logger.info("[publisher] Skipping WhatsApp hook — no verified "
                    "teaser.png this edition")

    return PublishResult(public_url=public_url, ftp_success=True,
                          teaser_public_url=teaser_public_url,
                          email_results=email_results,
                          whatsapp_result=whatsapp_result)
```

**Acceptance criteria:**
- [ ] AC-29: `publish(..., mock=True)` returns `ftp_success=True`, a deterministic `public_url` of the exact shape shown, `email_results` with one `{'channel': 'mock', 'success': True, ...}` entry per family member, and makes **zero** real `requests`/`ftplib` calls.
- [ ] AC-30: `publish(...)` with `_upload_and_verify` (HTML) raising `FTPUploadError` returns `ftp_success=False`, `public_url=''`, `email_results=[]` (email is never attempted), and `whatsapp_result['attempted'] is False`.
- [ ] AC-31: `publish(...)` with `_upload_and_verify` (HTML) returning `None` (never reached HTTP 200) returns the identical degraded shape as AC-30 (`ftp_success=False`, no email attempted) — both HTML-failure modes are treated identically downstream.
- [ ] AC-32: `publish(...)` with HTML succeeding but `_upload_and_verify` (teaser) raising `FTPUploadError` still returns `ftp_success=True`, `teaser_public_url=None`, and **still attempts email delivery to every member** (teaser failure does not block email) — verified via `send_email`'s mock call count equalling `len(family.members)`.
- [ ] AC-33: `publish(...)` with `teaser_path=None` (no teaser was generated this edition — orchestrator's own degraded path, §2.11) skips the teaser FTP step entirely (`_upload_and_verify` for `teaser.png` is never called) and the WhatsApp hook is never attempted (`whatsapp_result['attempted'] is False`, `error == 'no_teaser_available'`).
- [ ] AC-34: `publish(...)` with a live `teaser_public_url` calls `send_whatsapp_teaser` with `caption` equal to `neo.metadata['teaser_caption']` with **every** occurrence of `TEASER_LINK_PLACEHOLDER` replaced by the real `public_url` — verified with a caption containing the placeholder twice, confirming both are substituted (plain `str.replace` replaces all occurrences by default).
- [ ] AC-35: A member with `email=None` produces an `email_results` entry with `success=False, error='No email on file'`, and `send_email` is never called for that member (verified via call count).

### 2.7 `orchestrator.py` — import rewire

**What to implement:** replace the entire import block (module scope item 4: "DROP m2_scanner, m3_normalizer, m6_feedback; ADD researcher, editor, teaser, publisher").

```python
import argparse
import json
import logging
import re
import sys
import os
import time
from datetime import datetime, timezone
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    pass

from src.m1_profiles import load_profiles, load_settings
from src import researcher
from src import editor
from src import teaser
from src import publisher
from src import llm
from src.m4_renderer import render, save_html, CHARACTER_SCHEDULE
from src.db import Database
from src.token_tracker import TokenTracker
from src.env_compat import newsletter_url_base
from src.models import NEO
```

Dropped, and why each is safe to drop: `load_sources`/`get_scan_rules` (`m1_profiles.py`, now dead — only ever called by the archived scan pipeline; `m1_profiles.py` itself is unedited, kept BACKFILL, out of this WP's file scope — §6); `scan_all`/`generate_mock_ncis` (archived `m2_scanner.py`); `build_edition` (archived `m3_normalizer.py`); `distribute`/`send_survey` from the old `m5_distributor` (superseded by `publisher.publish`/`publisher.send_survey`); `run_webhook_server` (archived `m6_feedback.py` — the `webhook` CLI verb is removed, Assumption 11).

**Acceptance criteria:**
- [ ] AC-36: `grep -n "m2_scanner\|m3_normalizer\|m6_feedback\|m5_distributor" src/orchestrator.py` returns **zero** matches after this edit.
- [ ] AC-37: `python -m src.orchestrator health-check` runs to completion with no `ImportError`/`ModuleNotFoundError` (the single cheapest end-to-end smoke test that every import in this file actually resolves).

### 2.8 `orchestrator.py` — Salvaged zero-token assembly functions

**What to implement:** per module scope item 6, extract `_fetch_weather` (with **Basel removed** — module scope item 5: "Pardes Hanna ONLY") and `_format_hebrew_date` from `m3_normalizer.py` into `orchestrator.py` as private functions, plus one new small helper this WP adds for free (Assumption 9's character-metadata fix).

```python
def _fetch_weather(settings) -> list:
    """Salvaged from m3_normalizer.py, UNCHANGED except LOCATIONS now has
    only Pardes Hanna — Basel removed (module scope item 5; LOD200 §2
    item 4: 'Pardes Hanna ONLY — Basel REMOVED — Shaked home'; confirmed
    by TRANSCRIPT_MINING_2026-07-22.md: 'שקד חזר מבאזל -> הביתה').
    Real Open-Meteo network call, no API key, no --mock branch (Assumption
    14 — unchanged behavior from the salvaged original)."""
    import requests as _req

    LOCATIONS = [
        {'city': 'פרדס חנה', 'city_en': 'Pardes Hanna', 'lat': 32.47, 'lon': 34.97, 'icon': '🏠'},
    ]
    HEB_DAYS = ['ב׳', 'ג׳', 'ד׳', 'ה׳', 'ו׳', 'ש׳', 'א׳']

    weather_data = []
    for loc in LOCATIONS:
        try:
            resp = _req.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    'latitude': loc['lat'], 'longitude': loc['lon'],
                    'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max',
                    'timezone': 'auto', 'forecast_days': 7,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            daily_data = data.get('daily', {})
            dates = daily_data.get('time', [])
            highs = daily_data.get('temperature_2m_max', [])
            lows = daily_data.get('temperature_2m_min', [])
            precip = daily_data.get('precipitation_sum', [])
            wind = daily_data.get('wind_speed_10m_max', [])

            daily_list = []
            for i in range(min(7, len(dates))):
                dt = datetime.strptime(dates[i], '%Y-%m-%d')
                daily_list.append({
                    'date': dates[i], 'day': HEB_DAYS[dt.weekday()],
                    'high': round(highs[i]) if i < len(highs) else 25,
                    'low': round(lows[i]) if i < len(lows) else 15,
                    'precipitation': round(precip[i], 1) if i < len(precip) else 0,
                    'wind_speed': round(wind[i]) if i < len(wind) else 10,
                })

            today_high = round(highs[0]) if highs else 25
            today_precip = precip[0] if precip else 0
            today_wind = wind[0] if wind else 0

            if today_precip > 5:
                w_icon = '🌧️'
            elif today_precip > 0:
                w_icon = '⛅'
            elif today_high > 30:
                w_icon = '☀️'
            elif today_high > 20:
                w_icon = '🌤️'
            else:
                w_icon = '❄️' if today_high < 10 else '🌥️'

            wind_alert = today_wind >= 20
            avg_high = round(sum(highs[:7]) / min(7, len(highs)))
            max_wind = round(max(wind[:7])) if wind else 0
            total_precip = round(sum(precip[:7]), 1)

            summary_parts = [f"ממוצע {avg_high}°"]
            if total_precip > 0:
                summary_parts.append(f"משקעים {total_precip}mm")
            if max_wind >= 20:
                summary_parts.append(f"רוח עד {max_wind} קמ\"ש ⛵")

            weather_data.append({
                'city': loc['city'], 'city_en': loc['city_en'], 'icon': w_icon,
                'temp': f"{today_high}°", 'is_temp': False, 'wind_alert': wind_alert,
                'daily': daily_list, 'description': f"{loc['icon']} {loc['city']}",
                'week_summary': ' | '.join(summary_parts),
            })
            logger.info(f"[orchestrator] Weather fetched: {loc['city_en']} — {today_high}°, wind {today_wind}km/h")
        except Exception as e:
            logger.warning(f"[orchestrator] Weather fetch failed for {loc['city_en']}: {e}")
            continue

    return weather_data


def _format_hebrew_date(today: str) -> str:
    """Salvaged verbatim from m3_normalizer.py — no changes."""
    HEB_DAYS = ['שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת', 'ראשון']
    HEB_MONTHS = ['', 'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
                  'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
    try:
        dt = datetime.strptime(today, '%Y-%m-%d')
        return f"יום {HEB_DAYS[dt.weekday()]}, {dt.day} ב{HEB_MONTHS[dt.month]} {dt.year}"
    except (ValueError, IndexError):
        return today


def _character_metadata() -> dict:
    """NEW (this WP, free fix — Assumption 9 is about escalation; THIS is
    a separate, small, free bonus fix folded into the same assembly pass
    since it touches the metadata dict this WP already owns). Populates
    neo.metadata['character_emoji']/['character_name']/['character_month']
    from m4_renderer.CHARACTER_SCHEDULE. The template already reads these
    3 keys (cover mascot-name line) via .get(key, default) — the OLD
    m3_normalizer.py never populated them, so that line always silently
    rendered the hardcoded '🎩 Cat in the Hat' fallback regardless of the
    real monthly schedule."""
    current_month = datetime.now(timezone.utc).strftime('%Y-%m')
    meta = CHARACTER_SCHEDULE.get(current_month, {
        'name': 'Character', 'emoji': '🎭', 'style': 'Custom',
    })
    return {
        'character_emoji': meta['emoji'],
        'character_name': meta['name'],
        'character_month': current_month,
    }
```

**Acceptance criteria:**
- [ ] AC-38: `_fetch_weather(settings)`'s internal `LOCATIONS` list has exactly 1 entry (`city_en == 'Pardes Hanna'`) — `grep -c "Basel\|באזל" src/orchestrator.py` returns `0`.
- [ ] AC-39: `_fetch_weather(settings)` with a mocked `requests.get` returning a well-formed Open-Meteo payload returns a list of exactly 1 dict, with all the keys shown in the OLD `m3_normalizer.py` version (`city, city_en, icon, temp, is_temp, wind_alert, daily, description, week_summary`) — the per-item shape is unchanged, only the location count changed.
- [ ] AC-40: `_fetch_weather(settings)` with a mocked `requests.get` raising `requests.RequestException` for Pardes Hanna returns `[]` (not a crash) — matches the salvaged original's per-location `try/except continue`.
- [ ] AC-41: `_format_hebrew_date("2026-07-24")` returns `"יום שישי, 24 ביולי 2026"` (Friday — matches the OLD function's exact output for a known date, confirming byte-identical salvage).
- [ ] AC-42: `_format_hebrew_date("not-a-date")` returns the input string unchanged (`"not-a-date"`), not an exception.
- [ ] AC-43: `_character_metadata()` for a month present in `CHARACTER_SCHEDULE` (e.g. `'2026-04'`, mocked via `datetime.now`) returns `{'character_emoji': '🎩', 'character_name': 'Cat in the Hat', 'character_month': '2026-04'}`; for an absent month, returns the generic `{'character_emoji': '🎭', 'character_name': 'Character', 'character_month': '<that month>'}` fallback.

### 2.9 `orchestrator.py` — Adapter functions (the wiring seams)

**What to implement:** the four adapters resolving Assumptions 3, 5, 6, 7.

```python
_TAG_STRIP_RE = re.compile(r'</?(strong|em)>', re.IGNORECASE)
_SENTENCE_END_RE = re.compile(r'[.!?׃]')


def _short_greeting(opener_html: str, max_len: int = 160) -> str:
    """Assumption 7. Derives a short, plain-text greeting from editor.py's
    full opener HTML — feeds BOTH neo.greeting's real consumers: the
    template's cover mascot-bubble (unconstrained) and teaser.py's small
    speech bubble (WP005 §2.6: max 3 wrapped lines, plain text, no HTML
    tags). Strips the two permitted opener tags (<strong>/<em>), then
    takes the first sentence if it ends within max_len, else a hard
    truncation with a trailing ellipsis. Zero-token, deterministic."""
    text = _TAG_STRIP_RE.sub('', opener_html or '').strip()
    if not text:
        return ''
    m = _SENTENCE_END_RE.search(text)
    if m and m.end() <= max_len:
        return text[:m.end()].strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + '…'


def _map_discovery_bridges(bridges: list, research_results: dict) -> list:
    """Assumption 6. Adapts editor.py's abstract {from_member, to_member,
    text} bridges (WP004 §2.2) onto the UNCHANGED (BACKFILL, kept-as-is)
    Discovery template block's actual required shape — confirmed by
    direct read of templates/newsletter.html.j2 lines 731-744:
    {bridge_text, title, url, summary (optional)}. Anchors each bridge to
    its from_member's own top-ranked researched item (items[0]) — the
    SAME item already shown in that member's Personal Corner, re-
    referenced (not re-selected) as the bridge's clickable target."""
    mapped = []
    for b in bridges:
        source_items = research_results.get(b.get('from_member', ''), [])
        anchor = source_items[0] if source_items else None
        mapped.append({
            'from_member': b.get('from_member', ''),
            'to_member': b.get('to_member', ''),
            'bridge_text': b.get('text', ''),
            'title': anchor['title'] if anchor else (b.get('text', '')[:60] or '...'),
            'url': anchor['url'] if anchor else '#',
            'summary': anchor['summary'] if anchor else '',
        })
    return mapped


def _map_viewing(screen_scout_result: dict) -> dict:
    """Assumption 5. Adapts researcher.screen_scout()'s return shape
    (WP003 §2.14) onto neo.metadata['viewing']'s template contract (WP007
    §2.3/§3). Neither sibling spec defines this mapping — see Assumption
    5 for the full citation trail."""
    def _one(pick, member_id=None):
        if not pick:
            return None
        out = {
            'title': pick.get('title', ''),
            'platform': pick.get('service', ''),
            'hebrew_subs': bool(pick.get('hebrew_subtitles_verified')),
            'available_il': bool(pick.get('availability_verified')),
            'note': pick.get('share_note') or pick.get('availability_note') or '',
        }
        if member_id:
            out['member_id'] = member_id
        return out

    return {
        'family_pick': _one(screen_scout_result.get('family_pick')),
        'personal_pick': _one(
            screen_scout_result.get('personal_pick'),
            member_id=screen_scout_result.get('personal_pick_member_id'),
        ),
    }


def _compute_edition_number(db: Database) -> int:
    """Assumption 8. Duplicates m4_renderer.render()'s own internal
    edition_number query verbatim (that function neither accepts nor
    returns edition_number, and its signature is not changed by this WP
    — see Assumption 8) so orchestrator.py can pass the SAME value to
    teaser.generate_teaser(). Safe by construction: no newsletters row is
    inserted between render()'s internal query and this call within one
    synchronous cmd_weekly_build run."""
    try:
        row = db.conn.execute(
            "SELECT COUNT(*) as cnt FROM newsletters WHERE status != 'build_failed'"
        ).fetchone()
        return row['cnt'] or 1
    except Exception:
        return 1
```

**Acceptance criteria:**
- [ ] AC-44: `_short_greeting('<strong>בוקר טוב, בית ולד!</strong> השבוע מלא בגילויים.')` returns `'בוקר טוב, בית ולד!'` — tags stripped, truncated at the first sentence end, well under 160 chars.
- [ ] AC-45: `_short_greeting('x' * 300)` (no sentence-ending punctuation anywhere) returns a 161-character string ending in `'…'` (160 chars + ellipsis).
- [ ] AC-46: `_short_greeting('')` and `_short_greeting(None)` both return `''` without raising.
- [ ] AC-47: `_map_discovery_bridges([{'from_member': 'nimrod', 'to_member': 'tzlil', 'text': 'X would love this'}], {'nimrod': [{'title': 'T', 'url': 'https://x.com', 'summary': 'S', ...}]})` returns one dict with `bridge_text='X would love this'`, `title='T'`, `url='https://x.com'`, `summary='S'`.
- [ ] AC-48: `_map_discovery_bridges([{'from_member': 'nimrod', 'to_member': 'tzlil', 'text': 'X'}], {})` (no researched items at all for `nimrod`) returns one dict with `url='#'`, `title` falling back to a truncated slice of `text`, `summary=''` — never raises, never `KeyError`s.
- [ ] AC-49: `_map_viewing({'family_pick': {'title': 'T', 'service': 'netflix', 'hebrew_subtitles_verified': True, 'availability_verified': True, 'share_note': 'N'}, 'personal_pick': None, 'personal_pick_member_id': 'tzlil'})` returns `{'family_pick': {'title': 'T', 'platform': 'netflix', 'hebrew_subs': True, 'available_il': True, 'note': 'N'}, 'personal_pick': None}` — `personal_pick` stays `None` (not a dict with empty fields) when the underlying pick is `None`.
- [ ] AC-50: `_map_viewing({'family_pick': None, 'personal_pick': {'title': 'T2', 'service': 'prime', 'hebrew_subtitles_verified': False, 'availability_verified': True, 'availability_note': 'A'}, 'personal_pick_member_id': 'shaked'})`'s `personal_pick` dict includes `'member_id': 'shaked'` and `'note': 'A'` (falls back to `availability_note` when `share_note` is absent).
- [ ] AC-51: `_compute_edition_number(db)` against a real (test) `Database` with 3 `newsletters` rows (`status` = `ready`, `ready`, `build_failed`) returns `2` (the `build_failed` row excluded, matching `m4_renderer.render()`'s own query exactly).

### 2.10 `orchestrator.py` — `_build_neo()` full NEO assembly

**What to implement:** replaces `m3_normalizer._build_neo()`'s role for the new pipeline. This is the function that ties every sibling module's output together into the one object `render()`/`teaser.generate_teaser()`/`publisher.publish()` all consume.

```python
def _build_neo(family, settings, today: str, date_formatted: str,
                research_results: dict, screen_scout_result: dict,
                editorial: dict, weather: list) -> NEO:
    """Builds the NEO object the UNCHANGED (BACKFILL) template + this WP's
    own render(..., settings=settings) call expect. member_order matches
    m3_normalizer.py's own hardcoded order (salvaged verbatim — the same
    order the Family Strip / Personal Corners render in, per LOD200 §2)."""
    member_order = ["nimrod", "michal", "shaked", "maayan", "tzlil"]
    member_map = {m.id: m for m in family.members}

    member_sections = []
    for mid in member_order:
        member = member_map.get(mid)
        if not member:
            continue
        lang = "en" if member.language_preference == "en" else "he"
        items = []
        for item in research_results.get(mid, []):
            share_note = item.get('share_note', '')
            summary = item.get('summary', '')
            items.append({
                'title': item.get('title', ''),
                'summary': summary,
                'full_text': f"{summary}\n\n{share_note}".strip(),
                'url': item.get('url', ''),
                'source_name': item.get('source', ''),
                'category': item.get('category', ''),
                'language': lang,
                'image_url': None,  # researcher.py never returns one (WP003 §4 item shape)
                'published_at': None,
            })
        member_sections.append({
            'member_id': mid,
            'member_name': member.nickname_newsletter,
            'member_name_en': member.name_en,
            'language': member.language_preference,
            'items': items,
        })

    discovery = _map_discovery_bridges(editorial.get('discovery_bridges', []), research_results)

    puzzle = editorial.get('puzzle', {})
    puzzle_text = f"{puzzle.get('intro', '')}\n\n{puzzle.get('question', '')}"
    trivia = {
        'puzzle': puzzle_text,
        # Rendered field = LAST week's reveal, never this week's secret — Assumption 3.
        'answer': puzzle.get('last_week_answer_reveal', ''),
        'history': (f"{editorial.get('today_in_history', {}).get('fact', '')} "
                    f"{editorial.get('today_in_history', {}).get('family_idea_callout', '')}").strip(),
    }

    qow = editorial.get('question_of_the_week', {})
    poll_q = qow.get('poll_question', '')
    poll_opts = qow.get('poll_options', [])
    survey_question = f"{poll_q} ({' / '.join(poll_opts)})" if poll_opts else poll_q
    if qow.get('preamble'):
        survey_question = f"{qow['preamble']} {survey_question}".strip()

    greeting = _short_greeting(editorial.get('opener', ''))

    metadata = {
        'opener_text': editorial.get('opener', ''),
        'closer_text': editorial.get('closer', ''),
        'weather': weather,
        'teaser_caption': editorial.get('teaser_caption', ''),
        'editor_credit': editorial.get('editor_credit', ''),
        'editors_choice': editorial.get('editors_choice', {}),
        'viewing': _map_viewing(screen_scout_result),
        'whatsapp_group_link': '',  # WAHA has no public invite link (bot number only) — Assumption 9/§2.14
        'whatsapp_number': settings.distribution.get('whatsapp_number', ''),
        # --- OPEN RECONCILIATION ITEM (Assumption 2, §2.14, §6) — no WP
        # currently produces these 3. Left at safe, template-suppressing
        # defaults (WP007's own {% if %} guards render nothing, not an
        # error) until team_00 resolves the gap. ---
        'family_table_text': '',
        'extended_family': [],
        'shelf_pick': {},
    }
    metadata.update(_character_metadata())

    return NEO(
        date=today,
        family_name=family.family_name,
        greeting=greeting,
        family_content=[],  # Phase B (family-submission webhook ingestion) not active — LOD200 §7; Assumption 12
        member_sections=member_sections,
        discovery=discovery,
        trivia=trivia,
        survey_question=survey_question,
        date_formatted=date_formatted,
        metadata=metadata,
    )
```

**Acceptance criteria:**
- [ ] AC-52: `_build_neo(...)` with `family.members` in `config/family.json`'s real order (nimrod, michal, shaked, maayan, tzlil) produces `member_sections` in the exact order `[nimrod, michal, shaked, maayan, tzlil]`, regardless of `research_results` dict key insertion order (Python dicts preserve insertion order, but this function iterates the hardcoded `member_order` list, not `research_results.keys()`).
- [ ] AC-53: For a member with 3 researched items, `member_sections[i]['items']` has exactly 3 dicts, each containing all 9 keys shown (`title, summary, full_text, url, source_name, category, language, image_url, published_at`), with `image_url is None` and `published_at is None` for every item.
- [ ] AC-54: `member_sections[i]['items'][j]['full_text']` equals `f"{summary}\n\n{share_note}"` when both are non-empty; equals just `summary.strip()` when `share_note` is empty (the trailing `\n\n` + empty string is stripped, not left dangling).
- [ ] AC-55: `trivia['answer']` equals `editorial['puzzle']['last_week_answer_reveal']` exactly — **never** `editorial['puzzle']['answer']` (this is the single most safety-critical AC in this subsection — a regression here reintroduces the self-spoiling bug described in Assumption 3; verify with a fixture where `puzzle['answer'] != puzzle['last_week_answer_reveal']` and assert the DISTINCT value landed in `trivia['answer']`).
- [ ] AC-56: `survey_question` for `qow = {'preamble': 'השבוע רוצים לדעת:', 'poll_question': 'מה לבנות?', 'poll_options': ['א', 'ב']}` equals `"השבוע רוצים לדעת: מה לבנות? (א / ב)"` exactly (preamble, then question, then parenthesized slash-joined options).
- [ ] AC-57: `survey_question` for `qow = {'poll_question': 'מה לבנות?', 'poll_options': []}` (no options, no preamble) equals exactly `"מה לבנות?"` (no trailing empty parens).
- [ ] AC-58: `metadata['family_table_text'] == ''`, `metadata['extended_family'] == []`, `metadata['shelf_pick'] == {}` in every call — confirming the open-reconciliation-item fields are always the WP007-template-safe empty defaults, never `None` (which would break `.get(key, {})`-style downstream reads expecting a dict/list/str, not `None`).
- [ ] AC-59: `metadata['whatsapp_number']` reflects `settings.distribution.get('whatsapp_number', '')` exactly (a settings fixture with a non-default value flows through unchanged).
- [ ] AC-60: `family_content == []` unconditionally (no code path in this function ever sets it otherwise).
- [ ] AC-61: `neo.to_json()` (existing `NEO` method, unchanged) succeeds without raising on the full output of `_build_neo(...)` — confirms every value is JSON-serializable (no stray non-primitive objects leaked into `metadata`/`member_sections`/etc.).

### 2.11 `orchestrator.py` — `cmd_weekly_build()` full rewrite

**What to implement:** the complete pipeline sequencing per module scope item 5, folding in Assumptions 1, 4, 8, 9.

```python
def cmd_weekly_build(args):
    """researcher -> editor -> assemble (no tokens) -> render -> teaser ->
    save + db.update_newsletter -> budget check. Replaces the OLD
    M1->M2->M3->M4 pipeline."""
    logger.info("=" * 60)
    logger.info("WEEKLY BUILD starting")
    logger.info("=" * 60)
    start_time = time.time()

    config_dir = args.config or "config/"
    family = load_profiles(config_dir)
    settings = load_settings(config_dir)
    logger.info(f"Family: {family.family_name} ({len(family.members)} members)")

    db = Database(args.db or "data/family.db")
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # Prior puzzle answer MUST be read BEFORE create_newsletter(today, ...)
    # below, or a same-day re-run would read today's own (incomplete) row
    # instead of last week's (Assumption 4).
    prior_row = db.get_last_newsletter()
    prior_puzzle_answer = None
    if prior_row and prior_row.get('date') != today:
        prior_puzzle_answer = prior_row.get('puzzle_answer') or None

    db.create_newsletter(today, 'building')

    tt = TokenTracker(db, mock=args.mock)
    llm.configure(db, settings.ai, mock=args.mock)  # REQUIRED before editor.generate_editorial() — Assumption 1

    try:
        research_results = researcher.research_all_members(tt, db, family, today)
        screen_scout_result = researcher.screen_scout(tt, db, family, today)

        research_highlights = {
            mid: [item.get('share_note', '') for item in items if item.get('share_note')]
            for mid, items in research_results.items()
        }

        editorial = editor.generate_editorial(
            family, research_highlights, prior_puzzle_answer, today, settings,
            mock=args.mock,
        )
    except (llm.LLMError, editor.EditorSchemaError) as e:
        logger.critical(f"[orchestrator] Editorial generation failed fatally: {e}")
        db.update_newsletter(today, status='build_failed')
        db.close()
        raise

    weather = _fetch_weather(settings)
    date_formatted = _format_hebrew_date(today)

    neo = _build_neo(family, settings, today, date_formatted, research_results,
                      screen_scout_result, editorial, weather)

    html = render(neo, template_path="templates/", db=db, settings=settings)
    html_path = save_html(html, today)

    edition_number = _compute_edition_number(db)
    teaser_path = None
    try:
        teaser_path = teaser.generate_teaser(neo, edition_number=edition_number)
    except teaser.TeaserRenderError as e:
        logger.critical(f"[orchestrator] Teaser generation failed: {e}")
        publisher.escalate_admin_alert(
            "Teaser generation failed", f"{today}: {e}", family, settings, mock=args.mock)

    items_selected = sum(len(v) for v in research_results.values())
    for pick_key in ('family_pick', 'personal_pick'):
        if screen_scout_result.get(pick_key):
            items_selected += 1

    url_base = newsletter_url_base(settings)
    db.update_newsletter(
        today, status='ready', html_path=html_path,
        public_url=f"{url_base}/{today}/index.html",
        greeting=neo.greeting,
        puzzle=neo.trivia.get('puzzle', ''),
        puzzle_answer=editorial['puzzle']['answer'],  # THIS week's raw secret — for next week (Assumption 3)
        survey_question=neo.survey_question,
        items_fetched=items_selected,   # legacy column, repurposed — Assumption 12
        items_selected=items_selected,
        submissions_count=0,            # Phase B not active this edition — Assumption 12
        build_duration_ms=int((time.time() - start_time) * 1000),
        neo_json=neo.to_json(),
    )

    weekly_cost = db.get_daily_cost(today)
    cap = settings.budget.get('weekly_alert_usd', 2.50)
    logger.info(f"BUILD COMPLETE: {today} — HTML {len(html)}B, "
                f"teaser={'yes' if teaser_path else 'no'}, cost=${weekly_cost:.4f}")
    if weekly_cost > cap:
        logger.critical(f"BUDGET BREACH: ${weekly_cost:.4f} exceeds cap ${cap:.2f}")
        publisher.escalate_admin_alert(
            "Weekly budget cap exceeded",
            f"{today}: cost ${weekly_cost:.4f} exceeded cap ${cap:.2f} (LOD200 §6). "
            f"Edition still built; review token_usage.",
            family, settings, mock=args.mock,
        )

    db.close()
    return html_path
```

**Acceptance criteria:**
- [ ] AC-62: `cmd_weekly_build(args)` with `args.mock=True` runs end-to-end with **zero** real network calls except `_fetch_weather`'s (Assumption 14 — the one deliberate exception), producing a real `data/archive/html/<date>.html` file `>= 1000` bytes (`render()`'s own existing fatal-size guard, unchanged).
- [ ] AC-63: `llm.configure(...)` is called (verified via a mock/spy) exactly once, **before** the first call to `editor.generate_editorial(...)` — verified by call-order assertion, not just call-count.
- [ ] AC-64: `db.get_last_newsletter()` is called **before** `db.create_newsletter(today, 'building')` — verified via a mock's captured call order.
- [ ] AC-65: With `prior_row = {'date': today, 'puzzle_answer': '6'}` (a same-day re-run scenario), `prior_puzzle_answer` resolves to `None` (the `!= today` guard trips), not `'6'`.
- [ ] AC-66: With `prior_row = {'date': '<a week-ago date>', 'puzzle_answer': '6'}`, `prior_puzzle_answer` resolves to `'6'`.
- [ ] AC-67: `editor.generate_editorial(...)` raising `editor.EditorSchemaError` causes `cmd_weekly_build` to call `db.update_newsletter(today, status='build_failed')`, then re-raise the same exception (verified via `pytest.raises`) — the build does **not** silently continue past a broken editorial call.
- [ ] AC-68: `teaser.generate_teaser(...)` raising `TeaserRenderError` is caught; `cmd_weekly_build` does **not** raise, continues to `db.update_newsletter(..., status='ready', ...)`, and `publisher.escalate_admin_alert` is called exactly once with a subject containing `"Teaser generation failed"`.
- [ ] AC-69: `db.update_newsletter(...)`'s `puzzle_answer` kwarg equals `editorial['puzzle']['answer']` (THIS week's raw secret) — **not** `editorial['puzzle']['last_week_answer_reveal']` (the rendered text) — this is the exact inverse safety check of §2.10's AC-55, confirming the split is correct on BOTH the persistence side and the render side.
- [ ] AC-70: With `db.get_daily_cost` mocked to return a value greater than `settings.budget.get('weekly_alert_usd', 2.50)`, `publisher.escalate_admin_alert` is called exactly once with a subject containing `"budget"` (case-insensitive), and `cmd_weekly_build` still returns `html_path` normally (does not raise, does not change `status` back from `'ready'`).
- [ ] AC-71: With `db.get_daily_cost` mocked to return a value at or below the cap, `publisher.escalate_admin_alert` is **not** called for budget reasons.

### 2.12 `orchestrator.py` — `cmd_weekly_send()`, `cmd_weekly_survey()`, `cmd_health_check()`

**What to implement:**

```python
def cmd_weekly_send(args):
    """publisher.publish(): FTP index.html+teaser.png -> verify -> email
    -> WhatsApp group hook. Replaces m5_distributor.distribute()."""
    logger.info("=" * 60)
    logger.info("WEEKLY SEND starting")
    logger.info("=" * 60)

    config_dir = args.config or "config/"
    family = load_profiles(config_dir)
    settings = load_settings(config_dir)
    db = Database(args.db or "data/family.db")

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    newsletter = db.get_newsletter(today)
    if not newsletter:
        logger.error(f"No newsletter found for {today}. Run weekly-build first!")
        db.close()
        return
    if newsletter['status'] != 'ready':
        logger.error(f"Newsletter status is '{newsletter['status']}', expected 'ready'")
        db.close()
        return

    html_path = newsletter['html_path']
    neo_json = newsletter.get('neo_json')
    if not neo_json:
        logger.error("No NEO data in newsletter record")
        db.close()
        return

    neo = NEO(**json.loads(neo_json))

    teaser_path_guess = f"data/archive/teasers/{today}.png"
    teaser_path = teaser_path_guess if Path(teaser_path_guess).exists() else None
    if teaser_path is None:
        logger.warning(f"[orchestrator] No teaser found at {teaser_path_guess} — "
                        f"publishing without one")

    result = publisher.publish(html_path, teaser_path, neo, family, settings, mock=args.mock)

    if result.ftp_success:
        db.update_newsletter(today, status='distributed', public_url=result.public_url)
        logger.info(f"DISTRIBUTED: {result.public_url}")
    else:
        db.update_newsletter(today, status='send_failed')
        logger.error("DISTRIBUTION FAILED")

    for r in result.email_results:
        status = "✓" if r['success'] else "✗"
        logger.info(f"  {status} {r['member_id']} via {r['channel']}")

    wa = result.whatsapp_result
    logger.info(f"  WhatsApp: attempted={wa.get('attempted')} success={wa.get('success')} "
                f"channel={wa.get('channel')} error={wa.get('error')}")

    db.close()


def cmd_weekly_survey(args):
    """Kept per module scope B.4 — see publisher.send_survey()'s docstring
    (Assumption 11) for why this is a manually-triggered, email-only
    utility, not part of the automatic Friday flow."""
    logger.info("=" * 60)
    logger.info("WEEKLY SURVEY starting")
    logger.info("=" * 60)

    config_dir = args.config or "config/"
    family = load_profiles(config_dir)
    settings = load_settings(config_dir)
    db = Database(args.db or "data/family.db")

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    newsletter = db.get_newsletter(today)
    if not newsletter or not newsletter.get('neo_json'):
        logger.error(f"No newsletter for {today}")
        db.close()
        return

    neo = NEO(**json.loads(newsletter['neo_json']))
    results = publisher.send_survey(family, neo, settings, mock=args.mock)
    db.update_newsletter(today, status='feedback_collecting')
    for r in results:
        logger.info(f"  Survey → {r['member_id']}: {r['status']} ({r['channel']})")
    db.close()


def cmd_health_check(args):
    """Drops the sources.json check (config/sources.json is archived —
    §2.13); adds a profiles/*.md presence check (researcher.py raises
    TasteProfileMissingError if any are absent — a real, likely deploy-
    time failure mode on a fresh server clone, per REVIVAL_PLAN §4 step
    7's 'clone נקי')."""
    logger.info("HEALTH CHECK")
    config_dir = args.config or "config/"

    family = None
    try:
        family = load_profiles(config_dir)
        logger.info(f"  ✓ family.json: {len(family.members)} members")
    except Exception as e:
        logger.error(f"  ✗ family.json: {e}")

    try:
        load_settings(config_dir)
        logger.info(f"  ✓ settings.json loaded")
    except Exception as e:
        logger.error(f"  ✗ settings.json: {e}")

    if family:
        missing = [m.id for m in family.members
                   if not (Path("profiles") / f"{m.id}.md").exists()]
        if missing:
            logger.error(f"  ✗ profiles/: missing taste profiles for {missing}")
        else:
            logger.info(f"  ✓ profiles/: all {len(family.members)} taste profiles present")

    try:
        db = Database(args.db or "data/family.db")
        last = db.get_last_newsletter()
        logger.info(f"  ✓ DB: last newsletter {last['date']} ({last['status']})" if last
                    else "  ✓ DB: no newsletters yet")
        db.close()
    except Exception as e:
        logger.error(f"  ✗ DB: {e}")

    tmpl_path = Path("templates/newsletter.html.j2")
    logger.info(f"  ✓ Template: {tmpl_path}") if tmpl_path.exists() \
        else logger.error(f"  ✗ Template not found: {tmpl_path}")

    env_path = Path(".env")
    logger.info(f"  ✓ .env exists") if env_path.exists() \
        else logger.warning(f"  ⚠ .env not found (needed for API keys)")

    import shutil
    _, _, free = shutil.disk_usage(".")
    logger.info(f"  ✓ Disk: {free // (1024*1024)}MB free")
```

`main()` — drop the `webhook` verb + `--host`/`--port` args (Assumption 11), keep everything else identical:

```python
def main():
    parser = argparse.ArgumentParser(description='Family Newsletter Orchestrator')
    parser.add_argument('command', choices=[
        'weekly-build', 'weekly-send', 'weekly-survey',
        'daily-build', 'daily-send', 'daily-survey',  # backward compat aliases
        'health-check',
    ])
    parser.add_argument('--mock', action='store_true', help='Use mock data (no external calls)')
    parser.add_argument('--config', default='config/', help='Config directory')
    parser.add_argument('--db', default='data/family.db', help='Database path')

    args = parser.parse_args()

    commands = {
        'weekly-build': cmd_weekly_build,
        'weekly-send': cmd_weekly_send,
        'weekly-survey': cmd_weekly_survey,
        'daily-build': cmd_weekly_build,
        'daily-send': cmd_weekly_send,
        'daily-survey': cmd_weekly_survey,
        'health-check': cmd_health_check,
    }
    commands[args.command](args)


if __name__ == '__main__':
    main()
```

**Acceptance criteria:**
- [ ] AC-72: `cmd_weekly_send(args)` with no `newsletters` row for today logs an error containing `"weekly-build first"` and returns without calling `publisher.publish`.
- [ ] AC-73: `cmd_weekly_send(args)` with a `Path(f"data/archive/teasers/{today}.png")` fixture that does NOT exist calls `publisher.publish(html_path, None, ...)` (teaser_path is `None`, not the guessed path string) — verified via the mock's captured call args.
- [ ] AC-74: `cmd_weekly_send(args)` with `result.ftp_success = True` calls `db.update_newsletter(today, status='distributed', public_url=result.public_url)`; with `False`, calls `db.update_newsletter(today, status='send_failed')` — no other status value is ever set by this function.
- [ ] AC-75: `cmd_weekly_survey(args)` calls `publisher.send_survey` (not `publisher.publish`, not any `m5_distributor` symbol) and sets `status='feedback_collecting'`.
- [ ] AC-76: `cmd_health_check(args)` does not call `load_sources`/`get_scan_rules` anywhere (`grep -n "load_sources\|get_scan_rules" src/orchestrator.py` returns 0 matches) and does not raise even when `config/sources.json` does not exist on disk.
- [ ] AC-77: `cmd_health_check(args)` with a `family.json` defining 5 members and only 4 `profiles/*.md` files present on disk logs an error line containing the exact missing member id.
- [ ] AC-78: `python -m src.orchestrator webhook` (the removed verb) fails argparse validation (`choices=[...]` rejects it) with a non-zero exit code — confirms the verb is genuinely gone, not merely undocumented.
- [ ] AC-79: `python -m src.orchestrator daily-build --mock` and `python -m src.orchestrator weekly-build --mock` both dispatch to the identical `cmd_weekly_build` function object (backward-compat aliases unchanged).

### 2.13 Legacy archival — execution sequence

**What to implement:** per module scope item 6 and roadmap.yaml's WP006 note, executed **after** §2.7–§2.10's salvage/rewrite is complete and smoke-tested (`python -m src.orchestrator health-check` and `... weekly-build --mock` both succeed against the NEW orchestrator.py, importing nothing from the files about to move):

```bash
mkdir -p archive/legacy
git mv src/m2_scanner.py archive/legacy/m2_scanner.py
git mv src/m3_normalizer.py archive/legacy/m3_normalizer.py
git mv src/m6_feedback.py archive/legacy/m6_feedback.py
git mv src/m5_distributor.py archive/legacy/m5_distributor.py
git mv config/sources.json archive/legacy/sources.json
```

Five files (four named by roadmap.yaml's WP006 note, plus `m5_distributor.py` — this WP's own necessary addition, Assumption 10). `archive/legacy/poc.py` already exists from the prior WP (`FNL-S001-P001-WP003`) — this step adds alongside it, does not touch it.

**What is deliberately left in place, unedited, now-dead** (not this WP's file scope — §6): `src/m1_profiles.py`'s `load_sources()`/`get_scan_rules()` functions (only ever called by the now-archived scan pipeline; simply no longer imported/called by `orchestrator.py` after §2.7); `src/models.py`'s `SourceConfig`/`ScanRule` dataclasses (only constructed by the archived `load_sources`/`get_scan_rules`).

**Acceptance criteria:**
- [ ] AC-80: `git status` after this step shows all 5 files as renames (`R`), not delete+add, preserving git history (`git mv`, not `rm`+`add`).
- [ ] AC-81: `ls src/` no longer contains `m2_scanner.py`, `m3_normalizer.py`, `m6_feedback.py`, `m5_distributor.py`; `ls config/` no longer contains `sources.json`.
- [ ] AC-82: `ls archive/legacy/` contains all 5 newly-moved files plus the pre-existing `poc.py` (6 files total).
- [ ] AC-83: `python -m src.orchestrator health-check` and `python -m src.orchestrator weekly-build --mock` (run from a clean checkout, `venv` active) both complete with no `ImportError`, executed **after** this archival step — confirming §2.7's import rewire has zero remaining dependency on any archived file.
- [ ] AC-84: `grep -rn "m2_scanner\|m3_normalizer\|m6_feedback\|m5_distributor\|sources\.json" src/ config/ --include="*.py" --include="*.json"` (excluding `archive/`) returns zero matches anywhere in the live tree.

### 2.14 End-to-end content→section ownership map + `config/settings.json` edit

**What to implement:** the explicit table module scope item C requires, mapping each of LOD200 §2's 13 sections (plus WP007's bonus 14th) to its producing module in the pipeline this WP wires together.

| # | LOD200 §2 section | Producing module(s) | This WP's role |
|---|---|---|---|
| 1 | שער / Cover | `templates/newsletter.html.j2` (static markup) + `orchestrator._build_neo`/`_compute_edition_number` (date/edition) | Supplies `date_formatted`, `edition_number` |
| 2 | פתיח / Opener | `editor.py` (`opener`) | Passes through via `metadata['opener_text']` |
| 3 | פס משפחה / Family Strip | Template (Jinja-computed from `member_sections` item counts) | No dedicated producer needed |
| 4 | מזג אוויר / Weather | `orchestrator._fetch_weather` (salvaged, Basel removed) | §2.8 |
| 5 | פינה אישית ×5 / Personal Corners | `researcher.py` (`research_member`/`research_all_members`) | Maps into `member_sections` (§2.10) |
| 6 | גשר גילוי / Discovery | `editor.py` (bridge text) + `researcher.py` (anchor item, via `_map_discovery_bridges`) | §2.9 Assumption 6 |
| 7 | 🍿 מה רואים השבוע / Viewing | `researcher.py` (`screen_scout`) | Adapted via `_map_viewing` (§2.9 Assumption 5) |
| **8** | **🍽️ שולחן שישי / Family Table** | **UNOWNED — OPEN RECONCILIATION ITEM (Assumption 2)** | Wired to `''` (section suppressed) — see below |
| 9 | חידה / Puzzle | `editor.py` (`puzzle.*`) | Concatenated/split correctly (§2.10, Assumption 3) |
| **10** | **👨‍👩‍👧 מהמשפחה המורחבת / Extended Family** | **UNOWNED — OPEN RECONCILIATION ITEM (Assumption 2)** | Wired to `[]` (section suppressed) — see below |
| 11 | היום בהיסטוריה / Today in History | `editor.py` (`today_in_history.*`) | Concatenated (§2.10) |
| 12 | סקר / Survey | `editor.py` (`question_of_the_week.*`) | Joined into `survey_question` (§2.10) |
| 13 | סגירה + פוטר / Closer + Footer | `editor.py` (`closer`, `editor_credit`) + template (static footer) | Passes through |
| 14 (bonus, not in LOD200) | 📚 מהמדף שלנו / From Our Shelf | **UNOWNED — low priority, non-blocking** | Wired to `{}` (section suppressed) |

**Recommended follow-up for the two blocking gaps (items 8, 10) — for team_00, not built by this WP:**
- **Family Table (item 8):** extend `editor.py`'s existing single structured call (WP004 §2.2) with one new schema field, `family_table: {prompt: str, question: str}`, fed by a new, static user-prompt input (`active_family_threads: str` — the raw "חוטים משפחתיים פעילים עכשיו" text block already sitting, ready-to-use, in `profiles/family.md`, passed in by the orchestrator at zero additional cost). This stays within REVIVAL_PLAN's "1× editorial" cost model (no new LLM call) and reuses WP004's already-approved schema-validation/retry machinery. Estimated: a small WP004 addendum or a new ~1-page WP (e.g. `FNL-S001-P002-WP008`).
- **Extended Family (item 10):** a small, zero-LLM `researcher.curate_extended_family_items(family, profiles_dir)` reading `profiles/extended-family.md`'s `✓`-confirmed, non-sensitive entries. **Caveat found during this WP's research:** as of this spec's authoring, a direct read of `profiles/extended-family.md` did not surface a ready-made, safe, publishable headline matching LOD200 §2 item 10's own example ("Hadar's chamber-music win") — the file is presently a relationship-tree with `NEVER FOR NEWSLETTER`-flagged sensitive threads and open verification markers, not yet curated into publish-ready items. This is a **CONTENT-track gap** (REVIVAL_PLAN §3.7: content substrate is never LOD400-gated), not a code gap — recommend a parallel manual curation pass, not a blocker on this WP's own L-GATE_BUILD.
- **Shelf (bonus 14, item 14):** lowest priority since it is not LOD200-mandated; recommend deferring to Phase B/C rather than a pre-edition-1 fix.

**`config/settings.json` edit** — merge (never blind-overwrite — Assumption 13) these keys into the file's current state at build time. Final target end-state for the 3 affected top-level objects:

```json
"distribution": {
  "primary_channel": "email",
  "fallback_channel": "email",
  "whatsapp_group_name": "בית ולד 📰",
  "whatsapp_number": "972524242342",
  "admin_email": ""
},
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
  "research_max_continuations": 5,
  "provider": "anthropic",
  "provider_fallback": ["anthropic"],
  "anthropic_model": "claude-sonnet-5",
  "cursor_binary": "cursor-agent",
  "cursor_model": "grok-4",
  "cursor_timeout_seconds": 120,
  "editorial_max_tokens": 2500
},
"budget": {
  "weekly_alert_usd": 2.50,
  "monthly_alert_usd": 10.00
}
```

Notes for the builder: the first 14 keys of `ai` and both `budget` keys are **WP002's own edit** (§2.7 of that spec) — if WP002 was built first, those keys already exist with these exact values; this WP only needs to **add** the remaining 6 `ai` keys (`provider` through `editorial_max_tokens`) and the `distribution` object's changes, not touch what WP002 already wrote. `distribution.primary_channel`: `"whatsapp"` → `"email"` is **required** (module scope item 1 — a code-default change alone would not flip this, since the file currently has an *explicit* `"whatsapp"` value that always wins over a `.get(key, default)` fallback). `whatsapp_provider: "twilio"` (the old key) is **removed** — nothing in `publisher.py` reads it. `whatsapp_number: "972524242342"` is REVIVAL_PLAN §1 decision 5's known WAHA number ("052-424-2342") converted to E.164-without-`+` format for `wa.me`-link compatibility (matching the existing, unchanged Survey section's own `wa.me/{{ neo.metadata['whatsapp_number'] }}` usage). `schedule`, `content`, `newsletter`, `ftp` objects are **unchanged** — out of scope for this edit.

**Acceptance criteria:**
- [ ] AC-85: The section-ownership table above accounts for all 13 LOD200 §2 items plus the bonus 14th — cross-checked 1:1 against LOD200 §2's literal numbered list (no item skipped, no item double-counted).
- [ ] AC-86: `config/settings.json` after this edit is valid JSON (`json.load` succeeds).
- [ ] AC-87: `settings.distribution['primary_channel'] == 'email'`; `'whatsapp_provider'` key is absent from `distribution`.
- [ ] AC-88: All 20 `ai` keys listed above are present with the exact values shown, regardless of whether WP002's edit landed before or after this one (verified by applying this WP's edit against BOTH a settings.json fixture that already has WP002's 14 keys, and one that still has the OLD pre-WP002 `ai` object — both converge on the identical 20-key final state).
- [ ] AC-89: `budget.weekly_alert_usd == 2.50` (whether set by WP002 or, if WP002 has not yet landed, set by this edit as a safety net matching LOD200 §6's cap).
- [ ] AC-90: `schedule`, `content`, `newsletter`, `ftp` objects are byte-identical to their pre-edit values (no incidental changes).

## 3. Data model changes

**No new dataclass fields, no new DB schema, added by this WP.** This WP is a **consumer** of the data shapes WP001 (`llm.py` exceptions), WP002 (`token_tracker.research()`/`generate()`), WP003 (`researcher.py`'s item/pick dicts + the `watchlist`/`content_archive` DB methods), WP004 (`editor.py`'s structured dict), WP005 (`teaser.generate_teaser()`), and WP007 (`GeneratedContent`'s 4 new fields, `render()`'s new `settings=` param, `neo.metadata`'s new keys) already define — see the citations throughout §2. The only "schema-shaped" artifact this WP owns is `config/settings.json`'s content (§2.14, a config file, not a DB/dataclass schema) and `publisher.py`'s own two new dataclasses (`PublishResult`, and the informal `WhatsAppHookResult` contract — §2.1/§2.4, not a DB table).

Illustrative reference only (not new — already-existing `newsletters` table columns this WP writes into, unchanged DDL, per `src/db.py`, BACKFILL/kept):

```sql
-- already exists (src/db.py) — this WP writes these columns via
-- db.update_newsletter(), same method signature as the pre-rewire code
-- (date, status, greeting, puzzle, puzzle_answer, survey_question,
--  html_path, public_url, items_fetched, items_selected,
--  submissions_count, build_duration_ms, neo_json)
```

## 4. API contract changes

No HTTP endpoints (batch/cron pipeline). The relevant contracts are `publisher.py`'s public Python surface, `orchestrator.py`'s unchanged CLI surface (minus `webhook`), and the WAHA hook contract `src/whatsapp.py` (P003) must satisfy.

### `publisher.py` public surface

| Symbol | Kind | Signature | Notes |
|---|---|---|---|
| `publish` | function | `publish(html_path: str, teaser_path: Optional[str], neo: NEO, family: FamilyConfig, settings: Settings, mock: bool = False) -> PublishResult` | THE entry point. §2.6. Replaces `m5_distributor.distribute`. |
| `send_survey` | function | `send_survey(family: FamilyConfig, neo: NEO, settings: Settings, mock: bool = False) -> list` | Kept for CLI compat (§2.3). |
| `send_whatsapp_teaser` | function | `send_whatsapp_teaser(teaser_path: str, caption: str, settings: Settings, mock: bool = False) -> dict` | The WAHA hook (§2.4). |
| `escalate_admin_alert` | function | `escalate_admin_alert(subject: str, body: str, family: FamilyConfig, settings: Settings, mock: bool = False) -> bool` | §2.5. |
| `ftp_upload_file` | function | `ftp_upload_file(local_path: str, remote_filename: str, date: str, settings: Settings) -> str` | §2.2. Raises `FTPUploadError`. |
| `send_email` | function | `send_email(member: MemberProfile, neo: NEO, public_url: str, settings: Settings) -> bool` | §2.3, unchanged. |
| `PublishResult` | dataclass | see §2.1 | Replaces `DistributionResult`. |

### `src/whatsapp.py` — the REQUIRED contract for `FNL-S001-P003-WP001` (documented here; not implemented by this WP)

| Symbol | Kind | Signature | Notes |
|---|---|---|---|
| `send_group_image` | function | `send_group_image(image_path: str, caption: str, group_target: dict, settings: Settings, mock: bool = False) -> dict \| object` | `group_target = {'group_name': str, 'waha_number': str}`. Return value must expose `success: bool`, `channel: str`, `error: Optional[str]` (dict keys or object attributes — both accepted, §2.4). Auto-detected by `publisher.py` via `hasattr` — no edit to `publisher.py` needed once this exists. |

### `orchestrator.py` CLI surface (unchanged except `webhook` removed — Assumption 11)

| Verb | Before this WP | After this WP |
|---|---|---|
| `weekly-build` | M1→M2→M3→M4 | researcher→editor→assemble→render→teaser (§2.11) |
| `weekly-send` | `m5_distributor.distribute` | `publisher.publish` (§2.12) |
| `weekly-survey` | `m5_distributor.send_survey` | `publisher.send_survey` (§2.12) |
| `health-check` | includes `sources.json` check | drops it, adds `profiles/*.md` check (§2.12) |
| `daily-build`/`daily-send`/`daily-survey` | aliases | unchanged aliases |
| `webhook` | `m6_feedback.run_webhook_server` | **removed** (Assumption 11) |

## 5. Error handling requirements

| Error case | Expected behavior |
|---|---|
| `llm.configure()` never called before `editor.generate_editorial()` | Would raise `LLMConfigError` — **prevented by construction**: `cmd_weekly_build` calls `llm.configure(...)` immediately after constructing `tt`, before any researcher/editor call (AC-63). |
| `researcher.research_all_members`/`screen_scout` raise (should not — both catch their own per-member/per-slot errors per WP003 §1 Assumption 7) | Not specially caught by `cmd_weekly_build` — an uncaught exception here is a genuine bug in a sibling WP, and should surface loudly (build fails, non-zero exit) rather than be silently swallowed by this integrator. |
| `editor.generate_editorial()` raises `llm.LLMError` (any subtype) or `editor.EditorSchemaError` | Caught, `status='build_failed'` recorded, exception re-raised — a fatal build failure (AC-67). An edition with no editorial voice at all is not worth shipping. |
| `teaser.generate_teaser()` raises `TeaserRenderError` | Caught, `escalate_admin_alert` fired, build continues with `teaser_path=None` — degraded, not fatal (AC-68; Assumption 9). Downstream, `publisher.publish` gracefully skips the teaser FTP step and the WhatsApp hook (AC-33). |
| `render()` raises `RuntimeError` (its own pre-existing `< 1000 bytes` fatal-size guard) | Not caught by this WP — propagates, consistent with the OLD `cmd_weekly_build`'s behavior (it never caught this either); `newsletters.status` stays `'building'` (a stuck-in-progress row is a visible, honest failure signal for a human to investigate, same as before this WP). |
| Weekly cost exceeds `settings.budget.weekly_alert_usd` | Logged CRITICAL, `escalate_admin_alert` fired (Assumption 9) — does **not** block the build from completing or `weekly-send` from publishing (AC-70/71). |
| `publisher.publish()`: HTML FTP upload never reaches HTTP 200 (after 1 retry) or the connection itself fails after `retry_count` attempts | `ftp_success=False`, `public_url=''`, email is never attempted, `weekly-send` records `status='send_failed'` (AC-30/31/74). |
| `publisher.publish()`: teaser FTP upload/verify fails | `teaser_public_url=None`; email still proceeds; WhatsApp hook is skipped with `error='no_teaser_available'` (AC-32/33). |
| `publisher.publish()`: a member has no email on file | That member's `email_results` entry is `success=False, error='No email on file'`; other members are unaffected (AC-35). |
| `src/whatsapp.py` not present, or present but raises | The hook returns a safe, honestly-labeled failure dict; never raises out of `publish()` (AC-16, AC-20). |
| `escalate_admin_alert()` itself fails (no admin email resolvable, or SMTP misconfigured, or the send itself raises) | Returns `False`, logs an error, **never raises** — a failed alert must not crash the build/send it is reporting on (AC-26, AC-27). |
| `neo.trivia['answer']` / `newsletters.puzzle_answer` mismatch risk | **Prevented by construction, not caught at runtime** — §2.10 AC-55 and §2.11 AC-69 are the two-sided guarantee that the rendered reveal and the persisted secret can never be swapped; this is a code-review-time property (§7's cross-engine check re-verifies it explicitly), same class of guarantee as WP001's `-f` flag AC-27. |
| Template's "תשובה מהשבוע שעבר:" label prefix + `editor.py`'s own already-worded `last_week_answer_reveal` sentence both render together | **Known, accepted cosmetic redundancy** (Assumption 3) — mildly repetitive but correct and readable Hebrew, not a functional defect. Not fixed here (would require a WP007/template edit, outside this WP's file scope). Recommended one-line future fix: WP007 (or a follow-up) removes the hardcoded label prefix from the template, since `editor.py`'s content now supplies its own framing. |
| `profiles/<member_id>.md` missing on a fresh server deploy | Not caught specially by `cmd_weekly_build` (propagates via `researcher.research_member`'s own `TasteProfileMissingError`, per-member, non-fatal — WP003 §1 Assumption 7). Proactively surfaced earlier by `health-check`'s new profiles check (AC-77), so a deploy-verify step can catch it before the first Friday cron run. |
| `config/sources.json` referenced anywhere after archival | Prevented by construction — `orchestrator.py` no longer imports `load_sources`/`get_scan_rules` (AC-76); `m1_profiles.py` itself is unedited and still defines them harmlessly (dead code, §6). |

## 6. Out of scope (explicit)

- **The actual editorial content for "🍽️ שולחן שישי / Family Table" and "👨‍👩‍👧 מהמשפחה המורחבת / Extended Family" (LOD200 §2 items 8, 10) and "📚 מהמדף שלנו / From Our Shelf" (WP007's bonus 14th)** — genuinely unowned by any WP in the current set (Assumption 2, §2.14). This WP wires safe, template-suppressing empty defaults and documents the recommended fix in full; it does **not** implement that fix itself (writing new prompt/schema logic into `editor.py` or new curation logic into `researcher.py` is those WPs' file scope, not this integrator's — inventing it here would be exactly the "silently invent a producer" outcome the task brief explicitly forbids). **Flagged for team_00 as a pre-edition-1 blocking gap for items 8/10** (LOD200 §3's "All 13 sections present" happy-path criterion cannot be met without it); item 14 (Shelf) is non-blocking.
- **`src/whatsapp.py` itself** (the real WAHA `sendImage` integration, docker setup, group linking, number binding) — `FNL-S001-P003-WP001`, OPS, entirely separate. This WP builds and fully specifies the *hook* (`publisher.send_whatsapp_teaser`, the `send_group_image` contract, §2.4) that P003's module must satisfy — nothing more.
- **The server cron path update, the clean deploy to `/data/projects/family-newsletter`, `.env` provisioning on the server** — `FNL-S001-P003-WP002`, OPS. `run.sh` and the crontab entries are unchanged (module scope B.4) by design.
- **Any internal change to `llm.py`, `token_tracker.py`, `researcher.py`, `editor.py`, `teaser.py`, or `templates/newsletter.html.j2`/`m4_renderer.py`** — each is that sibling WP's own file scope (WP001/WP002/WP003/WP004/WP005/WP007 respectively). This WP only *calls* their already-specified public interfaces.
- **Editing `src/m1_profiles.py` or `src/models.py`** to remove the now-dead `load_sources()`/`get_scan_rules()`/`SourceConfig`/`ScanRule` symbols (§2.13) — left in place, unused, harmless; a future cleanup WP may remove them. Not touched here since neither file is in this WP's file scope (publisher.py + orchestrator.py only).
- **A CI-friendly, fully-offline mock mode for `_fetch_weather()`** — not added (Assumption 14); it makes a real, free, keyless Open-Meteo call even under `--mock`, matching the pre-existing `m3_normalizer.py` behavior exactly.
- **Populating the `newsletter_items` table** — confirmed dead (zero `INSERT` call sites) in the pipeline being replaced; this WP does not add one either (Assumption 12).
- **Fixing the template's redundant "תשובה מהשבוע שעבר:" label** (§5) — a one-line future template edit, outside this WP's file scope (`templates/newsletter.html.j2` belongs to WP007).
- **Real-time re-verification of `screen_scout()`'s self-reported Netflix/Prime availability or Hebrew-subtitle claims** — WP003's own stated limitation (its §6), unaffected by this WP's `_map_viewing` adapter, which passes the claims through as-is.
- **Deleting `archive/legacy/*.py` outright (vs. archiving)** — matches the treatment established by `FNL-S001-P001-WP003`'s prior archival of `poc.py`; these 5 files stay as historical reference, not live code.

## 7. Test requirements

- **Unit** (no real network/FTP/SMTP calls — mock `ftplib.FTP`, `requests`, `smtplib`/`env_compat.smtp_deliver_message`, `Database`, and every sibling module's public entry point): every AC in §2.1–§2.14 above. Priority/highest-risk targets: the puzzle-answer split (§2.10 AC-55, §2.11 AC-69 — the single easiest place for a corner-cutting builder to reintroduce the self-spoiling bug described in Assumption 3), the `llm.configure()` call-ordering requirement (AC-63/64), the FTP-verify-retry-once semantics (§2.2 AC-08–AC-11), and the WhatsApp hook's soft-import auto-activation (§2.4 AC-16–AC-20). Illustrative skeletons (pytest + pytest-mock, matching every sibling spec's established convention):

```python
def test_build_neo_never_leaks_this_weeks_secret_into_rendered_field(mocker):
    from src.orchestrator import _build_neo
    family = mocker.Mock(family_name="בית ולד",
                          members=[mocker.Mock(id="nimrod", nickname_newsletter="נימרוד",
                                                name_en="Nimrod", language_preference="he")])
    settings = mocker.Mock(distribution={})
    editorial = {
        "opener": "<strong>שלום</strong>", "closer": "להתראות",
        "puzzle": {"intro": "i", "question": "q", "answer": "SECRET-6",
                   "last_week_answer_reveal": "תשובת שעבר: 5!"},
        "today_in_history": {"fact": "f", "family_idea_callout": "c"},
        "question_of_the_week": {"poll_question": "p", "poll_options": []},
        "teaser_caption": "t {EDITION_LINK}", "editor_credit": "עורכת: צליל",
        "editors_choice": {}, "discovery_bridges": [],
    }
    neo = _build_neo(family, settings, "2026-07-24", "יום שישי", {}, {}, editorial, [])
    assert neo.trivia["answer"] == "תשובת שעבר: 5!"
    assert "SECRET-6" not in neo.trivia["answer"]


def test_cmd_weekly_build_calls_llm_configure_before_editor(mocker):
    import src.orchestrator as orch
    calls = []
    mocker.patch.object(orch, "load_profiles", return_value=mocker.Mock(
        family_name="x", members=[]))
    mocker.patch.object(orch, "load_settings", return_value=mocker.Mock(
        ai={}, distribution={}, budget={}))
    mocker.patch.object(orch, "Database")
    mocker.patch.object(orch, "TokenTracker")
    mocker.patch.object(orch.llm, "configure", side_effect=lambda *a, **k: calls.append("configure"))
    mocker.patch.object(orch.researcher, "research_all_members", return_value={})
    mocker.patch.object(orch.researcher, "screen_scout", return_value={})
    mocker.patch.object(orch.editor, "generate_editorial",
                         side_effect=lambda *a, **k: calls.append("editorial") or {
                             "opener": "", "closer": "",
                             "puzzle": {"intro": "", "question": "", "answer": "",
                                        "last_week_answer_reveal": ""},
                             "today_in_history": {"fact": ""}, "teaser_caption": "",
                             "question_of_the_week": {"poll_question": "", "poll_options": []},
                             "editor_credit": "", "editors_choice": {}, "discovery_bridges": [],
                         })
    mocker.patch.object(orch, "render", return_value="x" * 2000)
    mocker.patch.object(orch, "save_html", return_value="path.html")
    mocker.patch.object(orch.teaser, "generate_teaser", return_value="teaser.png")
    args = mocker.Mock(mock=True, config=None, db=None)

    orch.cmd_weekly_build(args)

    assert calls == ["configure", "editorial"]


def test_publish_skips_email_when_html_never_verifies(mocker):
    import src.publisher as pub
    mocker.patch.object(pub, "_upload_and_verify", return_value=None)
    email_spy = mocker.patch.object(pub, "send_email")
    family = mocker.Mock(members=[mocker.Mock(id="nimrod", email="n@x.com")])
    neo = mocker.Mock(date="2026-07-24", metadata={})

    result = pub.publish("html.html", None, neo, family, mocker.Mock(), mock=False)

    assert result.ftp_success is False
    email_spy.assert_not_called()
```

- **Integration** (real repo state, no real network — `--mock`): `python -m src.orchestrator weekly-build --mock` followed by `python -m src.orchestrator weekly-send --mock` run end-to-end against a scratch `data/family.db`, asserting: a real `data/archive/html/<date>.html` file is produced (`>= 1000` bytes — `render()`'s existing guard); `newsletters.status` transitions `building → ready → distributed`; `neo_json` round-trips through `NEO(**json.loads(...))` in `cmd_weekly_send` without error; the puzzle-answer split (this week's secret persisted, last week's reveal rendered) holds across two consecutive `--mock` builds a week apart (second build's rendered puzzle-answer text differs from the first build's persisted secret).
- **Cross-engine validation** (required at L-GATE_VALIDATE per Iron Rule #1 — the validator engine must differ from the builder engine): confirm `src/publisher.py` exports exactly `publish`, `send_survey`, `send_whatsapp_teaser`, `escalate_admin_alert`, `ftp_upload_file`, `send_email`, `PublishResult` as its primary public surface, and that `grep -n "TWILIO\|twilio\|Twilio" src/publisher.py` is empty (AC-12); confirm `neo.trivia['answer']` and `newsletters.puzzle_answer` can **never** be assigned from the same `editorial['puzzle']` key in `_build_neo`/`cmd_weekly_build` (re-verify AC-55/AC-69 together, since a builder "simplifying" one to match the other is the single highest-risk regression in this whole WP); confirm `llm.configure(...)` genuinely precedes every `editor.generate_editorial(...)` call site, with no code path that could reach the editorial call first; confirm the WhatsApp hook's soft-import (`try: from . import whatsapp except ImportError`) never raises when `src/whatsapp.py` is absent, and that `send_whatsapp_teaser` is **always** attempted as a single family-GROUP-level call, never per-member (re-checking that the old per-member Twilio loop shape was not accidentally reintroduced); confirm `git diff` for this WP touches only `src/publisher.py` (new), `src/orchestrator.py`, `config/settings.json` (the additive merge, §2.14), and the 5 `git mv` archival operations (§2.13) — no incidental edits to any sibling WP's own files (`llm.py`, `token_tracker.py`, `researcher.py`, `editor.py`, `teaser.py`, `templates/newsletter.html.j2`, `m4_renderer.py`, `m1_profiles.py`, `models.py`, `db.py`); confirm the section-ownership table (§2.14) is cross-checked 1:1 against LOD200 §2's literal 13-item list with no item silently dropped.

## 8. Consuming team sign-off
> I confirm this spec is executable and unambiguous. All open questions are resolved.
> **Signature:** familynewsletter_build | [PENDING — sign at L-GATE_SPEC]

---

## Cross-Engine Validation — Iron Rule

Documents at LOD400+ require cross-engine validation at L-GATE_VALIDATE.
**The validator engine MUST differ from the builder engine — IRON RULE.**
No exception. No waiver. See `gates/L-GATE_VALIDATE_VALIDATE_AND_LOCK.md`.
