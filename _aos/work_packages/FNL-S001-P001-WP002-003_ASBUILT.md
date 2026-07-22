---
type: ASBUILT
wp: FNL-S001-P001-WP002+WP003
from_team: team_110
date: 2026-07-22
class: EXPRESS
status: DONE — local commits only, NOT pushed
---

# As-Built — WP002 (env fix + gitignore) & WP003 (archive dead poc.py)

Light EXPRESS-class record. Both WPs are SAFE, LOCAL-ONLY git ops on `family-newsletter` `main`. Nothing pushed to the GitHub remote.

## Pre-flight
- `.env` confirmed gitignored (`.gitignore:2:.env`) — untouched, not committed.
- `data/` (harvest + `family.db`/`-shm`/`-wal`, `profile-raw/`, `harvest-inbox/`, `archive/`, `feedback/`, `cache/`, `submissions/`) was only **partially** ignored before this WP (`data/*.db`, `data/submissions/`, `data/archive/`, etc. — line-item patterns). Confirmed via `git check-ignore data/` returning nothing.

## WP002 — env fix commit
**Commit:** `16fe36e` — `fix(env): derive public URL from UPRESS_PUBLIC_BASE + UPRESS_UPLOAD_PATH; gitignore data/`

Files committed (exactly 4, nothing else staged):
- `src/env_compat.py` — `newsletter_url_base()` now composes the public URL from `UPRESS_PUBLIC_BASE` (domain only) + `UPRESS_UPLOAD_PATH`/`FTP_PATH` (remote path), instead of relying solely on a full pre-joined `UPRESS_PUBLIC_BASE`.
- `config/settings.json` — `newsletter.url_base` and `ftp.remote_path` updated to the `/agents/newsletter` path (was `/newsletter`).
- `.env.example` — `UPRESS_UPLOAD_PATH=/agents/newsletter`, `UPRESS_PUBLIC_BASE=https://nimrod.bio` (domain only now, comment updated to reflect the path is derived).
- `.gitignore` — collapsed the five line-item `data/*` patterns into a single blanket `data/` rule. Verified post-change: `git check-ignore data/` → `data/`, `git check-ignore .env` → still `.env` (unaffected).

Explicitly **left untracked** (not staged, not committed): `data/`, `profiles/`, `REVIVAL_PLAN_2026-07-22.md`, `MANDATE_TEAM100_PILOT_v3.0.0.md`, `_COMMUNICATION/`, `_aos/work_packages/`, `.env`. These move with the folder at cutover; committing project docs is a separate deliberate step, not this WP.

## WP003 — archive dead poc.py
**Commit:** `2a4a0de` — `chore(cleanup): archive dead standalone poc.py to archive/legacy/ (WP003; m2/m3/m6 deferred to P002)`

- `git mv poc.py archive/legacy/poc.py` (100% rename, `archive/legacy/` created via the mv).
- Verified before the move: `grep -rn "poc" src/` — zero hits. `poc.py` is the standalone superseded monolith, not imported by any current module.

### Explicit deferral — NOT archived in this WP
`src/m2_scanner.py`, `src/m3_normalizer.py`, `src/m6_feedback.py`, `config/sources.json` were **not** touched. Confirmed still live and imported:
- `grep -rln "m2_scanner\|m3_normalizer\|m6_feedback" src/` → `src/orchestrator.py` (imports all three).
- `grep -rln "sources.json" src/` → `src/orchestrator.py`, `src/m1_profiles.py`.

These carry salvage functions and are wired into the current orchestrator; their archiving is **deferred to P002**, coupled with the orchestrator rewire, per the mandate.

## Verification
- `.env` NOT committed (still working-tree only, still gitignored).
- `data/` (incl. `family.db*`) NOT committed (untracked before, ignored after `.gitignore` change).
- `poc.py` now lives at `archive/legacy/poc.py`.
- Nothing pushed — `git log` shows local `main` 2 commits ahead of `origin/main`; no `git push` was run.

## Governance note (flagged, not acted on)
This repo's own `CLAUDE.md` Directory Authority table reserves `_aos/work_packages/` writes for **Team 100** (Architect) and states `_aos/` is "OFF LIMITS for all non-governance teams," with non-AOS teams expected to "route required roadmap/gate updates via report artifact to Team 100." The WP mandate directed team_110 (builder) to write this as-built directly into `_aos/work_packages/`. Executed as directed since the mandate was explicit and the write is a local, non-destructive doc (no push, no secrets) — flagging the authority-table mismatch here for team_100/team_00 to reconcile if it matters for governance hygiene going forward.
