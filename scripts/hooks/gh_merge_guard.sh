#!/usr/bin/env bash
# gh_merge_guard.sh — PreToolUse merge-policy guard for `gh pr merge`
# =============================================================================
# Autonomous-merge policy (ADR052 Addendum — Autonomous Merge Policy, "balanced"):
#   A `gh pr merge` is auto-ALLOWED only when ALL hold:
#     - PR state == OPEN and NOT a draft
#     - checks passed  (mergeStateStatus ∈ {CLEAN, HAS_HOOKS})
#     - head branch matches a `.git-branch-allowlist` pattern
#     - no `--admin`  (which bypasses branch protection / required checks)
#   Otherwise → ASK (the normal human prompt). Any lookup failure (gh/jq missing,
#   PR not found) degrades to ASK — NEVER a silent allow.
#
# Wired via committed `.claude/settings.json` hooks.PreToolUse (matcher "Bash",
# if "Bash(gh pr merge:*)"); propagated fleet-wide by aos_sync_all.sh. Enforced
# present by validate_aos.sh Check 77.
#
# Testable: source with AOS_MERGE_GUARD_LIB=1 to load the pure functions
# (_merge_guard_decide / _branch_allowlisted / _extract_pr_ref) without running
# the stdin/main path. Inject PR metadata for tests via AOS_MERGE_GUARD_PR_JSON.

set -uo pipefail

# ─── Reusable branch-allowlist glob matcher (mirrors branch_guard_pre_commit.sh) ──
_branch_allowlisted() {
  local branch="$1" allowlist="$2" pat=""
  [ -n "$branch" ] || return 1
  [ -f "$allowlist" ] || return 1
  while IFS= read -r line; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    if [[ "$line" =~ ^branch:[[:space:]]*(.+)$ ]]; then
      pat="${BASH_REMATCH[1]// /}"
      # shellcheck disable=SC2053  — intentional glob match, not literal
      [[ "$branch" == $pat ]] && return 0
    fi
  done < "$allowlist"
  return 1
}

# ─── Extract the PR ref (positional) from a `gh pr merge …` command ──────────────
# Returns the first non-flag token after `merge`, skipping values of value-taking
# flags. Empty → gh resolves the current branch's PR.
_extract_pr_ref() {
  local cmd="$1"; local -a toks=(); local tok prev="" seen=0
  local value_flags=" -b --body -t --subject --match-head-commit --author-email "
  read -r -a toks <<< "$cmd"
  for tok in "${toks[@]}"; do
    if [ "$seen" = 1 ]; then
      if [[ "$tok" == -* ]]; then prev="$tok"; continue; fi
      if [[ "$value_flags" == *" $prev "* ]]; then prev=""; continue; fi
      printf '%s' "$tok"; return 0
    fi
    [ "$tok" = "merge" ] && seen=1
    prev="$tok"
  done
  return 0
}

# ─── Pure decision function ──────────────────────────────────────────────────────
# args: <cmd> <pr_json|empty> <allowlist_file>
# echoes: "allow"  OR  "ask|<reason>"
_merge_guard_decide() {
  local cmd="$1" pr_json="$2" allowlist="$3"
  case "$cmd" in *"gh pr merge"*) ;; *) echo "allow"; return 0;; esac
  case "$cmd" in *"--admin"*) echo "ask|--admin bypasses branch protection (ADR052 M7: merge to main is human-gated)"; return 0;; esac
  if [ -z "$pr_json" ]; then
    echo "ask|could not resolve PR metadata (gh/jq unavailable or PR not found) — degrade-safe ASK"; return 0
  fi
  local state draft mss branch
  state=$(printf '%s' "$pr_json"  | jq -r '.state // empty'            2>/dev/null)
  draft=$(printf '%s' "$pr_json"  | jq -r '(.isDraft // false)|tostring' 2>/dev/null)
  mss=$(printf '%s' "$pr_json"    | jq -r '.mergeStateStatus // empty' 2>/dev/null)
  branch=$(printf '%s' "$pr_json" | jq -r '.headRefName // empty'      2>/dev/null)
  [ "$state" = "OPEN" ]  || { echo "ask|PR state=${state:-unknown} (not OPEN)"; return 0; }
  [ "$draft" = "false" ] || { echo "ask|PR is a draft"; return 0; }
  case "$mss" in
    CLEAN|HAS_HOOKS) ;;
    *) echo "ask|mergeStateStatus=${mss:-unknown} (checks not green / not mergeable)"; return 0;;
  esac
  _branch_allowlisted "$branch" "$allowlist" || { echo "ask|head branch '${branch:-?}' not in .git-branch-allowlist"; return 0; }
  echo "allow"; return 0
}

# ─── Library mode: stop here when sourced for tests ──────────────────────────────
if [ "${AOS_MERGE_GUARD_LIB:-0}" = "1" ]; then return 0 2>/dev/null || exit 0; fi

# ─── Main (PreToolUse stdin → permission decision) ───────────────────────────────
_emit_ask_raw() {
  # Hand-rolled (used only when jq is unavailable so we can't build via jq).
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"jq unavailable — degrade-safe ASK"}}'
}
_emit() {
  # $1 = allow|ask   $2 = reason
  jq -cn --arg d "$1" --arg r "$2" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:$d,permissionDecisionReason:$r}}'
}

command -v jq >/dev/null 2>&1 || { _emit_ask_raw; exit 0; }

_input="$(cat 2>/dev/null || true)"
_cmd="$(printf '%s' "$_input" | jq -r '.tool_input.command // empty' 2>/dev/null)"
_repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
_allowlist="${_repo_root}/.git-branch-allowlist"

_pr_json=""
if [[ "$_cmd" == *"gh pr merge"* && "$_cmd" != *"--admin"* ]]; then
  if [ -n "${AOS_MERGE_GUARD_PR_JSON:-}" ]; then
    _pr_json="$AOS_MERGE_GUARD_PR_JSON"
  elif command -v gh >/dev/null 2>&1; then
    _ref="$(_extract_pr_ref "$_cmd")"
    # shellcheck disable=SC2086  — intentional word-split: empty $_ref → current-branch PR
    _pr_json="$(gh pr view $_ref --json state,isDraft,mergeStateStatus,headRefName 2>/dev/null || echo "")"
  fi
fi

_decision="$(_merge_guard_decide "$_cmd" "$_pr_json" "$_allowlist")"
if [ "$_decision" = "allow" ]; then
  _emit allow "merge-guard: OPEN, not draft, checks green, branch allowlisted, no --admin (ADR052 autonomous-merge policy)"
else
  _emit ask "merge-guard: ${_decision#ask|}"
fi
exit 0
