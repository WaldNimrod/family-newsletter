---
id: BRIEF_team_120_TO_family_newsletter_PROVISIONING_COMPLETE_AND_NEXT_2026-07-22_v1.0.0
type: BRIEF
from_team: team_120 (Ambassador) + team_00
to: family-newsletter project team (familynewsletter_arch/_build/_val)
date: 2026-07-22
re: _aos/ provisioning COMPLETE → GO for dev; what we need from you; kicking off the folder rename
dev_phase_eta: 48h
---

# Brief to the Family-Newsletter project team — provisioning complete, dev begins

## 0. Bottom line
The project's AOS infrastructure (`_aos/`) is **built, validated (0 FAIL), and landed on `main`**. The hard blocker that froze the build is cleared. **GO for the dev phase received, ETA 48h.** Edition #1 can move.

## 1. What was done (the `_aos/` provisioning)
- **Born-canonical identity:** project id = **`family-newsletter`** (display "Family Newsletter" / "בית ולד"). ⚠️ **"family" is a retired typo — it appears in NO `_aos/` artifact.** Team ids: `familynewsletter_{sd,arch,build,val}`. WP ids carry the **`FNL-`** prefix (hub-DB primary-key collision safety).
- Profile **L0**, archetype SOFTWARE, lean-kit `3.4.0+e7d4a39`, Model-B governance cache hydrated (299 files) + tracked stamp.
- Validated: `validate_aos.sh` → **0 FAIL** (43 PASS / 33 SKIP). Landed on `main` (`dee2ffc`) and pushed to origin.
- **Your in-flight revival work (M4/M5 fixes, `data/`, `profiles/`) was left untouched** — still uncommitted, exactly as it was.
- The spoke is registered in the hub (`projects.yaml`) with **`enabled: false`** for now (see §5) — inert, affects no fleet tooling.

## 2. How we work from here — standing laws baked in (binding)
In `_aos/context/PROJECT_CONTEXT.md`:
1. **Characterization depth by material type:** content/data/family-characterization → **LOD200** + cheap validation. **Any code write/edit → full LOD400 + cross-engine validation.** (Intentionally stricter than the canon minimum — zero-ambiguity LOD400 is the token-saving lever.)
2. **Engine routing:** builder = **Grok/Cursor**; spec authoring/validation = **Sonnet high-effort**; Opus only when truly required. **Grok builds → Claude validates** (Iron Rule #1, cross-engine — canonically required, not just cost).
3. **Track split:** new pipeline = STANDARD · edition = CONTENT · WAHA/server = OPS · kept code (M4/M5/db) = BACKFILL (as-built LOD500, no retro plan).
4. **Spec flow:** you author the specs; **team_00 validates at the end** (no per-spec pre-approval).

## 3. What's planned — S001 / Phase A registry (seeded in `_aos/roadmap.yaml`)
16 initial WPs under S001, classified in `notes:` as `CLASS=…`:
- **P001 — product contract + housekeeping:** `FNL-S001-P001-WP001` = **LOD200 product contract** (what edition #1 *must* contain + happy-path acceptance criterion + weekly `cost_cap`) — *the small missing gate everything hangs on*; + commit the 10.5 FTP fix + archive dead code.
- **P002 — new pipeline (STANDARD, code→LOD400):** `llm.py` (cursor/grok + anthropic fallback), `token_tracker`, `researcher.py`, `editor.py`, `teaser.py`, orchestrator + `publisher.py`.
- **P003 — WhatsApp + server (OPS):** WAHA docker + group + `whatsapp.py`; deploy to `/data/projects/family-newsletter` + Friday cron.
- **P004 — BACKFILL:** `m4_renderer`, `db`, template + `env_compat` (as-built LOD500).
- **P005 — content (CONTENT):** edition #1; round-1 taste profiles (already harvested — content substrate).

*Per-WP LOD specs are your build-phase work. The registry records id/label/track/status/spec_ref=TBD only.*

## 4. What we need from you (to move edition #1)
1. **LOD200 product contract** (`FNL-S001-P001-WP001`) — the blocking, missing input: what edition #1 must contain, the "good-enough" happy-path acceptance criterion, and the weekly token/cost cap. This is the contract that blocks build.
2. **Config updates from the interview** (REVIVAL_PLAN §5): **Shaked is back home → remove Basel from the weather**; confirm with Yoyo before mentioning her nail business in an edition.
3. **WAHA:** confirm number **052-424-2342** + create the "בית ולד 📰" group; decide Core vs Plus for `sendImage`.
4. **Verify `cursor-agent` headless on waldhomeserver** (browserless auth, web_search in non-interactive mode, stable JSON, Grok Hebrew quality) — a precondition for the research stage.
5. **First test group:** Nimrod + Tzlil, and only after a successful edition — all five.

## 5. 🚀 Kicking off the folder rename (team_00 directive — starting now)
Today: folder `Family Newsletter/family-newsletter`, remote `family-newsletter`, outside `/AOS_V5/`. That is why the registry entry is `enabled: false` (Check 74 requires an enabled project's `local_path` under `/AOS_V5/`). **team_00 directed kicking this off.** The runbook (team_120 + team_60 coordinated):
1. Rename/move the repo to **`/Users/nimrod/Documents/AOS_V5/family-newsletter`**.
2. Rename the GitHub repo: `family-newsletter` → `family-newsletter` (+ update the local remote URL).
3. Update `local_path` in hub `_aos/projects.yaml` + **flip `enabled: true`** (now passes Check 74).
4. Update every script/config reference to the new path/remote.

**What we need from you to start:** an execution window (when the folder can be moved without disrupting the active build session) + confirmation of the final GitHub repo name. team_120 executes the hub side; team_60 the git/deploy side.

## 6. Milestones
| Phase | Content |
|---|---|
| **S001 / Phase A** | First real edition to the group — LOD200 contract + new pipeline + WAHA/server + cron + BACKFILL |
| S002 / Phase B | The loop — reply polling, per-item feedback, monthly profile editor |
| S003 / Phase C | Polish (monthly character, archive, WhatsApp poll, monitoring, sub-domain) |

*Sources: REVIVAL_PLAN_2026-07-22.md, STYLE_GUIDE.md §1, the mandate. Provisioned + validated by team_120, 2026-07-22.*
