# _aos/ — Self-Contained Project Governance

## Project: Family Newsletter (family-newsletter)

## What is this?

This directory contains all governance artifacts for Family Newsletter (family-newsletter).
It is self-contained: clone this repo to any machine and governance is complete.
No external references to agents-os hub or other project repos.

## File Inventory

### Mandatory (all profiles)

| File | Purpose |
|------|---------|
| `README.md` | This file — governance model explanation |
| `metadata.yaml` | Provenance: lean_kit_version, source SHA, date, profile |
| `lean-kit/` | Physical snapshot of lean-kit framework at adoption time |
| `roadmap.yaml` | WP registry — SSOT for all work package state in this project |
| `team_assignments.yaml` | Active teams, role-based IDs, engine assignments |
| `MILESTONE_MAP.md` | Milestone descriptions and active milestone |
| `context/PROJECT_CONTEXT.md` | Current state, background, active work |
| `context/ACTIVATION_ARCH.md` | Activation prompt for architecture_agent |
| `context/ACTIVATION_BUILDER.md` | Activation prompt for builder_agent |
| `context/ACTIVATION_VALIDATOR.md` | Activation prompt for validator_agent |
| `work_packages/` | LOD specs per WP (LOD200, LOD400, LOD500) |

### L2 Profile Additions

| File | Purpose |
|------|---------|
| `metadata.yaml` → `aos_engine_version` | Engine snapshot version (L2 only) |

Engine directory (`aos_engine/` or legacy `agents_os/`) lives OUTSIDE `_aos/` as a sibling.

## Single-Writer Rule (IRON RULE)

At any time, exactly ONE agent holds write authority over `roadmap.yaml`.
Write authority transfers at gate boundaries:

- **architecture_agent** holds it between gates (WP planning, spec authoring)
- **builder_agent** holds it during L-GATE_BUILD (status updates during build)
- **validator_agent** reads only — never writes to roadmap.yaml

Never write to `roadmap.yaml` concurrently with another agent.
Commits to `roadmap.yaml` must include the WP-ID in the commit message.

## lean-kit Update Procedure (3 steps — manual, intentional)

When the lean-kit framework is updated at the agents-os hub:

1. **Update source:** Obtain new `agents-os/lean-kit/` at the desired version tag
2. **Copy to project:** Replace `_aos/lean-kit/` with the new physical copy (full directory replace)
3. **Update metadata:** Edit `metadata.yaml` — update `lean_kit_version`, `lean_kit_source_sha`, `lean_kit_source_date`
   Commit: `chore(lean-kit): update to vX.Y.Z+SHA`

This is intentionally manual. No automatic sync. Projects update when ready.

## Profile: L0

L0 (Lean): Human orchestrates via documents. No engine infrastructure in this repo.
All governance via `_aos/` files. Gate transitions via commit conventions.
Born-canonical id `family-newsletter` — "famely" is a retired typo (never in `_aos/`).

## Quick Reference

- **Validate:** `bash _aos/lean-kit/scripts/validate_aos.sh [project-root]`
- **Active WP:** Check `roadmap.yaml` → find WP with `status: IN_PROGRESS`
- **Start agent session:** Read `context/ACTIVATION_[ROLE].md` for your role
