# MANDATE — Team 100 Local Agent: v3.0.0 Pilot Build & Distribution
**Date:** 2026-04-10
**From:** Team 100 (Cowork) via Team 00 (Nimrod)
**To:** Team 100 (Local Claude Code Agent — Domain: family-newsletter)
**Priority:** CRITICAL — Execute immediately upon receipt
**Target Version:** v3.0.0

---

## 0. Role Definition

You are **Team 100**, the local Claude Code agent operating on Nimrod's home server with **full network access** (SSH, HTTP, SMTP, FTP). You have capabilities the Cowork sandbox does not: real outbound HTTP, git push/pull, Claude API calls, SMTP email delivery, and FTP uploads.

Your mission: execute a **complete real end-to-end pilot build** of the Family Newsletter v3.0.0 and distribute it to all 5 family members. This is the **first real edition** — it must contain real content, real links, real weather data, and zero placeholders.

---

## 1. Context: What Happened Before You

The Cowork session (Team 100 Sandbox) made extensive v3.0.0 code changes across 10+ files. These changes have been **committed and pushed** to `origin/main` (4 commits, tag `v3.0.0` on commit `7ab2b14`). However, the currently deployed HTML at `https://www.nimrod.bio/agents/newsletter/2026-04-10/index.html` was built from **old pre-v3.0.0 code** and contains critical issues.

### 1.1 — Commits to pull (already pushed to origin/main)

| Commit | Description |
|--------|-------------|
| `5e96d59` | v2.0.0: Weekly cadence, bug fixes, template overhaul, style guide |
| `1f46459` | fix(BUG-1): add email addresses for all 5 family members |
| `535c11c` | v3.0.0: Real content pipeline — weather, opener, closer + e2e pilot mandate |
| `7ab2b14` | v3.0.0: Final fixes — version footer, real URLs, pilot mandate |

### 1.2 — Key code changes in v3.0.0

**`src/m3_normalizer.py`** — 3 new generation functions:
- `_generate_opener()`: Warm Hebrew intro paragraph (Style A / Simaniia)
- `_generate_closer()`: Warm Hebrew closing paragraph (Style A / Simaniia)
- `_fetch_weather()`: 7-day forecast from Open-Meteo API for Pardes Hanna (32.47°N, 34.97°E) and Basel (47.56°N, 7.59°E)
- All three wired into `generate_content()` steps 8-10 and `_build_neo()` metadata

**`src/models.py`** — Added to `GeneratedContent` dataclass:
- `opener_text: str = ""`
- `closer_text: str = ""`
- `weather: list = field(default_factory=list)`

**`src/m2_scanner.py`** — Mock data URLs replaced:
- ALL 16 `example.com` URLs replaced with real source domains (yachtingworld.com, nature.com, anthropic.com, etc.)
- User-Agent updated to "FamilyNewsletter/2.0"

**`src/m4_renderer.py`** — Version tracking:
- `SYSTEM_VERSION = "3.0.0"`
- `build_timestamp` passed to template
- Character schedule and emoji fallback system

**`templates/newsletter.html.j2`** — Footer version line:
- Added `v{{ system_version }} • built {{ build_timestamp }}` to footer

**`src/m5_distributor.py`** — Branding: "Family Newsletter" → "Family Newsletter"

**`src/env_compat.py`** — Default from: `newsletter@nimrod.bio`

**`src/orchestrator.py`** — Renamed daily→weekly commands (with backward-compat aliases)

**`config/family.json`** — BUG-1 fix:
- `family_name`: "בית ולד" (was "משפחת בן-צבי ולד")
- Emails added for all 5 members:
  - nimrod@mezoo.co
  - michal@hbarc.co.il (alt: hobbithome@mezoo.co)
  - shakedwald@gmail.com
  - mayyanwald@gmail.com
  - tslilwald@gmail.com

**`STYLE_GUIDE.md`** — Binding editorial style:
- Style A (Simaniia/warm): Opener + Closer — warm, personal Hebrew, family-oriented
- Style B (Calcalist/factual): Article summaries — concise, informative, Hebrew

---

## 2. Known Issues on the Currently Deployed Page

**Live URL:** `https://www.nimrod.bio/agents/newsletter/2026-04-10/index.html`

The Cowork session performed a browser audit of the live page and found these 11 issues:

| # | Issue | Root Cause | v3.0.0 Fix |
|---|-------|-----------|------------|
| 1 | ALL 32 article links point to `example.com` | Mock data built into HTML | Real RSS fetch (not `--mock`) |
| 2 | No opener section | `_generate_opener()` didn't exist | Added in m3_normalizer |
| 3 | No closer section | `_generate_closer()` didn't exist | Added in m3_normalizer |
| 4 | No weather section | `_fetch_weather()` didn't exist | Added in m3_normalizer |
| 5 | "character placeholder" text visible | No character PNG assets | Emoji fallback in v3.0.0 (expected for pilot) |
| 6 | Greeting says "משפחת בן-צבי ולד" | Old family_name in config | Changed to "בית ולד" |
| 7 | "[Mock response for history]" visible | Mock AI responses in output | Real Claude API call |
| 8 | No version number in footer | Footer didn't have version | Added `v{{ system_version }}` |
| 9 | JS code leaking into visible footer | Template escaping issue | Fixed in template |
| 10 | Large blank areas in layout | Missing sections (weather, opener, closer) | Sections now populated |
| 11 | All content is mock/fallback data | Build ran with `--mock` or old code | Real build with v3.0.0 code |

**All issues except #5 are resolved by v3.0.0 code + a real (non-mock) build.**
Issue #5 (character PNG assets) is expected — emoji fallback is the correct behavior for the pilot.

---

## 3. Task: Full E2E Pilot Build

### Phase 1 — Pull & Install

```bash
cd /data/projects/family-newsletter  # or wherever the project lives
git pull origin main
git log --oneline -5  # verify commit 7ab2b14 (v3.0.0) is present
source venv/bin/activate
pip install -r requirements.txt
```

**Verify environment variables** (all must be set and non-empty):
```bash
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:+SET}"
echo "UPRESS_SFTP_HOST: ${UPRESS_SFTP_HOST:+SET}"
echo "EMAIL_SMTP_HOST: ${EMAIL_SMTP_HOST:+SET}"
echo "EMAIL_PASSWORD: ${EMAIL_PASSWORD:+SET}"
```

If `ANTHROPIC_API_KEY` is not set, the build WILL FAIL. Set it in `.env` before proceeding.

### Phase 2 — Delete Stale Data

The previous mock build may have cached stale NCIs in the database, causing dedup to skip real items:

```bash
# IMPORTANT: Remove stale DB to prevent dedup conflicts
rm -f data/family.db
# Also remove any stale HTML from today
rm -f data/archive/html/2026-04-10.html
```

### Phase 3 — Execute Real Build

```bash
python -m src.orchestrator weekly-build
```

**This will execute the full 6-module pipeline:**
- **M1**: Load 5 member profiles from `config/family.json`
- **M2**: Fetch REAL content from 15+ active RSS/web/YouTube sources
- **M3**: Score, curate, and generate ALL AI content via Claude API:
  - Opener (warm Hebrew intro, Style A)
  - Personalized headlines + summaries per member
  - Math puzzle for צליל
  - "Today in history" fact
  - Discovery bridges (cross-member recommendations)
  - Survey question
  - Closer (warm Hebrew sign-off, Style A)
  - Weather forecast (Open-Meteo API — Pardes Hanna + Basel)
- **M4**: Render HTML via Jinja2 template

**Expected output:** `data/archive/html/2026-04-10.html` (should be 25-45KB)

**Do NOT use the `--mock` flag.** The build must use real RSS sources and real Claude API calls.

**Expected cost:** ~$0.15-$0.30 in Claude API tokens.

---

## 4. E2E Content Validation

After the build completes, run ALL of the following checks **before distributing**.

### 4.1 — Basic HTML validation
```bash
HTML_FILE="data/archive/html/2026-04-10.html"
echo "File size: $(wc -c < $HTML_FILE) bytes"
# MUST be > 10,000 bytes. If smaller, build failed.
```

### 4.2 — Check for placeholder/mock content
```bash
# ALL of these MUST return 0:
grep -ci 'example\.com' "$HTML_FILE"
grep -ci 'lorem ipsum' "$HTML_FILE"
grep -ci 'placeholder' "$HTML_FILE"
grep -ci '\bTODO\b' "$HTML_FILE"
grep -ci '\bMOCK\b' "$HTML_FILE"
grep -ci 'Mock response' "$HTML_FILE"
```

**If any count > 0, STOP.** Investigate why mock content is present. Likely causes:
- DB wasn't cleared (stale NCIs from previous mock run)
- Claude API key missing (fallback to mock responses)
- RSS sources unreachable (network issue)

### 4.3 — Check all sections are populated
```bash
# These MUST exist in the HTML:
grep -c 'opener' "$HTML_FILE"         # opener section
grep -c 'weather-section' "$HTML_FILE" # weather forecast
grep -c 'closer' "$HTML_FILE"         # closer section
grep -c 'hero-panel' "$HTML_FILE"     # at least 1 hero article
grep -c 'feat-panel' "$HTML_FILE"     # at least 2 feature articles
grep -c 'puzzle' "$HTML_FILE"         # math puzzle for Tzlil
grep -c 'survey' "$HTML_FILE"         # survey section
```

### 4.4 — Validate ALL article URLs
```bash
python3 -c "
import re, requests, sys
html = open('$HTML_FILE').read()
urls = set(re.findall(r'href=\"(https?://[^\"]+)\"', html))
print(f'Found {len(urls)} unique URLs')
broken = []
for url in urls:
    try:
        r = requests.head(url, timeout=10, allow_redirects=True)
        if r.status_code >= 400:
            broken.append(f'{r.status_code} {url}')
            print(f'  BROKEN: {r.status_code} {url}')
        else:
            print(f'  OK: {url}')
    except Exception as e:
        broken.append(f'ERROR {url}: {e}')
        print(f'  ERROR: {url}: {e}')
if broken:
    print(f'\n{len(broken)} BROKEN LINKS:')
    for b in broken:
        print(f'  {b}')
    if len(broken) > 2:
        print('WARNING: More than 2 broken links. Investigate before distributing.')
        sys.exit(1)
else:
    print(f'\nAll {len(urls)} links OK')
"
```

**Acceptance:** ≤2 broken links is acceptable (RSS sources may have rotated). >2 broken links requires investigation.

### 4.5 — Validate weather data
```bash
grep -oP '\d+°' "$HTML_FILE" | head -5
# Should show real temperatures (15-40°C range for Israel, 5-25°C for Basel)
```

### 4.6 — Validate Hebrew content
```bash
# Check opener is real Hebrew text (not empty or placeholder)
python3 -c "
import re
html = open('$HTML_FILE').read()
# Look for Hebrew characters in opener section
opener_match = re.search(r'opener.*?</div>', html, re.DOTALL)
if opener_match:
    hebrew = re.findall(r'[\u0590-\u05FF]+', opener_match.group())
    print(f'Opener: {len(hebrew)} Hebrew words found')
    if len(hebrew) < 5:
        print('WARNING: Opener may be empty or placeholder')
else:
    print('ERROR: No opener section found')
"
```

### 4.7 — Validate family name
```bash
# Must show "בית ולד", NOT "משפחת בן-צבי ולד"
grep -c 'בית ולד' "$HTML_FILE"
grep -c 'משפחת בן-צבי ולד' "$HTML_FILE"  # this MUST be 0
```

### 4.8 — Validate version footer
```bash
grep -c 'v3.0.0' "$HTML_FILE"  # Must be > 0
```

---

## 5. Visual Inspection (Browser MCP)

**CRITICAL REQUIREMENT:** After validation checks pass, open the generated HTML file in a browser and perform visual inspection. If you have MCP browser tools, take screenshots as artifacts.

Check:
- [ ] Hebrew text renders correctly (RTL direction)
- [ ] Weather graph bars display with real temperatures
- [ ] Opener paragraph is warm, personal Hebrew (not markdown or raw text)
- [ ] Member sections have REAL article headlines from real sources (not "Title here")
- [ ] Closer paragraph is warm Hebrew sign-off
- [ ] Images load (Unsplash) or fallback gradients display correctly
- [ ] Character emoji (🎩) displays (NOT "character placeholder" text)
- [ ] Footer shows "v3.0.0 • built 2026-04-10 HH:MM:SS"
- [ ] No blank areas or missing sections
- [ ] Links in articles point to real URLs (not example.com)

---

## 6. Distribution

**Only proceed if ALL checks in Sections 4 and 5 pass.**

### 6.1 — Upload to FTP and send emails
```bash
python -m src.orchestrator weekly-send
```

This will:
1. Upload HTML to `ftp.s887.upress.link` → public URL on nimrod.bio
2. Send personalized email to each family member:
   - nimrod@mezoo.co
   - michal@hbarc.co.il
   - shakedwald@gmail.com
   - mayyanwald@gmail.com
   - tslilwald@gmail.com

### 6.2 — Verify public URL
```bash
curl -s -o /dev/null -w "%{http_code}" "https://www.nimrod.bio/agents/newsletter/2026-04-10/index.html"
# Must return 200
```

### 6.3 — Verify live page content (Browser MCP)

**MANDATORY:** Navigate to `https://www.nimrod.bio/agents/newsletter/2026-04-10/index.html` in a browser and verify that the DEPLOYED version matches the local build. Take screenshots as proof artifacts.

Specifically confirm:
- [ ] Real article headlines (not mock)
- [ ] All links point to real sources (not example.com)
- [ ] Opener section present with Hebrew text
- [ ] Closer section present with Hebrew text
- [ ] Weather section with real temperatures
- [ ] Family greeting says "בית ולד"
- [ ] Version footer shows v3.0.0
- [ ] No "[Mock response for history]" text anywhere
- [ ] No "character placeholder" text (should show 🎩 emoji)

---

## 7. Post-Distribution Checks

```bash
# Check distribution results in logs:
tail -50 logs/newsletter-2026-04-10.log | grep -E '\[M5\]'
# Should show: FTP upload success + email sent to each member
```

---

## 8. Success Criteria

ALL of the following must be true:

| # | Criterion | Check |
|---|-----------|-------|
| 1 | HTML > 10KB with real content | `wc -c` > 10000 |
| 2 | Zero placeholder/mock text | grep returns 0 for all patterns |
| 3 | ≤2 broken links | URL validation script |
| 4 | Weather section shows real temperatures for Pardes Hanna + Basel | grep for °C values |
| 5 | Opener + Closer are real Hebrew editorial text (Style A) | Hebrew word count > 5 |
| 6 | All 5 member sections populated with real articles | grep for hero-panel, feat-panel |
| 7 | Math puzzle exists and is non-trivial | grep for puzzle section |
| 8 | Family greeting says "בית ולד" | grep confirms |
| 9 | Footer shows v3.0.0 | grep confirms |
| 10 | FTP upload returned 200 | curl check |
| 11 | All 5 emails sent successfully | M5 log check |
| 12 | Live page visual inspection passes | Browser MCP screenshots |

---

## 9. Required Artifacts

After completing the mission, produce the following artifacts:

1. **Validation report** — `REPORT_PILOT_v3.0.0_2026-04-10.md` in the project root, containing:
   - Build success/failure status
   - Number of articles fetched + selected per member
   - Weather data status (both cities)
   - Link validation results (total links, broken count, details)
   - Distribution results per family member (email sent/failed)
   - Any errors encountered and how they were resolved
   - Public URL of published edition
   - Claude API token cost for this build

2. **Browser screenshots** — Screenshots of the live deployed page at `https://www.nimrod.bio/agents/newsletter/2026-04-10/index.html` showing:
   - Full page overview
   - Opener section
   - Weather section
   - A member section with real articles
   - Closer section
   - Footer with version

3. **Response file** — Write to `~/agent_comm/outbox/REPORT_PILOT_E2E_2026-04-10.md` for Team 00 routing.

---

## 10. Known Issues & Expected Behavior

1. **Character assets (PNG):** Not yet created. The 🎩 emoji fallback is correct and expected for the pilot. Do NOT treat this as a failure.

2. **Phone numbers:** Still placeholders in family.json. WhatsApp distribution will fall back to email. This is acceptable.

3. **Degraded RSS sources (7 of 22):** Some sources are marked degraded and will be skipped. The remaining 15 should provide enough content. If M2 returns 0 items from ALL sources, check server connectivity.

4. **Open-Meteo weather API:** Free, no key required. If it fails, the weather section will gracefully not render (the newsletter still works). This is acceptable for the pilot but should be investigated.

5. **Claude API tokens:** Expected cost: ~$0.15-$0.30. Weekly alert threshold: $1.00.

6. **Style guide:** All AI-generated Hebrew text MUST follow `STYLE_GUIDE.md` at project root. Style A (Simaniia/warm) for opener/closer, Style B (Calcalist/factual) for article summaries.

7. **Jinja2 `autoescape=True`:** The template uses autoescaping. Any HTML content in template variables must use the `|safe` filter. This is already handled in v3.0.0 code.

8. **DB dedup:** If you see 0 articles selected after M2 reports items fetched, the DB has stale entries. Delete `data/family.db` and re-run.

---

## 11. Cron Schedule (Post-Pilot)

After successful pilot distribution, set up the weekly cron schedule:

```cron
TZ=Asia/Jerusalem
# Weekly build: Friday 09:00 IST
0  9 * * 5  cd /data/projects/family-newsletter && ./run.sh weekly-build  >> logs/cron.log 2>&1
# Weekly send: Friday 12:00 IST
0 12 * * 5  cd /data/projects/family-newsletter && ./run.sh weekly-send   >> logs/cron.log 2>&1
```

**Day `5` = Friday. Not `*` (daily).**

---

## 12. Project Structure Reference

```
family-newsletter/
├── config/
│   ├── family.json          # 5 member profiles with emails, interests, RSS sources
│   └── settings.yaml        # system config (API keys, thresholds, paths)
├── src/
│   ├── orchestrator.py      # CLI entry point: weekly-build, weekly-send, weekly-survey
│   ├── m1_profiles.py       # Load member profiles from family.json
│   ├── m2_scanner.py        # Fetch RSS/web/YouTube + mock fallback
│   ├── m3_normalizer.py     # Score, curate, generate AI content (Claude API)
│   ├── m4_renderer.py       # Jinja2 template → HTML
│   ├── m5_distributor.py    # FTP upload + email delivery
│   ├── m6_feedback.py       # Click tracking + survey (future)
│   ├── models.py            # Dataclasses: NCI, NEO, GeneratedContent, etc.
│   ├── db.py                # SQLite database operations
│   ├── env_compat.py        # Environment variable resolution
│   └── token_tracker.py     # Claude API cost tracking
├── templates/
│   └── newsletter.html.j2   # Main Jinja2 HTML template
├── data/
│   ├── archive/html/        # Generated HTML files by date
│   └── family.db            # SQLite DB (NCIs, newsletters, surveys)
├── STYLE_GUIDE.md           # Binding editorial style guide
├── MANDATE_TEAM100_PILOT_v3.0.0.md  # This file
├── run.sh                   # Shell wrapper for orchestrator
└── requirements.txt         # Python dependencies
```

---

## 13. Family Members Reference

| Member | Hebrew | Role | Email | Key Interests |
|--------|--------|------|-------|---------------|
| Nimrod | נימרוד | אבא | nimrod@mezoo.co | Sailing, architecture, AI, sustainability |
| Michal | מיכל | אמא | michal@hbarc.co.il | Dance, mindfulness, anthroposophy, nature |
| Shaked | שקד | בן | shakedwald@gmail.com | Gaming, sci-fi, fantasy, YouTube |
| Maayan (Yoyo) | מעיין (יויו) | בת | mayyanwald@gmail.com | Circus, dance, acrobatics, travel |
| Tzlil | צליל | בת | tslilwald@gmail.com | Math, Minecraft, baking, capoeira |

---

*Mandate issued by Team 100 (Cowork Session) — approved by Team 00 (Nimrod)*
*Execute upon receipt. Report results via artifacts and ~/agent_comm/outbox/*
*Version: v3.0.0 — First real edition. It must be perfect.*
