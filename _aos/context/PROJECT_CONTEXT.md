# PROJECT CONTEXT — Family Newsletter (בית ולד)

## AOS environment (read first)

- **Repository role:** spoke (hub = agents-os methodology source; spoke = product snapshot consumer)
- **Profile:** L0 (Lean) — solo, files + git + discipline; no DB/dashboard/services. See `_aos/metadata.yaml`.
- **Roadmap / WP state:** `_aos/roadmap.yaml` (SSoT; born-canonical id `family-newsletter`)
- **Boundaries (write roots, forbidden imports):** `_aos/project_identity.yaml`
- **Governance contracts (snapshots):** `_aos/governance/team_*.md` — read **on mandate** or deep work; not required cover-to-cover each session.
- **Provisioned:** 2026-07-22 by team_120 (Ambassador) under team_00 mandate `MANDATE_team_00_TO_team_120_FAMILY_AOS_PROVISIONING_2026-07-22`. Build was frozen until this `_aos/` existed; it now does.

## Team entry

- **Roles:** `familynewsletter_sd` (Nimrod, orchestrator) · `familynewsletter_arch` (Claude/Sonnet — LOD spec author) · `familynewsletter_build` (Grok via Cursor CLI — runtime builder) · `familynewsletter_val` (Claude — cross-engine validator). See `_aos/team_assignments.yaml`.
- **Per-role activation prompts:** `_aos/context/ACTIVATION_{ARCH,BUILDER,VALIDATOR}.md`.

## Domain profile

### What this product is

A personalized weekly Hebrew family newsletter ("בית ולד") for the five Wald household members — a per-member section by taste, cross-member "discovery bridges", a math riddle, a family "Friday table" item, weekly watch picks, and a WhatsApp teaser to a family group. Python app: modular pipeline (`src/m1..m6`, being rebuilt as `researcher.py`/`editor.py`/`teaser.py`/`publisher.py` + an `llm.py` driver layer), SQLite "family memory" (`src/db.py`), Jinja2 comic template (`templates/newsletter.html.j2`), published to nimrod.bio via FTP + WhatsApp (WAHA), on a weekly Friday home-server cron.

### Current focus

**S001 / Phase A** — first real edition reaches the family group. The rethink (REVIVAL_PLAN_2026-07-22): drop the RSS/scraping pipeline, rebuild around an LLM-with-web-search researcher; add WhatsApp/WAHA delivery; run weekly on waldhomeserver. See `_aos/roadmap.yaml` for the seeded WP registry.

## Governance baked in (team_00 ruling, 2026-07-22 — binding)

1. **LOD depth by material type (standing law):**
   - **Content / data / family-characterization → LOD200 + cheap validation** (the *only* exception).
   - **ANY code write OR edit → full AOS characterization (LOD400 + validations), no exceptions.** The rule is intentionally stricter than the canon minimum — zero-ambiguity LOD400 is the token-saving lever (lets the lazy Grok builder build right the first time).
2. **Engine routing (token crunch to end of month):** builder = **Grok via Cursor CLI** (flat-cost, needs zero-ambiguity LOD400); heavy spec/edit/validate = **Sonnet high-effort**; **Opus only where truly required**. Cross-engine VALIDATE (Iron Rule #1) is satisfied by **Grok builds → Claude validates** — canonically required, not just cost.
3. **Track / archetype:** Profile L0; WP split — new pipeline = **STANDARD**, edition content = **CONTENT**, WAHA/server = **OPS**, existing kept code (M4 render, M5→publisher, db) = **BACKFILL** (as-built LOD500, no retroactive plan). Tagged `CLASS=…` in each roadmap WP's `notes:`.
4. **Spec-production flow:** the team authors the specs; **team_00 validates at the end** (not a per-spec pre-approval bottleneck).

## Naming (born-canonical)

Canonical id **`family-newsletter`** / display "Family Newsletter" / Hebrew "בית ולד". "family" / "Family Newsletter" is a **retired typo** — never write it into any `_aos/` artifact. The outer folder name, the GitHub remote (`family-newsletter`), the eventual relocation under `/AOS_V5/`, and the server path `/data/projects/family-newsletter` are handled by a **separate post-dev rename runbook** (out of scope for provisioning).

## Standards / SSOT

- **Validate:** `bash _aos/lean-kit/modules/validation-quality/scripts/validate_aos.sh .`
- **Active WP:** `_aos/roadmap.yaml` → `status: IN_PROGRESS`
- **Code standards:** hub `_aos/context/CODE_STANDARDS.md` (cite qualified per ADR037)
- **Source of this context:** `REVIVAL_PLAN_2026-07-22.md`, `STYLE_GUIDE.md §1`, and the provisioning mandate.
