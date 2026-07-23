---
id: CAPABILITIES_REPORT_team_110_CURSOR_CLOUD_2026-07-22_v1.0.0
type: CAPABILITIES_REPORT
from_team: team_110
to_team: team_00
cc: team_100
date: 2026-07-22
subject: "Cursor Cloud capabilities — verified probe for P002 BUILD / RUNTIME placement"
responds_to: _COMMUNICATION/team_110/RESEARCH_REQUEST_team_00_TO_team_110_CURSOR_CLOUD_CAPABILITIES_2026-07-22_v1.0.0.md
cloud_agent: bc-9e175a29-cf6f-4965-9f2a-0365528820c1
probe_repo_path: /workspace
probe_branch: cursor/cloud-agent-environment-probing-fd55
probe_head: 324a3919aedb3cd749930bd546f50daf5ab2dffd
build_base_commit: ef0e366
---

# Capabilities Report — Cursor Cloud (team_110)

**Role.** team_110 (builder)  
**Repo.** `git@github.com:WaldNimrod/family-newsletter.git` (Cloud clone via HTTPS + GitHub App token as `cursor`)  
**Probe method.** Cursor Cloud Agent `[Cloud probe](bc-9e175a29-cf6f-4965-9f2a-0365528820c1)` launched from Mac orchestration session; all A/C/E empirical tags below are from that Ubuntu VM unless marked `[DOCS]`.  
**Mac baseline (non-authoritative for Cloud):** earlier same-day Mac session (`Darwin MacBook-Air-2.local`) — cited only for contrast.

Tag legend: `[VERIFIED:<cmd>]` · `[DOCS:<url>]` · `[UNKNOWN]` · `[CANON:<source>]` (team_00 fact, not re-probed)

---

## Environment identity (mandatory)

**Verdict: THIS probe ran on a Cursor Cloud Ubuntu VM — not Darwin.**

```text
$ uname -a
Linux cursor 6.12.94+ #1 SMP PREEMPT_DYNAMIC Mon Jul  6 18:05:21 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux

$ hostname
cursor

$ cat /etc/os-release | head -5
PRETTY_NAME="Ubuntu 24.04.4 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.4 LTS (Noble Numbat)"
VERSION_CODENAME=noble

$ echo "CURSOR_CLOUD=${CURSOR_CLOUD:-unset}"
CURSOR_CLOUD=unset

$ pwd ; whoami
/workspace
ubuntu
```

`[VERIFIED: uname -a / hostname / /etc/os-release / pwd / whoami]`  
`[DOCS: https://cursor.com/docs/cloud-agent]` — Cloud agents run in isolated VMs with cloned repos.  
`[DOCS: https://cursor.com/docs/cloud-agent/setup]` — default image is Ubuntu.

---

## A. Runtime & packages

### A1. OS / arch / Python / pip / venv

| Item | Result |
|------|--------|
| OS | Ubuntu 24.04.4 LTS (`noble`), Linux 6.12.94+, **x86_64** |
| Python | **3.12.3** (`/usr/bin/python3`) |
| pip | **24.0** (system + in-venv after fix) |
| venv (stock image) | **FAIL** — `ensurepip` / `python3-venv` missing |
| venv (after `sudo apt-get install -y python3.12-venv python3-venv`) | **PASS** at `/tmp/fnl-probe-venv` |

Stock-image failure:

```text
$ python3 -m venv /tmp/fnl-probe-venv
The virtual environment was not created successfully because ensurepip is not
available.  On Debian/Ubuntu systems, you need to install the python3-venv
package using the following command.
    apt install python3.12-venv
```

After remediation:

```text
$ python --version
Python 3.12.3
$ pip --version
pip 24.0 from /tmp/fnl-probe-venv/lib/python3.12/site-packages/pip (python 3.12)
$ echo "VENV_ACTIVE=$VIRTUAL_ENV"
VENV_ACTIVE=/tmp/fnl-probe-venv
```

`[VERIFIED: python3 --version; python3 -m pip --version; python3 -m venv; apt-get install python3.12-venv]`

**Constraint for BUILD env snapshot:** bake `python3-venv` (and preferably project `requirements.txt` install) into `.cursor/environment.json` `install`/`update` script or a saved snapshot so every scheduled agent does not re-apt.

### A2. pip install arbitrary PyPI packages

| Package | Result | Version installed |
|---------|--------|-------------------|
| pytest | PASS | 9.1.1 |
| pytest-mock | PASS | 3.15.1 |
| Pillow | PASS | 12.3.0 |
| feedparser | PASS | 6.0.12 |
| requests | PASS | 2.34.2 |
| jinja2 | PASS | 3.1.6 |
| anthropic | PASS | 0.118.0 |
| python-bidi | PASS | 0.6.11 |

```text
$ pip install pytest pytest-mock Pillow feedparser requests jinja2 anthropic python-bidi
Successfully installed ... Pillow-12.3.0 ... anthropic-0.118.0 ... pytest-9.1.1 pytest-mock-3.15.1 python-bidi-0.6.11 ...

$ pip list | rg -i 'pytest|Pillow|feedparser|requests|Jinja2|anthropic|python-bidi'
anthropic          0.118.0
feedparser         6.0.12
Jinja2             3.1.6
pillow             12.3.0
pytest             9.1.1
pytest-mock        3.15.1
python-bidi        0.6.11
requests           2.34.2
```

**Allowlist / proxy / offline:** no package allowlist observed. PyPI reachable (`pypi.org` HTTP 200). No HTTP(S)_PROXY vars. Selective TLS RST to some hosts (see E1/E2) — **not** a blanket offline mode.

`[VERIFIED: pip install …; curl pypi.org]`

### A3. Hebrew RTL / libraqm

```text
$ python -c "from PIL import features; print('raqm', features.check('raqm'))"
raqm True
```

`[VERIFIED: PIL.features.check('raqm')]`

- **libraqm install:** not required on this image (`raqm True` out of the box with manylinux Pillow wheel).
- **python-bidi:** installable; **not needed as fallback on this Cloud image** while `raqm True`. Keep it as defensive dep if env snapshots regress.

### A4. Pre-installed tooling

| Tool | Version |
|------|---------|
| git | 2.43.0 |
| node | v22.14.0 |
| npm | 10.9.7 |
| gcc | 13.3.0 |
| clang | 18.1.3 |
| make | 4.3 |
| cursor-agent / agent CLI | **NOT FOUND** |

```text
$ which cursor-agent agent
which_exit=1
$ cursor-agent --version
--: cursor-agent: command not found
```

`[VERIFIED: git/node/gcc/clang/make/which cursor-agent]`

---

## B. Git / repo

### B1. How the session obtains the repo / auth / ef0e366

```text
$ git rev-parse HEAD
324a3919aedb3cd749930bd546f50daf5ab2dffd

$ git log -1 --oneline ef0e366
ef0e366 feat(P002): author 7 LOD400 build specs + register WP007 + lock DESIGN_FISH 'all fish' decision

$ git cat-file -t ef0e366
commit

$ git remote -v
origin  https://x-access-token:[REDACTED]@github.com/waldnimrod/family-newsletter (fetch)
origin  https://x-access-token:[REDACTED]@github.com/waldnimrod/family-newsletter (push)

$ git status -sb
## cursor/cloud-agent-environment-probing-fd55

$ gh auth status
✓ Logged in to github.com account cursor
  - Git operations protocol: https
  - Token: ghs_************************************
```

- **Clone model:** Cloud provisions `/workspace` from GitHub; agent does not need a local Mac checkout.
- **Auth:** GitHub App / installation token as user **`cursor`** (`ghs_` token via `gh`), HTTPS remote with `x-access-token`. **Not** a deploy key or personal PAT in the VM shell.
- **ef0e366:** present and readable. Probe HEAD was `324a391` on auto-branch `cursor/cloud-agent-environment-probing-fd55` (newer than `ef0e366` on `main`).

`[VERIFIED: git remote/rev-parse/ef0e366/gh auth status]`  
`[DOCS: https://cursor.com/docs/cloud-agent]`

### B2. Commit + push + PR / branch model

`[DOCS: https://cursor.com/docs/cloud-agent/automations]` — Repo-backed automations can open PRs (PR tool default-on). Team-scoped automations open PRs as `cursor`; private automations open as the creator’s GitHub account.

`[DOCS: https://cursor.com/docs/cloud-agent/api/endpoints]` — Create-agent API supports `autoCreatePR`, `workOnCurrentBranch`, and auto-generated `cursor/...` branches (default: push to new branch, not `main`).

**Expected branch model for P002 (mandate):**

1. One Cloud agent per WP (or strictly serialized WPs).
2. Branch name unique per run, e.g. `build/FNL-S001-P002-WP00N-<shortsha>` or accept auto `cursor/...` branch.
3. Commit only on that branch → open PR → human/team_00 merge to `main`.
4. **Never** two agents with `workOnCurrentBranch=true` on the same branch.

`gh` authenticated as `cursor` confirms PR/push capability is present when PR tooling is enabled.

### B3. Concurrent-write collision avoidance

| Layer | Isolation |
|-------|-----------|
| Filesystem | **Per-agent isolated VM** — no shared worktree with other Cloud agents |
| Remote git | **Shared** — collision risk is on branch/PR, not local files |

**Hard requirement (lost uncommitted work already observed on Mac):**

1. Never run two scheduled agents that commit to the **same** branch.
2. Prefer auto `cursor/...` branch or explicit unique branch per WP.
3. Serialize WP001→WP007 (webhook / CI-completed trigger / manual handoff) rather than parallel schedules.
4. Result sink = **PR** (primary); optional committed status file **only** on the agent’s unique branch.
5. Do not use Mac interactive sessions and Cloud agents on the same uncommitted worktree story in parallel.

`[VERIFIED: isolated /workspace + unique branch cursor/cloud-agent-environment-probing-fd55]`  
`[DOCS: https://cursor.com/docs/cloud-agent]`

---

## C. Build engine (Grok / cursor-agent)

### C1. Is cursor-agent / Grok available? Is `grok-4` valid?

| Surface | Cloud VM result |
|---------|-----------------|
| `cursor-agent` CLI inside VM | **Absent** |
| Cloud Agent **platform** model | **Present** — this probe ran as Cloud Agent with model **`cursor-grok-4.5-high`** (orchestrator config) |

Mac-side model list (account `nimrod@mezoo.co`, for Automations model picker / CLI on Mac):

```text
cursor-grok-4.5-high
cursor-grok-4.5-high-fast
cursor-grok-4.5-medium
cursor-grok-4.5-medium-fast
cursor-grok-4.5-low
cursor-grok-4.5-low-fast
```

**`grok-4` is NOT a valid model id.** Use `cursor-grok-4.5-high` (or `-medium` / `-low` / `*-fast` variants).

`[VERIFIED on Cloud: which cursor-agent → not found]`  
`[VERIFIED on Mac account models: cursor-agent models | rg grok]`  
`[DOCS: https://cursor.com/docs/cloud-agent/automations]` — Automations select a model for the Cloud Agent run.

**Implication:** Cloud BUILD does **not** use Mac’s `cursor-agent -f` invocation. It uses **Cloud Agents / Automations** with model `cursor-grok-4.5-high`. The Mac CLI remains the interactive/local path.

### C2. Headless / non-interactive

**Mac CLI (local path):**

```bash
cursor-agent -p -f --model cursor-grok-4.5-high --workspace /path/to/repo "…"
```

`-p/--print` = non-interactive print; `-f/--force` = auto-approve commands.

`[VERIFIED on Mac: cursor-agent --help]`

**Cloud path:** Automations / Cloud Agents API — unattended by design; no TTY. Config surface: [cursor.com/automations](https://cursor.com/automations) or `POST /v1/agents` ([API endpoints](https://cursor.com/docs/cloud-agent/api/endpoints)).

### C3. One session: Grok build + Claude validation?

| Mode | Feasible on Cloud? | Notes |
|------|--------------------|-------|
| Grok Cloud Agent writes code + runs `pytest` (mocked Anthropic) | **YES** | Native agent model |
| Same VM calls **Anthropic HTTP API** (`anthropic` SDK / `api.anthropic.com`) | **NO (blocked)** | See E1 — TLS RST |
| Second Cloud Agent with a **Claude Cursor model** for review/validate | **YES (linked sessions)** | Satisfies Iron Rule #1 (builder ≠ validator engine) without Anthropic egress |
| Live Anthropic smoke (token_tracker `pause_turn`, cost caps) | **NO on Cloud** | Must run on Mac or waldhomeserver where `api.anthropic.com` works |

**Recommendation:** BUILD on Cloud = Grok agent + unit tests with mocks. Cross-engine VALIDATE = separate Cloud Agent on Claude model **or** Claude validator on Mac. Live Anthropic API settlement of token_tracker defects = **Mac/waldhomeserver only** until E1 is fixed.

---

## D. Secrets

### D1. How secrets are supplied; unattended availability

`[DOCS: https://cursor.com/docs/cloud-agent/setup]` — Recommended: **Secrets tab** at [cursor.com/dashboard/cloud-agents](https://cursor.com/dashboard/cloud-agents). Secrets are encrypted, exposed as environment variables, environment-scoped. Snapshot `.env.local` is possible but not recommended.

`[DOCS: https://cursor.com/docs/cloud-agent/api/endpoints]` — Session-scoped `envVars` on agent create (beta; verify injection).

`[DOCS: https://cursor.com/docs/cloud-agent/automations]` — Scheduled automations run unattended and inherit team/environment secrets when configured.

### D2. Probe of available secrets on this Cloud run

```text
ANTHROPIC_API_KEY=UNSET
UPRESS_SFTP_HOST=UNSET
UPRESS_SFTP_PORT=UNSET
UPRESS_SFTP_USER=UNSET
UPRESS_SFTP_PASS=UNSET
FTP_HOST=UNSET
FTP_USER=UNSET
FTP_PASS=UNSET
AOS_API_BASE=UNSET
AOS_ACTOR_API_KEY=UNSET
WAHA_API_KEY=UNSET
WAHA_URL=UNSET
CURSOR_API_KEY=UNSET

ls: cannot access '.env': No such file or directory
ls: cannot access '.env.local': No such file or directory
```

`[VERIFIED: env name presence loop; ls .env]`

**Injection is supported by product (docs), but no secrets were configured for this environment** — all UNSET. Before BUILD scheduling, team_00 must add at minimum:

| Secret | Needed for Cloud BUILD? | Needed for Cloud RUNTIME? |
|--------|-------------------------|---------------------------|
| `ANTHROPIC_API_KEY` | Desired for live smoke — **but E1 currently blocks use** | Would need E1 fix + key |
| `UPRESS_SFTP_*` | No (mock FTP in tests) | **No — uPress IP allowlist + ephemeral Cloud egress** |
| `AOS_API_BASE` / `AOS_ACTOR_API_KEY` | Optional messaging | **No — Tailscale required (E4)** |
| WAHA creds | No | **No — Tailscale / waldhomeserver** |

Mac `~/.aos/actor.env` is **not** available in Cloud.

---

## E. Network

### E1. `api.anthropic.com`

```text
$ curl -v --max-time 15 https://api.anthropic.com/ 2>&1 | tail -20
* Connected to api.anthropic.com (160.79.104.10) port 443
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* Recv failure: Connection reset by peer
curl: (35) Recv failure: Connection reset by peer
```

Reproduced **3/3** attempts; same via `urllib`. TCP connect succeeds; TLS handshake is reset.

`[VERIFIED: curl -v https://api.anthropic.com/ ×3]`

**Impact:** Live Anthropic API (runtime sonnet-5 generation, token_tracker live smoke) **cannot run on this Cloud egress path today.**

### E2. Public internet / web_search / web_fetch / general HTTP

| Target | Result |
|--------|--------|
| `https://pypi.org/simple/pytest/` | **HTTP 200** |
| `https://api.github.com/` | **HTTP 200** (×3) |
| `https://example.com/` | **TLS RST** |
| `https://www.google.com/` | **TLS RST** (×3) |
| IP echo hosts (`ifconfig.me`, `api.ipify.org`, …) | **TLS RST** |

`[VERIFIED: curl to each]`

**Egress is selective**, not fully open and not fully closed. PyPI + GitHub work (enough for `pip install` + git). Many general HTTPS destinations reset. Treat **web_search / arbitrary web_fetch as unreliable** on Cloud until an allowlist/policy is understood. Cursor-native agent tools may use backend-proxied fetch (not verified from VM shell).

### E3. uPress FTP (`ftp.s887.upress.link:21` — fixed host)

```text
FTP_TARGET=ftp.s887.upress.link:21
resolving ftp.s887.upress.link
ips ['185.201.148.144']
connected ('185.201.148.144', 21)
banner b''
```

`[VERIFIED: python socket.create_connection to ftp.s887.upress.link:21]`  
`[CANON: team_00 — uPress requires client IP allowlist for FTP]`

| Fact | Status |
|------|--------|
| DNS + TCP :21 from Cloud | PASS (banner empty) |
| Egress public IP (for allowlist) | **UNKNOWN** (all IP-echo hosts RST) |
| Scheduled FTP from Cloud | **NO-GO** — ephemeral Cloud egress IP cannot be maintainably allowlisted on uPress |

**FTP stays on waldhomeserver** (or any host with a stable allowlisted public IP).

### E4. Tailscale / AOS `100.125.98.56:8092` / waldhomeserver / WAHA

```text
$ curl -sS -o /dev/null -w "AOS … %{http_code}\n" --max-time 5 http://100.125.98.56:8092/api/system/health
curl: (52) Empty reply from server
AOS … 000
AOS_FAIL

$ curl … http://waldhomeserver/
curl: (6) Could not resolve host: waldhomeserver
WALD_FAIL

$ which tailscale tailscaled
which_exit=1
```

`[VERIFIED: curl AOS; curl waldhomeserver; which tailscale]`  
`[DOCS: https://cursor.com/docs/cloud-agent/setup]` — Tailscale **possible** only via userspace mode (`tailscaled --tun=userspace-networking` + proxy env); not present by default. Cloudflare Tunnel is an alternative.

**Default Cloud: NO Tailscale, NO AOS messaging, NO WAHA.** Opt-in infra would be a separate team_00 decision; not required for BUILD.

Contrast Mac (same day): `http://100.125.98.56:8092/api/system/health` → **HTTP 200**.

---

## F. Scheduling

### F1. Config surface

`[DOCS: https://cursor.com/docs/cloud-agent/automations]`

- UI: [cursor.com/automations](https://cursor.com/automations) (also Agents Window, `/automate` skill, Marketplace templates).
- Triggers: **cron / presets**, GitHub/GitLab/Bitbucket PR & push events, Slack, webhooks, Linear, Sentry, PagerDuty.
- Scheduled triggers “may run with a delay but will not start before the indicated time.”
- Must explicitly attach **repository** for code-changing automations (cron defaults to no-repo).

### F2. Concurrency, chaining, result sinks

| Topic | Finding |
|-------|---------|
| Concurrency limit | `[UNKNOWN]` — docs do not publish a hard concurrent-agent cap. Each agent = isolated VM. |
| Chain WP001→WP007 | **YES** — webhook trigger, or “PR merged” / “CI completed” (GitHub) trigger, or Memories across runs of the same automation |
| Result sinks | **PR** (default tool), committed file on agent branch, Slack message, webhook to internal systems, Memories |

`[DOCS: https://cursor.com/docs/cloud-agent/automations]`

**Mandate:** serialize P002 WP agents; unique branch per run; PR as SSoT of results.

### F3. Max session duration + resources

**Resources on this probe VM** (`[VERIFIED: nproc; free -h; df -h; /proc/meminfo; /proc/cpuinfo]`):

| Resource | Measured |
|----------|----------|
| CPU | **4** × Intel Xeon |
| RAM | **~16 GiB** total (`MemTotal: 16398460 kB`), ~14 GiB available |
| Disk | **252G** overlay, ~231G free |
| Swap | 0 |
| `ulimit` cpu time | unlimited |
| `ulimit` max memory | unlimited |

`[DOCS: https://cursor.com/docs/cloud-agent/setup]` — “default VM profile with limited memory and CPU”; Enterprise can request increases; self-serve custom resources “coming soon.”

**Max wall-clock session duration:** `[UNKNOWN]` — not published in consulted docs. WP006 (~1600 lines / 107 ACs) fits comfortably in 16 GiB / 4 CPU if installs are snapshotted; risk is agent context / run timeout, not RAM.

---

## G. Build vs runtime placement

| Runtime step | Cloud? | Evidence |
|--------------|--------|----------|
| Grok **BUILD** (write code, pytest, PR) | **YES with constraints** | A2/A3/B/C/F; bake venv+deps; branch discipline |
| Live Anthropic API smoke / sonnet-5 generation | **NO** | E1 TLS RST to `api.anthropic.com` |
| teaser.png (Pillow + Hebrew RTL) | **YES for generation-in-build tests** | A3 `raqm True`; runtime image still needs Anthropic content upstream |
| FTP upload to uPress | **NO** | IP allowlist + ephemeral egress (`[CANON]` + E3) |
| WhatsApp / WAHA | **NO** | E4 no Tailscale |
| AOS messaging (`100.125.98.56`) | **NO** | E4 |

### Recommended architecture

```text
┌─────────────────────────┐     PR / merge      ┌──────────────────────────────┐
│ Cursor Cloud (BUILD)    │ ──────────────────► │ origin/main                  │
│ Grok agent + pytest     │                     └──────────────┬───────────────┘
│ mock Anthropic in tests │                                    │ pull
│ unique branch → PR      │                                    ▼
└─────────────────────────┘                     ┌──────────────────────────────┐
                                                │ waldhomeserver (RUNTIME)     │
                                                │ sonnet-5 via Anthropic API   │
                                                │ teaser.png → FTP (allowlist) │
                                                │ WAHA WhatsApp + AOS message  │
                                                └──────────────────────────────┘
```

Live token_tracker settlement (pause_turn / cost caps / `allowed_callers`) that **requires** Anthropic HTTP: Mac or waldhomeserver — **not Cloud**.

---

## Verdicts

### BUILD verdict: **GO-WITH-CONSTRAINTS**

Cloud **can** host the P002 code BUILD (Grok Cloud Agent → implement WPs → pytest with mocks → PR) **if**:

1. Environment snapshot / `install` script includes `python3-venv` + project deps (`pytest`, `pytest-mock`, Pillow, …).
2. Secrets dashboard configured only as needed (Anthropic key **not usable from Cloud today** — do not block BUILD on it).
3. Branch-per-WP / no parallel commits to same branch.
4. Live Anthropic smoke tests **excluded** from Cloud BUILD ACs (run on Mac/waldhomeserver).
5. Model id = `cursor-grok-4.5-high` (not `grok-4`).
6. Cross-engine VALIDATE = second agent on Claude **Cursor model**, or Mac Claude validator — not Anthropic API from Cloud VM.

### RUNTIME verdict: **no** (weekly edition must stay on **waldhomeserver**)

| Step | Placement |
|------|-----------|
| sonnet-5 generation (Anthropic API) | **waldhomeserver** (Cloud: E1 blocked) |
| teaser.png | **waldhomeserver** (with generation) |
| FTP upload | **waldhomeserver** (uPress IP allowlist) |
| WhatsApp / WAHA | **waldhomeserver** (Tailscale) |
| AOS messaging | **waldhomeserver** (Tailscale) |

Partial Cloud runtime is **not** recommended: generation alone is blocked by E1, and distribution is blocked by FTP allowlist + Tailscale.

### Top 3 blockers / risks for this pipeline

1. **`api.anthropic.com` TLS RST from Cloud** — blocks live API smoke tests and any Cloud-hosted sonnet-5 runtime. Must settle token_tracker defects on Mac/waldhomeserver.
2. **uPress FTP IP allowlist + ephemeral Cloud egress** — FTP cannot be scheduled from Cloud; runtime publish stays on waldhomeserver.
3. **Concurrent-write discipline** — isolated VMs do not protect shared remote branches; serialize WP agents and unique-branch → PR only (already lost work once on Mac).

Honorable mention: stock image missing `python3-venv` (easy fix via snapshot); no secrets configured yet; selective HTTPS egress (web research from VM shell unreliable).

---

## Routing

- **Artifact:** `/Users/nimrod/Documents/AOS_V5/family-newsletter/_COMMUNICATION/team_110/CAPABILITIES_REPORT_team_110_CURSOR_CLOUD_2026-07-22_v1.0.0.md`
- **Cloud probe agent:** [bc-9e175a29-cf6f-4965-9f2a-0365528820c1](https://cursor.com/agents?id=bc-9e175a29-cf6f-4965-9f2a-0365528820c1) (if dashboard URL scheme differs, search agent id `bc-9e175a29-cf6f-4965-9f2a-0365528820c1`)
- **Responds to:** `_COMMUNICATION/team_110/RESEARCH_REQUEST_team_00_TO_team_110_CURSOR_CLOUD_CAPABILITIES_2026-07-22_v1.0.0.md`
- **Next:** team_00 / team_100 decide BUILD-in-Cloud + RUNTIME-on-waldhomeserver; configure Cloud env snapshot + Automations; schedule P002 Grok build with constraints above.

---

*team_110 · 2026-07-22 · empirical Cloud probe + Cursor docs*
