---
id: HANDOFF_team_100_TO_NEXT_SESSION_POST_CUTOVER_2026-07-22_v1.0.0
type: HANDOFF
from_team: team_100
to_team: team_100
date: 2026-07-22
next_step: "Author the P002 LOD400 build specs (llm.py, token_tracker, researcher, editor, teaser, orchestrator/publisher) from the LOD200 contract, then hand each to Grok/Cursor on Mac to build."
handoff_to: team_100
handoff_context_pointer: [_aos/roadmap.yaml, _aos/context/PROJECT_CONTEXT.md, _aos/work_packages/FNL-S001-P001-WP001/LOD200.md, REVIVAL_PLAN_2026-07-22.md, _COMMUNICATION/team_120/OPEN_QUESTIONS_INDEX_team_100_TO_team_120_2026-07-22_v1.0.0.md]
---

# Handoff — team_100 to the next team_100 session, post-cutover

## 0. Why this file exists

This is a self-contained context transfer for whichever session picks this
project up next — read it FIRST, before anything else, if you're arriving
after the folder cutover ran. Two independent things changed at once on
2026-07-22 and either one could leave a session disoriented:

1. **The repo moved.** From `/Users/nimrod/Documents/AOS_V5/family-newsletter`
   to `/Users/nimrod/Documents/AOS_V5/family-newsletter` (team_120 §5 ruling,
   required by hub Check 74 for an enabled project).
2. **Claude Code's project-memory slug migration is UNVERIFIED.** The memory
   dir was moved from `~/.claude/projects/-Users-nimrod-Documents-Family-Newsletter/`
   to `~/.claude/projects/-Users-nimrod-Documents-AOS_V5-family-newsletter/`
   as part of the same cutover, but end-to-end confirmation that a fresh
   session at the new path actually reads that migrated memory has NOT
   happened yet as of this writing.

If memory came through fine, this file is redundant — skip to §4 (what's
next) and treat this as a sanity-check. **If memory did NOT come through
(you're a "cold" session with no recollection of this project), this file
is your insurance policy** — it lives inside the repo itself, so it moved
with the `mv` in step 4 of the cutover, guaranteed, independent of whatever
happened to `~/.claude/projects/`.

## 1. What this project is

**Family Newsletter** (Hebrew: בית ולד) is a personalized weekly Hebrew
newsletter for the five Wald household members — a per-member content
section by taste, cross-member "discovery bridges," a math riddle for one
of the kids, a family Friday-table conversation starter, weekly
watch-picks, and a WhatsApp teaser delivered to a family group. It's a
Python app (modular pipeline being rebuilt around an LLM-driven researcher
+ editor + teaser-image + publisher chain, replacing an old RSS-scraping
design), SQLite "family memory," a Jinja2 comic-style HTML template,
published via FTP (nimrod.bio) and WhatsApp (WAHA self-hosted bridge), run
weekly on a Friday cron on waldhomeserver. It's an AOS L0 spoke project
(hub = `/Users/nimrod/Documents/AOS_V5/agents-os`).

## 2. Standing governance laws (binding, team_00 ruling 2026-07-22)

These are baked into `_aos/context/PROJECT_CONTEXT.md` §"Governance baked
in" — restated here so this handoff is self-contained:

1. **LOD depth by material type.** Content / data / family-characterization
   → **LOD200 + cheap validation only** (this is the one deliberate
   exception to the canon minimum). Templates, rules, code, config, and
   installs — ANY code write or edit — → **full LOD400 + cross-engine
   validation, no exceptions.** This is intentionally stricter than the AOS
   canon floor: zero-ambiguity LOD400 specs are the token-saving lever that
   lets a lazy/flat-cost builder build correctly on the first pass.
2. **Engine routing.** Builder = **Grok via Cursor CLI on the Mac**
   (flat-cost, needs zero-ambiguity LOD400 input to work well). Heavy spec
   authoring / editing / validation = **Claude, high effort (Sonnet)**;
   **Opus only where truly required.** Cross-engine validation (Iron Rule
   #1) is satisfied structurally by **Grok builds → Claude validates** —
   this is canonically required, not merely a cost optimization, and
   Claude's role at runtime (once built) is validation, not authorship.
3. **Track / archetype split.** New pipeline modules = STANDARD · edition
   content = CONTENT · WAHA/server work = OPS · kept/inherited code
   (renderer, db, template) = BACKFILL (as-built LOD500, no retroactive
   spec). Tagged `CLASS=…` in each WP's `notes:` field in `_aos/roadmap.yaml`.
4. **Spec-production flow.** The team (you) authors the specs.
   **team_00 validates at the end** of a batch — this is not a per-spec
   pre-approval bottleneck. Produce first, then bring the batch to team_00.

## 3. Status ledger (as of 2026-07-22, post-cutover)

| Item | Status |
|---|---|
| Family harvest (ChatGPT export, social scans, direct interviews) | **Done** — round 1. See `profiles/` |
| Taste profiles (nimrod, michal, shaked, maayan, tzlil, family, extended-family, family-friends) | **Done** — round 1, content substrate. `_aos/roadmap.yaml` WP `FNL-S001-P005-WP002` = COMPLETE |
| `_aos/` governance provisioning | **Done** — born-canonical `family-newsletter` id, L0 profile, validated 0 FAIL, landed on `main` (`dee2ffc`) |
| LOD200 product contract (`FNL-S001-P001-WP001`) | **APPROVED** — `_aos/work_packages/FNL-S001-P001-WP001/LOD200.md`. This is the SSOT the P002 LOD400 build specs derive from. **Housekeeping note:** the file's own frontmatter `status:` field still literally reads `DRAFT — awaiting team_00 validation` as of this writing — a stale field, not a real blocker; sync it to `APPROVED` next time you touch that file. |
| WP002 (env/URL fix) + WP003 (archive dead `poc.py`) | **Done**, committed locally (`16fe36e`, `2a4a0de`) — see `_aos/work_packages/FNL-S001-P001-WP002-003_ASBUILT.md`. Were 2 commits ahead of `origin/main`, unpushed, until the cutover runbook's step 6 pushed them along with the rename sweep. **Housekeeping note:** `_aos/roadmap.yaml`'s own `status:` field for both WPs still literally reads `PLANNED` — stale, same class of issue as the LOD200 field above; sync both next time you're in `_aos/roadmap.yaml`. |
| Folder cutover (repo → `/AOS_V5/family-newsletter`, GitHub rename, `data/family.db` → `data/family.db`, spelling sweep) | **Done** — see `CUTOVER_RUNBOOK.sh` + `CUTOVER_GUIDE.md` in the scratchpad this was executed from (or wherever they were archived after the run). Verify against the runbook's own step 7 checklist if anything here looks off. |
| Claude Code memory-slug migration | **UNVERIFIED / provisional** — see §0 above. Confirm end-to-end before trusting it. |

## 4. What's next

**P002 — new pipeline (CLASS=STANDARD, code → full LOD400 required).**
Author the LOD400 build specs, in this order (each derives from the LOD200
contract at `_aos/work_packages/FNL-S001-P001-WP001/LOD200.md`), then hand
each off to Grok/Cursor on the Mac to build, with Claude validating the
result before it's trusted:
1. `llm.py` — dual-driver layer (Cursor/Grok default + Anthropic fallback,
   prompt-in/JSON-out)
2. `token_tracker` — update for `claude-sonnet-5` pricing,
   `research()` with server tools + `pause_turn`, `web_search` cost logging
3. `researcher.py` — 5x `research_member` two-step gather+critique;
   watchlist + screen-scout sections
4. `editor.py` — editorial call, structured output, `--mock` mode
5. `teaser.py` — Pillow 1080×1350 cover card, Hebrew RTL via raqm/bidi
6. orchestrator rewire + `publisher.py` (FTP + email kept, Twilio removed)

**P003 — WhatsApp + server (CLASS=OPS).** WAHA docker on waldhomeserver +
"בית ולד 📰" group wiring + `whatsapp.py` (`sendImage`). **Critical:** this
is also where the existing Friday cron on waldhomeserver gets repointed —
it currently still targets `/data/projects/family-newsletter` (doesn't
exist on disk; prior deploy archived 2026-07-18), and needs to move to
`/data/projects/family-newsletter` alongside restoring a live deploy there.
Do not forget this — the cron is real and already scheduled
(`0 9 * * 5` build / `0 12 * * 5` send, `TZ=Asia/Jerusalem`); it's currently
a silent no-op, not absent.

**P004 — BACKFILL.** As-built LOD500 documentation for kept code:
`src/m4_renderer.py`, `src/db.py`, `templates/newsletter.html.j2` +
`src/env_compat.py`. Already marked COMPLETE in `_aos/roadmap.yaml` (P004
WP001–WP003) — no retroactive spec needed, just keep the as-built docs
current if any of these files change during P002 work.

## 5. Read order for this session

1. `CLAUDE.md` (repo root) — mandatory session startup, identity,
   directory authority, AOS hub reference
2. `_aos/roadmap.yaml` — SSOT for WP state; find the active/next WP here
3. `_aos/context/PROJECT_CONTEXT.md` — domain background, team entry,
   governance laws (§2 above is copied from here)
4. `_aos/work_packages/FNL-S001-P001-WP001/LOD200.md` — the product
   contract everything derives from
5. `REVIVAL_PLAN_2026-07-22.md` — the full rethink/architecture narrative
   behind the LOD200 contract (repo root, currently untracked — moves with
   the repo regardless)
6. `profiles/` — per-member taste profiles, the content substrate

## 6. Open items pointer

`_COMMUNICATION/team_120/OPEN_QUESTIONS_INDEX_team_100_TO_team_120_2026-07-22_v1.0.0.md`
— 26 tracked open items from the characterization sweep, of which only
**4 are marked `[blocks-edition-1]`**: (1) get Yoyo's consent before
naming her nail business in the newsletter, (2) drop Basel from the
weather section — Shaked is home now, (3) resolve WAHA Core vs. Plus for
`sendImage` support, (4) verify `cursor-agent` headless on waldhomeserver
(auth, `web_search` availability, JSON output stability, Hebrew quality).
Everything else in that index is `[nice-to-have]` or explicitly
`[future-loop]` (deferred to Phase B/C) — do not let those block P002/P003.

## 7. Edition #1 scope decision (binding, team_00 2026-07-22)

**FULL section set — all 13 sections**, per `LOD200.md` §2 (Cover, Opener,
Family Strip, Weather, 5× Personal Corner, Discovery Bridge, Viewing,
Family Table item, Puzzle, Extended Family, Today in History, Survey,
Closer/Footer). **Completeness over speed was the explicit call** — a
**~10-day timeline was accepted** rather than shipping a trimmed edition
faster. Content quality ~70%-on-target is the accepted bar for edition #1
(the Phase B feedback loop is what refines it toward 90%+, not a bigger
LOD200 spec now) — "precise + fast from static profiles" was explicitly
rejected as the goal.
