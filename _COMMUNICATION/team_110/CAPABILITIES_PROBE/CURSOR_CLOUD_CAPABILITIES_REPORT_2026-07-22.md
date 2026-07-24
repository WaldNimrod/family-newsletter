# Cursor Cloud Capabilities Report — Family Newsletter (team_110)

**Date:** 2026-07-22 (UTC)  
**Run:** https://cursor.com/agents/bc-6d332510-9f11-43ac-9ca5-66b6a764dade  
**Repo:** `github.com/WaldNimrod/family-newsletter`  
**Base commit requested:** `ef0e366` (present; ancestor of session HEAD)  
**This session model:** `cursor-grok-4.5-high`  
**Evidence log:** `/workspace/_COMMUNICATION/team_110/CAPABILITIES_PROBE/evidence.log`

Tags: `[VERIFIED:<cmd>]` empirical in this VM · `[DOCS:<url>]` Cursor docs · `[UNKNOWN]` not determinable here.

---

## A. RUNTIME & PACKAGES

### A1. OS / arch / Python / pip / venv

| Fact | Result |
|------|--------|
| OS | Linux 6.12.94+ x86_64 (`cursor` host) |
| Python | 3.12.3 |
| pip | present — pip 24.0 |
| venv | works **after** `sudo apt-get install -y python3.12-venv` (stock image lacks `ensurepip`) |

```text
$ uname -a
Linux cursor 6.12.94+ #1 SMP PREEMPT_DYNAMIC Mon Jul  6 18:05:21 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux

$ python3 --version
Python 3.12.3

$ pip3 --version
pip 24.0 from /usr/lib/python3/dist-packages/pip (python 3.12)

$ python3 -m venv /tmp/fnl-venv2 && /tmp/fnl-venv2/bin/python --version
Python 3.12.3
VENV_OK
```

[VERIFIED: `uname -a; python3 --version; pip3 --version; python3 -m venv …`]

Initial `python3 -m venv` **failed** with `ensurepip is not available` until `python3.12-venv` was installed via apt (sudo works).

### A2. PyPI installs

**Yes** — arbitrary public PyPI packages install successfully (`pypi.org` / `files.pythonhosted.org` are on the egress allowlist).

Install-test (all OK):

```text
$ pip3 install --user pytest pytest-mock Pillow feedparser requests jinja2 anthropic python-bidi
Successfully installed Pillow-12.3.0 … anthropic-0.118.0 … feedparser-6.0.12 …
  pytest-9.1.1 pytest-mock-3.15.1 python-bidi-0.6.11 jinja2-3.1.2 …
```

Import check: all packages import; versions recorded in evidence log.

**Limits:** egress is **restricted allowlist** (not offline). Non-allowlisted hosts are TCP-reset (`Connection reset by peer`). No PyPI allowlist beyond the platform default registries. `apt-get` to Ubuntu archives works.

[VERIFIED: `pip3 install --user …` + imports]  
[DOCS: https://cursor.com/docs/cloud-agent/security-network]

### A3. Hebrew RTL / raqm / python-bidi

**Stock Pillow (before apt):** not re-checked pre-install; after `sudo apt-get install -y libraqm0 libraqm-dev`:

```text
$ python3 -c "from PIL import features; print('raqm', features.check('raqm'))"
raqm True
```

**libraqm installable:** yes via apt (`libraqm0`, `libraqm-dev` installed successfully).

**python-bidi fallback:** yes — import + `get_display('שלום עולם')` works; wrote `/tmp/hebrew_bidi_test.png`. Acceptable fallback for bidi reorder; **raqm is preferred** for shaping/ligatures and is available after apt.

[VERIFIED: Pillow `features.check('raqm')`; `python-bidi` + Pillow draw]

### A4. Pre-installed toolchain

| Tool | Version |
|------|---------|
| git | 2.43.0 |
| node | v22.14.0 (`/exec-daemon/node`); also nvm node v22.22.2 |
| npm | 10.9.7 |
| gcc / g++ | 13.3.0 |
| make | 4.3 |
| clang | 18.1.3 |

[VERIFIED: `git/node/gcc/g++/make/clang --version`]

---

## B. GIT / REPO

### B1. How the session gets the repo / auth / `ef0e366`

- Workspace is a **checked-out clone** at `/workspace` (not empty; ready at session start).
- Remote configured as `https://github.com/WaldNimrod/family-newsletter`.
- Auth: **GitHub App installation token** (`ghs_*`) via `url.*.insteadof` rewrite to `https://x-access-token:***@github.com/` (also `gh` logged in as user `cursor`). Not a deploy key or long-lived PAT in the clear.
- `gh auth status`: logged in; `gh api user` → 403 (integration token scoped for repo ops, not user profile).

```text
$ git log --oneline ef0e366 -1
ef0e366 feat(P002): author 7 LOD400 build specs + register WP007 + lock DESIGN_FISH 'all fish' decision

$ git merge-base --is-ancestor ef0e366 HEAD && echo ef0e366_is_ancestor=yes
ef0e366_is_ancestor=yes
```

Session started with `origin/main` at `3aac420` (after `ef0e366`). Probe branch commit is `5a49892`.

[VERIFIED: `git log ef0e366`; `git push`; `gh auth status`]  
[DOCS: https://cursor.com/docs/cloud-agent/setup — Cursor manages workspace checkout]

### B2. Commit + push + PR

| Action | Result |
|--------|--------|
| commit | **Yes** |
| push new branch | **Yes** (`cursor/capabilities-probe-dade`) |
| open PR | **Yes** via platform `ManagePullRequest` (cloud agent instruction: do not use `gh` for PR writes) |

**Branch model (this agent / cloud instructions):** feature branches off base (`main`), named `cursor/<descriptive-name>-dade`, push with `-u origin`, open draft PR against `main`.

[VERIFIED: commit + `git push -u origin cursor/capabilities-probe-dade`]

### B3. Concurrent-write / lost-work risk

**No shared writable workspace between sessions.** Each cloud agent is an **isolated VM** ([DOCS: https://cursor.com/docs/cloud-agent/setup](https://cursor.com/docs/cloud-agent/setup)). Parallel agents do **not** share uncommitted files.

Collision modes that *do* lose work:

1. **Uncommitted work dies with the VM** if the session is killed/expires/archived before commit+push.
2. **Git remote races** if two agents push the **same branch** (non-fast-forward / overwrite).
3. Docs: *“You can run as many agents as you want in parallel”* ([DOCS: https://cursor.com/docs/cloud-agent](https://cursor.com/docs/cloud-agent)) — **no automatic lock** across agents.

**Hard requirement mitigation:**

- Unique branch per session (`cursor/<wp>-<runid>-dade`).
- Commit + push **before** long work / before any second session.
- Result sink = PR or committed artifact only (never “leave it in the VM”).
- Prefer one automation chain or explicit “wait for prior PR merge” prompts; do not schedule overlapping writers on the same branch.

[VERIFIED: isolated VM + successful exclusive branch push]  
[DOCS: https://cursor.com/docs/cloud-agent]

---

## C. BUILD ENGINE (Grok / cursor-agent)

### C1. Availability / model ids

| Item | Result |
|------|--------|
| This session **is** the Cloud Agent | `CURSOR_AGENT=1` |
| Model id | **`cursor-grok-4.5-high`** (MCP `run-info.originalModelName`) |
| `cursor-agent` CLI binary | **Not present** on PATH / under `/usr` `/opt` `/home/ubuntu` |
| Is `grok-4` valid? | **Not observed.** Valid observed id: `cursor-grok-4.5-high`. Task-tool allowlist also includes `cursor-grok-4.5-high-fast` (and other families). Bare `grok-4` is **not** evidenced here. |

[VERIFIED: MCP `run-info`; `which cursor-agent` → missing]  

### C2. Headless / non-interactive

Cloud sessions are **already headless/non-interactive** (no TTY agent CLI). Mac-style `cursor-agent -f` is N/A here; invocation surface is:

- Web / Automations / API kickoff → Cloud Agent VM runs autonomously.
- This run: `source=web`, model `cursor-grok-4.5-high`.

[VERIFIED: run metadata `source=web`, `status=RUNNING`]  
[DOCS: https://cursor.com/docs/cloud-agent/automations]

### C3. Grok build + Claude validate in ONE session

**Yes for Cursor-hosted models.** Empirically launched a Task subagent with `model=claude-opus-4-7-thinking-high`; it replied `CLAUDE_SUBAGENT_OK`.

So Iron Rule #1 (Grok builds → Claude validates) can be **same-session** via Task/subagent with a Claude model id — **without** calling `api.anthropic.com`.

**Separate concern:** pipeline **runtime** LLM via Anthropic Python SDK **cannot** call Anthropic from this egress policy (see E1).

[VERIFIED: Task subagent `claude-opus-4-7-thinking-high`]

---

## D. SECRETS

### D1. How secrets are supplied

| Mechanism | Status in **this** run |
|-----------|-------------------------|
| Dashboard Secrets tab → env vars | **Recommended by docs**; **none present** here (`ANTHROPIC_API_KEY`, `AOS_*` unset) |
| Environment-scoped secrets | Available when a saved environment is attached — this run has `environment: null` |
| Snapshot-baked `.env.local` | Possible but not recommended |
| Repo-committed `.env` | Not present / not used |

[VERIFIED: `echo ${ANTHROPIC_API_KEY:-UNSET}` → UNSET; MCP `environment-info` → `environment: null`]  
[DOCS: https://cursor.com/docs/cloud-agent/setup#environment-variables-and-secrets]

**Unattended scheduled runs:** same injection path — secrets configured on the **environment / team Secrets** that the automation binds to are available as env vars at boot.

### D2. Can keys be injected securely?

| Secret | Injectable via Secrets tab? | Usable **today** in this run? |
|--------|----------------------------|-------------------------------|
| `ANTHROPIC_API_KEY` | **Yes** (docs) | **No** — unset **and** `api.anthropic.com` egress-blocked |
| uPress FTP creds | **Yes** (docs) | **No** — FTP protocol fails (E3) |
| WAHA | **Yes** (docs) | **No** — host not reachable (E4) |
| `AOS_API_BASE` / `AOS_ACTOR_API_KEY` | **Yes** (docs) | **No** — unset; Tailscale target not functional (E4) |

[VERIFIED: env empty; network failures]  
[DOCS: https://cursor.com/docs/cloud-agent/setup]

---

## E. NETWORK

**Egress policy for this run:** `restricted: true` with a **default package/registry/GitHub allowlist** only. **Not** “allow all.” Custom domains (`api.anthropic.com`, `nimrod.bio`, general web) are **absent**.

[VERIFIED: MCP `environment-info.egress`]  
[DOCS: https://cursor.com/docs/cloud-agent/security-network]

### E1. `api.anthropic.com`

```text
$ curl -sS -o /dev/null -w "anthropic=%{http_code}\n" --max-time 5 https://api.anthropic.com/v1/messages
curl: (35) Recv failure: Connection reset by peer
anthropic=000

$ python3 -c "import anthropic; … messages.create(…)"
ANTHROPIC_SDK_ERR APIConnectionError Connection error.
```

**NO** live Anthropic API from this environment as configured.

### E2. Public internet / web_search / web_fetch / general HTTP

| Target | Result |
|--------|--------|
| `https://pypi.org`, `https://api.github.com`, `https://registry.npmjs.org` | **200** |
| `https://example.com`, `https://httpbin.org`, `https://news.ycombinator.com`, `https://feeds.bbci.co.uk/...`, `https://www.google.com` | **Connection reset** |
| Agent `WebFetch` to `cursor.com` | **Rejected: Domain not in network allowlist** |
| Agent `WebSearch` | Returns results (Cursor-side search backend — **not** equivalent to arbitrary HTTP from the VM) |

Researcher `requests`/`feedparser` against public RSS **fails** under current allowlist.

[VERIFIED: curl matrix + `requests.get`]

### E3. uPress FTP (`nimrod.bio`)

```text
TCP connect to nimrod.bio:21 / ftp.nimrod.bio:21 → OK (handshake)
ftplib.FTP.connect → EOFError (empty banner / protocol killed)
https://nimrod.bio → Connection reset
```

**FTP upload test: NO** under current egress (TCP may appear open; FTP application data does not work).

[VERIFIED: `ftplib` + curl]

### E4. Tailscale / AOS `100.125.98.56:8092` / `waldhomeserver` / WAHA

```text
$ curl -v --max-time 5 http://100.125.98.56:8092/api/system/health
* Connected to 100.125.98.56 … port 8092
* Empty reply from server
curl: (52) Empty reply from server

$ getent hosts waldhomeserver
(fail — Temporary failure in name resolution)

$ which tailscale
(not found)
```

MCP: `usePrivateWorker: false`, no Tailscale configured.

**Confirmed: private Tailscale services are NOT reachable for real AOS/WAHA use.** Spurious TCP “connect” to `100.125.98.56` does **not** speak HTTP health (empty reply). Docs allow Tailscale **userspace** mode in a configured environment ([DOCS: https://cursor.com/docs/cloud-agent/setup](https://cursor.com/docs/cloud-agent/setup) — Running Tailscale) but it is **not** set up here.

**Implication:** WhatsApp send (WAHA) + AOS messaging **must stay on waldhomeserver** unless Tailscale/Cloudflare Tunnel is deliberately provisioned into a Cloud Agent environment.

---

## F. SCHEDULING

### F1. Configuration surface

[DOCS: https://cursor.com/docs/cloud-agent/automations]

- **Cursor Automations:** schedule (presets or **cron**), or event triggers (GitHub/GitLab/Slack/webhooks/Linear/…).
- Configure via Agents Window, `cursor.com/automations`, `/automate` skill, or marketplace templates.
- Must attach a **repository** (cron defaults to *no repo* — agents cannot edit/PR without an explicit repo binding).

No automation exists yet for this repo (`list-cloud-agents` with `sources=["automations"]` → 0).

[VERIFIED: MCP list automations agents = 0]  
[DOCS: https://cursor.com/docs/cloud-agent/automations]

### F2. Concurrency / chaining / result sinks

| Question | Answer |
|----------|--------|
| Concurrency limits | Docs: run **as many agents as you want in parallel** — no built-in mutex. |
| Chain WP001→WP002… | Possible via **sequential automations** (webhook/PR trigger on prior completion) or one long prompt that does all WPs; **not** a first-class “workflow DAG” evidenced in docs. |
| Result sinks | **PR** (verified), **committed files** (verified), Slack/webhook outputs per automations docs. |

[DOCS: https://cursor.com/docs/cloud-agent]  
[VERIFIED: PR/commit sinks]

### F3. Duration + resources

| Resource | Measured |
|----------|----------|
| RAM (host) | **15 GiB** total; cgroup `memory.max` = **17179869184** (16 GiB) |
| CPU | **4** cores; cgroup `cpu.max` = `400000 100000` (4 CPUs) |
| Disk | **252G** overlay, ~231G free |
| Max session duration | **No hard number found in docs.** Team admin toggle: **Long running agents**. [DOCS: https://cursor.com/docs/cloud-agent/settings] |

WP006 (~1600 lines / 107 ACs): **resources are adequate** for Python build/test. Risk is **egress** and **session/context**, not RAM/CPU.

[VERIFIED: `free`, `nproc`, cgroup files, `df`]  
[DOCS: https://cursor.com/docs/cloud-agent/setup#resource-limits]

---

## G. BUILD vs RUNTIME

### G1. What can run here?

| Stage | Capability |
|-------|------------|
| **BUILD** (code, tests with mocks, commit, PR, Grok build + Claude subagent validate) | **Yes**, with constraints below |
| **RUNTIME** weekly pipeline end-to-end | **No** in current config |

#### Runtime step matrix

| Step | Here? | Why |
|------|-------|-----|
| Install deps / venv / pytest | **CAN** | PyPI + apt work |
| Dual-driver LLM code paths (unit tests / mocks) | **CAN** | No network needed |
| Live `claude-sonnet-5` via Anthropic API | **CANNOT** | Egress reset; key unset |
| Researcher web/RSS harvest | **CANNOT** | General HTTP blocked |
| Pillow teaser.png + Hebrew RTL | **CAN** (local) | raqm + python-bidi after apt |
| FTP teaser upload (uPress) | **CANNOT** | FTP EOF / host not allowlisted |
| Email publisher (if SMTP public) | **UNKNOWN** / likely **CANNOT** without allowlist |
| WhatsApp via WAHA on waldhomeserver | **CANNOT** | No Tailscale / DNS |
| AOS messaging (`100.125.98.56:8092`) | **CANNOT** | No functional Tailscale path |

**Must stay on waldhomeserver (unless env is rebuilt):** live Anthropic generation (or open egress + secret), FTP publish, WAHA/WhatsApp, AOS API.

To make Cloud partially runtime-capable you would need, at minimum:

1. Network mode **Default + allowlist** (or Allow all) adding `api.anthropic.com` and research domains.  
2. Secrets: `ANTHROPIC_API_KEY`, FTP, etc.  
3. Tailscale userspace **or** Cloudflare Tunnel for AOS/WAHA.  
4. Snapshot with `python3.12-venv`, `libraqm0`, pip deps.

Even then, WAHA/WhatsApp is a private-network concern.

---

## VERDICTS

### BUILD verdict: **GO-WITH-CONSTRAINTS**

Safe for P002 **implementation + unit tests + commit/PR**, Grok as builder (`cursor-grok-4.5-high`), Claude as **same-session Task subagent** for validation.

Constraints:

1. Create a saved **environment snapshot** (venv/libraqm/pip preinstalled) — stock image needs apt for venv/raqm.
2. Preflight **unique branch + early commit/push** to prevent lost work under parallel sessions.
3. Do **not** rely on live Anthropic / public web / FTP in CI-style tests unless egress is widened.
4. Model id is **`cursor-grok-4.5-high`**, not bare `grok-4`.

### RUNTIME verdict: **partially / no end-to-end**

| Class | Location |
|-------|----------|
| Local image generation, pure Python transforms, templating | *Could* run in Cloud after snapshot |
| Live LLM, web research, FTP upload, WhatsApp, AOS messaging | **Must stay on waldhomeserver** (current Cloud) |

**Weekly RUNTIME host recommendation:** keep on **waldhomeserver**; use Cursor Cloud for **BUILD only** until egress + Tailscale + secrets are deliberately provisioned.

### Top 3 blockers for the full pipeline

1. **Restricted egress** — blocks `api.anthropic.com`, general HTTP/RSS (researcher), and effective FTP to `nimrod.bio`.  
2. **No Tailscale / private network** — AOS (`100.125.98.56:8092`) and WAHA/`waldhomeserver` unreachable → WhatsApp + AOS messaging cannot run here.  
3. **No secrets bound to this run** (`environment: null`) — even if egress were opened, `ANTHROPIC_API_KEY` / FTP / AOS keys are not injected for unattended execution today.

---

*Probe agent: team_110 · branch `cursor/capabilities-probe-dade` · evidence in this directory.*
