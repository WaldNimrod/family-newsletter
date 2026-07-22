## AOS Spoke Notice — AOS Identity: Family Newsletter L0 Spoke

<!-- AOS canonical invariants (ADR040 / Iron Rule #12):
     - DB probe: check hub _aos/db_connectivity_status.json (probe_database)
       before any structured mutations. ADR034 / Iron Rule #7.
     - gov-update / gov-sync: Team 00 / Team 100 ONLY. ADR040 / Iron Rule #12.
-->

# CLAUDE.md — Family Newsletter

## Identity
**Repo:** family-newsletter
**Profile:** L0 (Lean/Manual)
**Hub:** /Users/nimrod/Documents/AOS_V5/agents-os

## What this repo is
Update with project purpose.

## Mandatory session startup
0. **[CTX-03] Step 0 — Identity + connectivity (server / agent / non-interactive sessions):** Interactive Mac shells already have `AOS_API_BASE` + `AOS_ACTOR_API_KEY` exported from `~/.aos/actor.env` (auto-sourced by `~/.zshrc`). The v5 server (DB + API) is at the Tailscale-canonical `http://100.125.98.56:8092` (ADR043 §15.4).
   - **Verify env:** `echo ${AOS_API_BASE:-UNSET}` and `echo ${AOS_ACTOR_API_KEY:+KEY_SET}`. If `UNSET`/empty → `source ~/.aos/actor.env` (interactive), or run `bash /Users/nimrod/Documents/AOS_V5/agents-os/scripts/provision_actor_key.sh <team>` once from a team_00/team_99 issuer session. Never commit the key.
   - **Identity (so messages/handoffs attribute to THIS domain, not the hub team_100 default — read at send time by the messaging path):** `export AOS_SESSION_TEAM_ID=<this domain's team>` and `export AOS_PROJECT_ID=<this spoke id>`.
   - **Reachability:** `curl -s -o /dev/null -w '%{http_code}' --max-time 3 ${AOS_API_BASE:-http://100.125.98.56:8092}/api/system/health` → expect **200**.
   - **Authenticated check:** `curl -s -o /dev/null -w '%{http_code}' --max-time 3 -H "Authorization: Bearer ${AOS_ACTOR_API_KEY}" "${AOS_API_BASE}/api/messaging/v2/inbox?recipient_kind=team&recipient=<your team>"` → expect **200**, not **401**.
   - Full procedure (key retrieval, auth matrix): hub `governance/directives/ADR043` §15.4 + §16 — do NOT duplicate it here (Iron Rule #11, one-directional flow).
1. Read `_aos/roadmap.yaml` — active WPs and current gate position
2. Read `_aos/context/PROJECT_CONTEXT.md` — domain background and team entry
3. Read `_aos/project_identity.yaml` — boundary declarations and allowed write roots
4. Read governance contract for your team: `_aos/governance/team_[ID].md`

## Team model
Universal numbering (Iron Rule #9). See `_aos/definition.yaml`.
Active team assignments: `_aos/team_assignments.yaml`.

## Directory Authority

| Team | May write to |
|------|-------------|
| Team 00 (Principal) | Anywhere |
| Team 100 (Architect) | `_COMMUNICATION/team_100/`, `_aos/roadmap.yaml`, `_aos/work_packages/` |
| Team 120 (Ambassador) | `_COMMUNICATION/team_120/`, `_aos/` (bootstrap/propagation, under mandate) — inherits Team 191's `_aos/` authority (D-191auth) |
| ALL OTHER TEAMS | `_COMMUNICATION/team_[ID]/` and application source ONLY |

`_aos/` is the governance layer — **OFF LIMITS for all non-governance teams**.
Non-AOS teams route required roadmap/gate updates via report artifact to Team 100.
Canonical authority table: `methodology/AOS_DIRECTORY_CANON_v1.0.0.md` Part 5 (see hub).

## §BOUNDARY — Cross-Project Isolation
- **This repository is:** Family Newsletter (L0 spoke)
- **Cross-project handoff:** `~/Documents/_agent_comm/outbox/` or route to Team 10
- NEVER create files that belong to another project in this repo
- `_aos/project_identity.yaml` is the machine-readable boundary SSoT

## Dev/Staging TLS & Browser-QA Discipline (uniform)

- **Dev/staging TLS is often invalid BY DESIGN** — many hosts issue a valid certificate only on the primary/production domain. A cert error on a **dev/staging** URL is **expected** and is NOT a defect to fix; a cert error on **production** IS a real defect.
- **Cert-bypass flags are DEV-ONLY:** `curl -k` · chrome `--ignore-certificate-errors` · `requests verify=False`. Never use them in production QA.
- **Never use `curl` alone to validate layout** — curl sees only HTML, never the rendered box model, so horizontal-overflow / RTL / responsive bugs pass curl and ship. For any layout/overflow/visual check, run the dependency-free browser-QA runner: `_aos/lean-kit/modules/validation-quality/scripts/qa/qa_probe.mjs` (Node 18+, no pip/npm). Discipline + curl-vs-CDP-vs-Lighthouse guidance: `_aos/lean-kit/modules/validation-quality/docs/BROWSER_QA_HARNESS_CANON_v1.0.0.md`.
- Dev SEO/Performance scores (noindex edge headers, cache misses) are **artifacts** — re-measure on the production domain.

## AOS Hub reference
Hub: /Users/nimrod/Documents/AOS_V5/agents-os
Methodology: hub `methodology/` directory
Canon: hub `methodology/AOS_DIRECTORY_CANON_v1.0.0.md`
Lean Kit: `_aos/lean-kit/` (physical snapshot — read-only)

---
*Template: lean-kit/modules/project-governance/config_templates/CLAUDE.md.template*
*Instantiated: 2026-07-22 | Profile: L0*
