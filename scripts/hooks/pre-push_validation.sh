#!/usr/bin/env bash
# AOS pre-push validation hook (delegated) — AOS-V4.5-WP-CI-LOCAL-MINIMAL (S1)
#
# Purpose: the AUTHORITATIVE local pre-merge gate. Per ADR051 (Local-first, Minimal-cloud,
#   Zero-pay) this replaces reliance on GitHub-hosted CI: validation runs here, on the dev's
#   machine, before any push reaches GitHub.
#
# Prerequisites: bash, git, python3; invoked from within an AOS repo (hub or spoke).
# Env vars:
#   AOS_SKIP_TESTS=1         → run validate_aos.sh only; skip the repo test suite.
#   AOS_PREPUSH_TESTS=advisory → repo-test failures only WARN (non-blocking). Default is now
#                              STRICT: repo-test failures BLOCK the push. Flipped 2026-06-16 once
#                              the v5 suite reached green + deterministic (471/0); was advisory
#                              under D-S1-002 only while pre-existing test debt could wedge pushes.
# Ports: none — this script opens no listeners (CS-5: prerequisites/env/ports stated).
# Contract: exit 0 = allow push; non-zero = block push.
# Bypass: `git push --no-verify` skips the hook natively (single disciplined operator).
#
# Ref: _aos/work_packages/AOS-V4.5-WP-CI-LOCAL-MINIMAL/LOD400_BUILD_SPEC_v1.0.0.md §B/S1
#      [agents-os _aos/context/CODE_STANDARDS.md CS-5] (shell), CS-6 (English in code).
#
# ── S5 extension (AOS-V5-M12-WP-L0-SELFHOST-GIT-GATE) — attestation marker +
#    dual-push mirror. BOTH new behaviors are OFF BY DEFAULT and do not alter
#    ANY of the above for a normal feat/* push (env vars unset -> stdin is
#    never even read by the new code):
#   AOS_PREPUSH_WRITE_ATTESTATION=1  → on green, write + push a lightweight
#     SHA-keyed pass-marker (refs/attestations/<sha>) covering cold-integration
#     + cockpit-e2e (retry-once), for the server-side pre-receive_gate.sh (S2)
#     to verify before accepting a push to the self-hosted bare's main.
#   AOS_PREPUSH_ATTESTATION_REMOTE   → remote to push the marker to (default waldhome).
#   AOS_PREPUSH_DUAL_PUSH=1          → additionally push waldhome (authoritative,
#     on the critical path) + origin --all (GitHub-Free mirror, OFF the
#     critical path — a mirror failure only logs/alerts) + a post-push parity
#     check (`git ls-remote origin main` == pushed SHA).
#   AOS_PREPUSH_MIRROR_REMOTE        → mirror remote name (default origin).
# Neither var is set by default anywhere in this pass — see
# _aos/work_packages/AOS-V5-M12-WP-L0-SELFHOST-GIT-GATE/LOD400_BUILD_SPEC_SELFHOST_GIT_GATE_v1.0.0.md §1 S5.
# Standalone unit-test entry points (bypass the whole hook flow — never reached
# by a normal git-invoked call, whose $1/$2 are a remote name/URL string, not
# these literal flags):
#   bash scripts/hooks/pre-push_validation.sh --emit-attestation <sha> <remote>
#   bash scripts/hooks/pre-push_validation.sh --dual-push <sha> [waldhome] [origin]

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# Git env hygiene: when invoked as a git hook, git exports GIT_DIR / GIT_WORK_TREE /
# GIT_INDEX_FILE pointing at THIS repo. Child processes (validate_aos.sh, the pytest suite)
# inherit them, so their git subcommands operate on this repo instead of their own fixtures —
# e.g. tests doing `git init` / `git worktree add` in a tmp dir leaked 'init' commits and
# stray worktrees onto the working branch. Unset so children resolve git from their own cwd.
# (AOS-V4.5 — root cause of pre-push branch pollution.)
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_PREFIX GIT_OBJECT_DIRECTORY 2>/dev/null || true

log() { printf '[pre-push] %s\n' "$1" >&2; }

# ── S5 functions (attestation marker + dual-push) — defined early so the
#    standalone CLI entry points below can dispatch before any of the main
#    hook flow (governance validation, repo tests) runs at all. ─────────────

_aos_build_attestation_json() {
  # args: sha cold_integration_status cockpit_e2e_status
  local sha="$1" ci="$2" e2e="$3" ts host
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  host="$(hostname 2>/dev/null || echo unknown)"
  printf '{"sha":"%s","checks":{"cold-integration":"%s","cockpit-e2e":"%s"},"ts":"%s","host":"%s"}\n' \
    "$sha" "$ci" "$e2e" "$ts" "$host"
}

# Runs scripts/run_cockpit_e2e.sh with one retry on failure (S5: "cockpit-e2e
# retry-once"). Prints pass/fail/n-a to stdout; return code mirrors pass=0.
_aos_cockpit_e2e_status() {
  local script="$REPO_ROOT/scripts/run_cockpit_e2e.sh"
  if [ ! -x "$script" ]; then
    log "cockpit-e2e: $script not found/executable — marking n/a (non-blocking marker; this repo may not carry cockpit/)."
    printf 'n/a'
    return 0
  fi
  if bash "$script" >&2; then
    printf 'pass'; return 0
  fi
  log "cockpit-e2e: first attempt FAILED — retrying once (S5 retry-once policy)…"
  if bash "$script" >&2; then
    printf 'pass'; return 0
  fi
  printf 'fail'; return 1
}

# Reuses this file's own parity harness (below) as the hub's cold-integration
# equivalent. Repos without the lockfile+core/tests shape (most spokes) mark
# n/a (non-blocking — the gate this feeds is hub-only today).
_aos_cold_integration_status() {
  # M12 P5.0 live finding (first exercise of the deferred AC-2 green path): this function is
  # called inside a command substitution — ci="$(...)" — so EVERYTHING it writes to stdout
  # lands in the JSON marker. Re-running the harness here (a) leaked the entire pytest
  # progress output into the "cold-integration" value, corrupting the marker
  # (INVALID_JSON reject at the server gate), and (b) doubled push time. When §2's strict
  # harness has ALREADY passed in this same hook invocation, that run IS the
  # cold-integration equivalent — reuse the fact instead of re-running.
  if [ "${_AOS_TESTS_GENUINELY_GREEN:-0}" = "1" ]; then
    printf 'pass'; return 0
  fi
  if [ "${_PARITY_HARNESS_APPLICABLE:-0}" = "1" ]; then
    # Standalone path (--emit-attestation): run it, but keep stdout CLEAN (>&2).
    if _run_parity_harness >&2; then printf 'pass'; return 0; else printf 'fail'; return 1; fi
  fi
  printf 'n/a'
  return 0
}

_aos_write_and_push_attestation() {
  # args: sha remote
  local sha="$1" remote="$2" ci e2e json blob rc=0
  ci="$(_aos_cold_integration_status)" || rc=1
  e2e="$(_aos_cockpit_e2e_status)" || rc=1
  json="$(_aos_build_attestation_json "$sha" "$ci" "$e2e")"
  log "attestation for $sha: $json"
  if [ "$rc" -ne 0 ]; then
    log "attestation checks did not both pass (cold-integration=$ci cockpit-e2e=$e2e) — NOT pushing a marker for $sha."
    log "  (a missing marker is the correct, safe outcome — the server gate rejects $sha on main until a green marker exists.)"
    return 1
  fi
  blob="$(printf '%s' "$json" | git hash-object -w --stdin)" || { log "git hash-object failed"; return 1; }
  # --force on THIS ref only: refs/attestations/<sha> is a namespaced, blob-
  # pointing side-channel marker (not refs/heads/*), safe to overwrite on a
  # retried push for the same SHA (git otherwise refuses non-fast-forward-
  # looking updates to a ref pointing at a non-commit object).
  if git push --force "$remote" "$blob:refs/attestations/$sha"; then
    log "pushed attestation refs/attestations/$sha -> $remote (blob $blob)"
    return 0
  fi
  log "push of refs/attestations/$sha to $remote FAILED"
  return 1
}

_aos_dual_push_and_parity_check() {
  # args: sha waldhome_remote origin_remote
  local sha="$1" wh="${2:-waldhome}" og="${3:-origin}"
  log "dual-push: git push $wh $sha:refs/heads/main (authoritative, on critical path)"
  git push "$wh" "$sha:refs/heads/main" || { log "dual-push: $wh push FAILED — this DOES block (authoritative leg)"; return 1; }
  log "dual-push: git push $og --all (mirror, OFF the critical path — failure here logs/alerts, never blocks)"
  if ! git push "$og" --all; then
    log "ALERT: mirror push to $og FAILED — reconcile later; the deploy is NOT blocked by this (Tier-2 #7)."
  fi
  local remote_main
  # `|| true`: under `set -e -o pipefail`, a failing `git ls-remote` (e.g. the
  # SAME broken mirror that just failed above) would otherwise abort the whole
  # script right here instead of falling through to the mismatch/red-alert
  # branch below — the parity check must degrade gracefully, never crash.
  remote_main="$(git ls-remote "$og" refs/heads/main 2>/dev/null | cut -f1)" || true
  if [ "$remote_main" = "$sha" ]; then
    log "post-push parity check: $og main == $sha — OK"
  else
    log "RED-ALERT: post-push parity mismatch — $og main is '${remote_main:-<unreachable>}', expected $sha"
  fi
  return 0
}

# ── CI-parity harness detection (M12-P1 item a — test parity + CI green) ──────
# Placed ahead of §1 (governance validation) so the S5 standalone entry points
# just below can dispatch BEFORE any of the main hook flow runs at all —
# "bypass the whole hook flow" per the header comment above. Detection +
# _run_parity_harness are pure/cheap to DEFINE (file-existence checks; the
# harness itself only runs when actually invoked from §2/§2b below), so moving
# them ahead of §1 changes nothing about the NORMAL flow's behavior or timing.
#
# This hook file is the fleet-wide SOURCE propagated verbatim to every spoke by
# aos_sync_all.sh (scripts/hooks/pre-push_validation.sh) — most spokes have no Python
# lockfile at all, so this MUST degrade gracefully rather than assume the hub's shape.
# Detected only when BOTH a pinned lockfile AND core/tests/ exist (currently: agents-os
# hub only). When detected, this REPLACES the legacy ambient `pytest -q` with a fresh
# `git clone --local` + a fresh venv installed FROM THE LOCKFILE + `pytest core/tests/ -q`
# with AOS_DATABASE_URL unset (pg_bootstrap auto-provisions an isolated test DB) — the
# SAME world scripts/integration_gate.sh and .github/workflows/cold-integration.yml run
# in CI, so a lockfile-only or hardcoded-path defect invisible to the operator's ambient
# PATH (which happens to carry extra packages / match hardcoded Mac paths by construction)
# fails HERE too, not just in CI (AC-P1.2). This was the exact green-local/red-CI gap that
# left cold-integration.yml red for 140/140 runs (M12-P1 LOD200 §1).
_PARITY_LOCKFILE=""
for _cand in "$REPO_ROOT/core/requirements.lock" "$REPO_ROOT/requirements.lock"; do
  if [ -f "$_cand" ]; then _PARITY_LOCKFILE="$_cand"; break; fi
done
_PARITY_HARNESS_APPLICABLE=0
if [ -n "$_PARITY_LOCKFILE" ] && [ -d "$REPO_ROOT/core/tests" ]; then
  _PARITY_HARNESS_APPLICABLE=1
fi

# Fresh-clone + fresh-venv + pytest core/tests/ -q. Returns pytest's exit code.
# Wall-clock budget ≤6 min (360s) — logs a WARNING (never blocks on the budget itself;
# the budget is an operational health signal, not a gate) if exceeded.
_run_parity_harness() {
  local t0 tmp_clone venv_dir rc elapsed lockfile_rel
  t0=$(date +%s)
  tmp_clone="$(mktemp -d "${TMPDIR:-/tmp}/aos_prepush_parity.XXXXXX")"
  # shellcheck disable=SC2064 — intentional early expansion of $tmp_clone (fixed at trap-set time)
  trap "rm -rf '$tmp_clone'" RETURN
  log "parity harness: fresh clone (git clone --local) → $tmp_clone"
  if ! git clone --local --quiet "$REPO_ROOT" "$tmp_clone" 2>&2; then
    log "parity harness: git clone --local FAILED"; return 1
  fi
  venv_dir="$tmp_clone/.venv"
  if ! python3 -m venv "$venv_dir" 2>&2; then
    log "parity harness: python3 -m venv FAILED"; return 1
  fi
  lockfile_rel="${_PARITY_LOCKFILE#"$REPO_ROOT"/}"
  log "parity harness: fresh venv install -r $lockfile_rel"
  if ! "$venv_dir/bin/pip" install -q -r "$tmp_clone/$lockfile_rel" 2>&2; then
    log "parity harness: pip install -r $lockfile_rel FAILED"; return 1
  fi
  log "parity harness: pytest core/tests/ -q (AOS_DATABASE_URL unset — isolated bootstrap DB, never the dev DB)"
  set +e
  ( cd "$tmp_clone" && env -u AOS_DATABASE_URL "$venv_dir/bin/python3" -m pytest core/tests/ -q )
  rc=$?
  set -e
  elapsed=$(( $(date +%s) - t0 ))
  log "parity harness: rc=$rc elapsed=${elapsed}s"
  if [ "$elapsed" -gt 360 ]; then
    log "WARNING: parity harness took ${elapsed}s > the 6-minute (360s) budget — investigate before this becomes routine (does not itself block the push)."
  fi
  return "$rc"
}

# Standalone S5 unit-test entry points — dispatched HERE (not at the very top)
# because _aos_cold_integration_status() depends on _run_parity_harness +
# _PARITY_HARNESS_APPLICABLE, both defined just above; this is still entirely
# BEFORE §1 (governance validation) and §2 (repo tests), so it genuinely
# bypasses the whole hook flow. Never reached by a normal git-invoked hook
# call, whose $1/$2 are a remote name/URL string, not these literal flags.
case "${1:-}" in
  --emit-attestation)
    _aos_write_and_push_attestation "${2:?sha required}" "${3:?remote required}"
    exit $?
    ;;
  --dual-push)
    _aos_dual_push_and_parity_check "${2:?sha required}" "${3:-waldhome}" "${4:-origin}"
    exit $?
    ;;
esac

# ── S5 recursion guard (M12 P5.0 live finding, 2026-07-18): the attestation
#    writer's own `git push --force <remote> <blob>:refs/attestations/<sha>`
#    re-fires THIS hook with AOS_PREPUSH_WRITE_ATTESTATION still exported —
#    which re-ran the full parity harness and then tried to attest the
#    attestation BLOB itself, recursing without bound (observed live: 4 stacked
#    hook generations on the Mac + 5 stacked git-receive-packs on the bare
#    before the chain was killed; not one marker ever landed).
#    Fix: read the ref lines git hands us on stdin ONCE, here. If EVERY pushed
#    ref is a refs/attestations/* side-channel marker there is nothing to
#    validate or attest — a marker is a blob this same hook just minted on a
#    genuinely-green run — so exit clean immediately, breaking the recursion.
#    The captured lines feed the S5 attestation block at the bottom (stdin is
#    consumed here and would otherwise read empty there).
_AOS_PUSH_LINES="$(cat || true)"
if [ -n "$_AOS_PUSH_LINES" ]; then
  _only_attestations=1
  while IFS=' ' read -r _l _ls _r _rs; do
    [ -z "${_l:-}" ] && continue
    case "${_r:-}" in refs/attestations/*) : ;; *) _only_attestations=0 ;; esac
  done <<< "$_AOS_PUSH_LINES"
  if [ "$_only_attestations" = "1" ]; then
    log "attestation-marker-only push (refs/attestations/*) — side-channel blob minted by this hook on a green run; no validation/attestation applies. Allowing."
    exit 0
  fi
fi

# ── 1. Governance validation — locate validate_aos.sh ─────────────────────────
#    Preference: hub root wrapper → spoke snapshot (_aos/lean-kit) → hub lean-kit source.
VALIDATE=""
for cand in \
  "$REPO_ROOT/validate_aos.sh" \
  "$REPO_ROOT/_aos/lean-kit/modules/validation-quality/scripts/validate_aos.sh" \
  "$REPO_ROOT/lean-kit/modules/validation-quality/scripts/validate_aos.sh"; do
  if [ -f "$cand" ]; then VALIDATE="$cand"; break; fi
done

if [ -n "$VALIDATE" ]; then
  log "validate_aos.sh → $VALIDATE"
  if ! bash "$VALIDATE" "$REPO_ROOT"; then
    log "validate_aos.sh FAILED — push blocked. (bypass: git push --no-verify)"
    exit 1
  fi
else
  # DV-4.2 fail-loud (ADR056 / Model-B). An AOS repo (has _aos/) with no resolvable
  # validate_aos.sh means the Model-B governance cache is not hydrated — typical in a fresh
  # git worktree, where _aos/lean-kit/ is git-ignored and therefore not checked out. Silently
  # skipping the governance gate here is a false-green hole: the push lands with NO governance
  # validation at all (independent of --no-verify). Block loud and point at the fix. A genuine
  # non-AOS repo (no _aos/ at all) still skips harmlessly.
  if [ -d "$REPO_ROOT/_aos" ]; then
    log "validate_aos.sh not found but _aos/ present — Model-B governance cache not hydrated"
    log "  (fresh worktree?). Governance gate CANNOT run — push BLOCKED (DV-4.2 fail-loud)."
    log "  Fix: hydrate the cache → bash scripts/aos_governance_bootstrap.sh  (then re-push)."
    log "  Deliberate bypass (single disciplined operator): git push --no-verify."
    exit 1
  else
    log "validate_aos.sh not found + no _aos/ — genuine non-AOS repo, skipping governance validation."
  fi
fi

# ── 2. Repo test entrypoint (graceful — skip when absent) ─────────────────────
if [ "${AOS_SKIP_TESTS:-0}" = "1" ]; then
  log "AOS_SKIP_TESTS=1 — skipping repo test suite."
  exit 0
fi

# ── 2b. Detect + run the repo test entrypoint. Returns the test command's
#    exit code (0 when no entrypoint or tooling absent — graceful). ──────────
_run_repo_tests() {
  if [ "$_PARITY_HARNESS_APPLICABLE" = "1" ] && [ "${AOS_PREPUSH_TESTS:-strict}" != "fast" ]; then
    log "tests: CI-parity harness (fresh clone + fresh venv from $_PARITY_LOCKFILE)"
    _run_parity_harness; return $?
  fi
  if [ "$_PARITY_HARNESS_APPLICABLE" = "1" ]; then
    log "AOS_PREPUSH_TESTS=fast — explicit opt-DOWN to the legacy in-place ambient pytest (parity harness skipped; never the default; logged so the trade-off is visible in the push transcript)."
  fi
  if [ -f "$REPO_ROOT/Makefile" ] && grep -qE '^test:' "$REPO_ROOT/Makefile"; then
    log "tests: make test"; make -C "$REPO_ROOT" test; return $?
  elif [ -f "$REPO_ROOT/pytest.ini" ] || \
       { [ -f "$REPO_ROOT/pyproject.toml" ] && grep -q 'pytest' "$REPO_ROOT/pyproject.toml" 2>/dev/null; }; then
    if command -v pytest >/dev/null 2>&1; then log "tests: pytest -q"; pytest -q; return $?; fi
    log "pytest config present but pytest not installed — skipping."; return 0
  elif [ -f "$REPO_ROOT/package.json" ] && grep -q '"test"' "$REPO_ROOT/package.json"; then
    if command -v npm >/dev/null 2>&1; then log "tests: npm test"; ( cd "$REPO_ROOT" && npm test ); return $?; fi
    log "package.json test script present but npm not installed — skipping."; return 0
  fi
  log "no repo test entrypoint detected — validate-only."; return 0
}

_AOS_TESTS_GENUINELY_GREEN=0
if _run_repo_tests; then
  log "OK — push allowed."
  _AOS_TESTS_GENUINELY_GREEN=1
else
  trc=$?
  # "advisory" is the ONLY non-blocking value. "fast" (harness-selection opt-down) and any
  # other/future value still BLOCK by default — AOS_PREPUSH_TESTS=fast trades away the fresh-
  # clone/fresh-venv CI-parity harness for speed, it does NOT also relax blocking on failure.
  if [ "${AOS_PREPUSH_TESTS:-strict}" = "advisory" ]; then
    log "WARNING: repo tests FAILED (rc=$trc) — ADVISORY mode, push ALLOWED."
    log "  (validate_aos.sh governance gate already passed; set AOS_PREPUSH_TESTS=strict to block on tests.)"
  else
    log "repo tests FAILED (rc=$trc) and AOS_PREPUSH_TESTS=${AOS_PREPUSH_TESTS:-strict} — push blocked."
    exit 1
  fi
fi

# ── S5 wiring (OFF by default — AOS_PREPUSH_WRITE_ATTESTATION unset on this
#    branch; see header). Only runs when tests were GENUINELY green (never on
#    an advisory-allowed failure — an attestation must mean what it says).
if [ "$_AOS_TESTS_GENUINELY_GREEN" = "1" ] && [ "${AOS_PREPUSH_WRITE_ATTESTATION:-0}" = "1" ]; then
  _att_remote="${AOS_PREPUSH_ATTESTATION_REMOTE:-waldhome}"
  _mirror_remote="${AOS_PREPUSH_MIRROR_REMOTE:-origin}"
  _pushed_shas=()
  # Reads the ref lines captured ONCE at the top (_AOS_PUSH_LINES) — stdin itself was consumed
  # by the recursion guard and would read empty here (M12 P5.0 fix).
  while IFS=' ' read -r _lref _lsha _rref _rsha; do
    if [ -n "${_lsha:-}" ] && [ "$_lsha" != "0000000000000000000000000000000000000000" ]; then
      _pushed_shas+=("$_lsha")
    fi
  done <<< "${_AOS_PUSH_LINES:-}"
  if [ "${#_pushed_shas[@]}" -eq 0 ]; then
    log "AOS_PREPUSH_WRITE_ATTESTATION=1 but no non-deletion local SHA read from stdin — nothing to attest for this invocation."
  fi
  for _sha in "${_pushed_shas[@]}"; do
    if _aos_write_and_push_attestation "$_sha" "$_att_remote"; then
      if [ "${AOS_PREPUSH_DUAL_PUSH:-0}" = "1" ]; then
        _aos_dual_push_and_parity_check "$_sha" "$_att_remote" "$_mirror_remote" \
          || log "WARNING: dual-push/parity step reported an issue for $_sha (see log above) — the primary push already succeeded via git's own push path."
      fi
    else
      log "WARNING: attestation write/push failed or was skipped for $_sha — the server-side gate (S2) is the actual enforcement point; this push may be rejected there."
    fi
  done
fi

exit 0
