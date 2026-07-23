---
id: BUILD_DIRECTIVE_team_00_TO_team_110_P002_PIPELINE_2026-07-23_v1.0.0
type: BUILD_DIRECTIVE
from_team: team_00 / team_100
to_team: team_110 (Cursor Cloud Grok builder)
date: 2026-07-23
build_base: "origin/main (latest). The 7 LOD400 specs are @ ef0e366, unchanged."
model: cursor-grok-4.5-high
goal: "Build the P002 pipeline = edition-1 INFRASTRUCTURE (goal #1). Grok builds each WP → Claude validates → PR per WP. Runtime stays on waldhomeserver. Content (goal #2) + media integration (goal #3) follow separately."
inputs:
  - _COMMUNICATION/team_100/VALIDATION_REPORT_team_00_2026-07-22_P002_7SPEC_BATCH_v1.0.0.md   # full per-WP fix detail
  - _COMMUNICATION/team_110/CAPABILITIES_REPORT_team_110_CURSOR_CLOUD_2026-07-22_v1.0.0.md     # env constraints
  - _COMMUNICATION/team_00/MEDIA_BRIEF_team_100_TO_team_00_SKIPPER_CAT_ASSETS_EDITION1_2026-07-23_v1.0.0.md
  - _aos/work_packages/FNL-S001-P002-WP001..WP007/LOD400_spec.md
routing: "team_00 launches this in Cursor Cloud (manual paste OR a one-time Automation). Claude Code cannot trigger Cloud directly (no CURSOR_API_KEY in that session)."
---

# BUILD DIRECTIVE — P002 pipeline (Cursor Cloud, Grok)

## 0. Mission & guardrails
Build the 7-WP Python pipeline that generates the weekly Hebrew family newsletter.
- **Grok-first** (conserve Sonnet tokens): Grok builds; a Claude pass validates each WP.
- **One WP per branch → PR → team_00 merge.** Never two agents on the same branch (isolated VMs don't protect shared branches).
- **Model:** `cursor-grok-4.5-high` (NOT `grok-4` — invalid).
- **No live Anthropic on Cloud** (`api.anthropic.com` TLS-RST from Cloud egress): all pytest mocks the Anthropic client. Live-API smoke tests (WP002) run on **Mac/waldhomeserver**, out of this Cloud build.
- **The specs' ACs contain self-certifying errors** (see §3) — **fix the AC, don't corrupt code to satisfy a wrong AC.** When an AC contradicts the spec's own code or the LOD200 contract, treat it as a defect and correct it (log the correction in the PR).
- Full per-WP fix detail = the VALIDATION_REPORT (inputs). This directive = order + constraints + the fix index.

## 1. Phase 0 — Environment bootstrap (do FIRST, once; its own PR)
1. Create **`.cursor/environment.json`** (repo root) so every scheduled agent has a ready env (verify the exact schema empirically against cursor.com/docs/cloud-agent/setup; adjust field names if needed). Intended effect:
   - `sudo apt-get install -y python3.12-venv python3-venv`
   - create venv + `pip install -r requirements.txt`
   - `pip install pytest pytest-mock python-bidi`
   - **snapshot** after install so scheduled agents skip re-installing.
2. Add `pytest`, `pytest-mock`, `python-bidi` to **`requirements.txt`** (team_00-authorized).
3. Smoke: `python -c "import src.<each module>"` for existing modules; `pytest -q` (no tests yet → exit-0 collection); confirm `python -c "from PIL import features; print(features.check('raqm'))"` → True.
4. Confirm `python3.12`, Pillow raqm=True, all deps import. Commit → PR "phase-0 env".

## 2. Build order (CORRECTED — resolves the WP006↔WP007 crash)
The HANDOFF's "…WP006 then WP007" order is **wrong**: WP006 calls `render(settings=)` that only exists after WP007 patches `m4_renderer.py`, and both edit `orchestrator.py`/`m3_normalizer.py`. Build in this order, each on its own branch → PR:
1. **WP007-part-1** — `src/m4_renderer.py` (`render(settings=)` + `og_image_url`) + `src/models.py` (4 new `GeneratedContent` fields) ONLY. (The interface WP006 calls.)
2. **WP001** — `src/llm.py`.
3. **WP002** — `src/token_tracker.py` (mock tests on Cloud; live smoke deferred to Mac).
4. **WP003** — `src/researcher.py`.
5. **WP004** — `src/editor.py`.
6. **WP005** — `src/teaser.py`.
7. **WP006** — orchestrator rewire + `src/publisher.py`. **WP006 owns the FINAL state of `orchestrator.py` + `m3_normalizer.py`** (including the settings-threading + the 4 `neo.metadata` fields) — it must NOT assume WP007's companion edits.
8. **WP007-part-2** — `templates/newsletter.html.j2` (sections, corners, dark-mode, footer, mascot slots).

## 3. Per-WP P0 fixes (apply during build; detail in VALIDATION_REPORT §5)
- **WP001:** AC-09 empty-`provider_fallback` guard is unreachable → check raw value before `or [provider]`; AC-10 mock op raises → use a JSON mock op or expect the error; **`cursor_model` default `grok-4` → `cursor-grok-4.5-high`**.
- **WP002:** 🔴 `pause_turn` must **replace** message state, not append (O(N²)/cost-cap) → rewrite AC-25; `allowed_callers:["direct"]` unverified → **verify on Mac live smoke**, remove if rejected.
- **WP003:** AC-83 counts **14** watchlist cols (not 13) — do NOT drop a column; resolve AC-15 bookshelf-fallback logic (shared themes OR'd in → fallback never fires).
- **WP004:** add an **unconditional** "any mention of `shaked` → English" rule (currently only in the empty-highlights fallback); rescope AC-04 to a bare-`{identifier}` regex (schema JSON has `{}`).
- **WP005:** 🔴 `_load_font` fallback must force `raqm_available=False` for that draw (raqm=True + fallback font = `KeyError` crash); fix Rubik font source (static build or variable font) + `curl -f`.
- **WP006:** 🔴 add a preflight asserting `render` accepts `settings` (build-order guard); set `neo.metadata['editor_name']` (WP007 reads `editor_name`, not `editor_credit`).
- **WP007:** AC-47 expects a decrease of **3** (not 2).
- P1 items per WP: see VALIDATION_REPORT §5 (cost-under-report, no-farm-business rule, 30KB + member≥1 checks, duplicate-string targeting, etc.).

## 4. Cross-cutting build rules
- **Missing content → visible marked placeholder (team_00 D1).** Any section whose text isn't produced yet (Family-Table `family_table_text`, Extended-Family `extended_family`, Viewing, Shelf) must render a **clearly-marked placeholder in the UI** (e.g. a dashed box / "🚧 בהכנה" label) — **not** a silent empty/absent section. This keeps all 13 sections visibly present for edition-1; real content lands in the content phase (goal #2).
- **Graphics = pre-made assets (team_00 delivers in parallel).** Consume PNGs from `assets/characters/2026-07/<pose>.png` (+ `assets/characters/_placeholder/<pose>.png`) and `assets/hero/hero-scene.png` (MEDIA_BRIEF). **Add a `_placeholder/` fallback to `get_character_html()`** (currently month-dir only). Until assets arrive, emoji fallback renders — that is fine for the build.
- **Anthropic mocked in all Cloud pytest.** No `api.anthropic.com` calls from Cloud.
- **Cross-engine validate** each WP with a Claude Cursor model agent (or Mac Claude) — not the Anthropic API from the Cloud VM.

## 5. Definition of done (goal #1)
- All 8 build steps (§2) merged via PR; `.cursor/environment.json` snapshot persisted.
- `python -m orchestrator weekly-build --mock` produces HTML **≥30 KB** with all 13 sections visibly present (real or marked-placeholder).
- `teaser.py` generates the RTL teaser **without crashing** (raqm path), human-eyeballed once.
- `pytest -q` green (Anthropic mocked); each WP's corrected ACs pass.
- WP002 live-API items (`pause_turn`, `allowed_callers`, cost-cap) settled separately on Mac/waldhomeserver.

## 6. Out of scope (this directive)
- **Runtime** (weekly sonnet-5 generation + FTP + WhatsApp + AOS) → **waldhomeserver** (Cloud egress blocks Anthropic/FTP/Tailscale). Deploy is a later OPS directive (P003).
- **Content authoring** (goal #2) → separate phase, target **Mon 2026-07-27**.
- **Media generation** (goal #3 assets) → team_00, in parallel; integration = drop files at §4 paths + commit.
- **Tranche-B graphics** (per-member ×5 + per-category costumes ×10) + their topic→character **selection logic** → TBC by team_00 (MEDIA_BRIEF §2). If confirmed, adds a WP.
