# Famely Neuslettr - תהליך יומי, הפצה, משוב ושמירת מידע
## v1.0 POC Architecture

---

## 1. התהליך היומי - מה רץ כל יום?

### זרימה מלאה (Production)

```
05:30  CRON trigger
  │
  ├─ FETCH ──────────────────────────────────────────────────
  │   │  לכל מקור מידע ב-sources (RSS, websites, APIs):
  │   │    1. שלוף תכנים חדשים מ-24 שעות אחרונות
  │   │    2. שמור raw content ב-archive (JSON + SQLite)
  │   │    3. הוסף metadata: source, timestamp, language, hash
  │   │  
  │   │  לתוכן משפחתי (WhatsApp uploads):
  │   │    1. קרא הודעות שהתקבלו מהבוט מ-24 שעות אחרונות
  │   │    2. סווג: תמונה / קישור / טקסט חופשי
  │   │    3. שמור ב-family_content table
  │   │
  │   └─ Output: raw_items[] (כל הפריטים הגולמיים)
  │
  ├─ DEDUPE & FILTER ────────────────────────────────────────
  │   │  1. hash-based dedup (כותרת + URL)
  │   │  2. סנן תוכן שכבר הופיע בניוזלטרים קודמים
  │   │  3. סנן תוכן לא מתאים (spam, paywall, broken links)
  │   │
  │   └─ Output: clean_items[]
  │
  ├─ SCORE ──────────────────────────────────────────────────
  │   │  לכל פריט × לכל בן משפחה:
  │   │    1. keyword match (topic + subtopics) → base score
  │   │    2. priority weight (high=3x, medium=2x, low=1x)
  │   │    3. source trust score (from feedback history)
  │   │    4. freshness boost (newer = higher)
  │   │    5. engagement history boost (topics clicked before)
  │   │    6. novelty penalty (similar to recent items = lower)
  │   │  
  │   │  Score = weighted sum, normalized to 0-100
  │   │
  │   └─ Output: scored_items[member_id] → sorted list
  │
  ├─ CURATE ─────────────────────────────────────────────────
  │   │  1. Select TOP-N per member (from content_preferences)
  │   │  2. Balance topics (no more than 60% from one topic)
  │   │  3. Pick 1 "discovery" item (cross-pollination)
  │   │  4. Include family-uploaded content
  │   │  5. Generate daily trivia/puzzle (Claude)
  │   │
  │   └─ Output: curated{member_sections, family, discovery, trivia}
  │
  ├─ GENERATE ───────────────────────────────────────────────
  │   │  For each curated item, call Claude API:
  │   │    1. Generate headline (short, catchy)
  │   │    2. Generate summary (per member's language & length pref)
  │   │    3. Generate trivia/puzzle (for Tzlil: math, for all: history)
  │   │    4. Generate daily greeting (weather-aware, date-aware)
  │   │    5. Generate discovery bridge text ("Nimrod → Tzlil: ...")
  │   │  
  │   │  All summaries saved to archive for future reference
  │   │
  │   └─ Output: enriched{} with all generated text
  │
  ├─ BUILD ──────────────────────────────────────────────────
  │   │  1. Load Jinja2 template (newsletter.html)
  │   │  2. Render with enriched content
  │   │  3. Inline all CSS (email/WhatsApp preview compat)
  │   │  4. Add tracking pixels per item (1x1 transparent PNG)
  │   │  5. Add UTM parameters to all links
  │   │  6. Generate og:meta tags for WhatsApp link preview
  │   │  7. Save local copy to archive
  │   │
  │   └─ Output: final HTML string
  │
  ├─ UPLOAD ─────────────────────────────────────────────────
  │   │  1. Upload HTML to static server:
  │   │     /newsletter/2026-04-08/index.html
  │   │  2. Upload og:image for WhatsApp preview
  │   │  3. Verify URL is accessible (health check GET)
  │   │
  │   └─ Output: public URL
  │
  └─ SEND (WhatsApp) ───────────────────────────────────────
      │  For each family member with phone number:
      │    1. Send template message via WhatsApp Business API:
      │       "בוקר טוב [שם]! ☀️
      │        [כותרת יומית מותאמת]
      │        📖 [URL]"
      │    2. Log send status
      │
      └─ Output: send_log[]

21:00  FEEDBACK CRON
  │
  └─ Send feedback survey to each member (see Section 3)
```

### זרימת POC v1.0 (מה שנבנה עכשיו)

```
POC מצומצם - רץ ידנית, בלי WhatsApp, בלי שרת:

  python main.py run --date 2026-04-08

  FETCH ───→ SCORE ───→ CURATE ───→ GENERATE ───→ BUILD
    │                                                  │
    │  RSS feeds only                    Local HTML file
    │  (no WhatsApp input)               (open in browser)
    │
    └── Archive to SQLite ←────── All steps log to DB
```

**מה נכלל ב-POC:**
- ✅ איסוף RSS אמיתי (feedparser)
- ✅ ניקוד לפי פרופילי משפחה
- ✅ תמהיל עם discovery
- ✅ סיכומים עם Claude API
- ✅ בניית HTML מהתבנית שאושרה
- ✅ שמירה ל-SQLite (archive)
- ✅ Output: קובץ HTML מוכן לצפייה

**מה לא נכלל ב-POC (Phase 2+):**
- ❌ שליחת WhatsApp
- ❌ העלאה לשרת
- ❌ קבלת תוכן משפחתי דרך WhatsApp
- ❌ משוב אוטומטי
- ❌ תזמון אוטומטי (cron)

---

## 2. הפצה - איך הניוזלטר מגיע למשפחה?

### ארכיטקטורת הפצה

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  HTML file   │────→│  Static Server   │────→│  WhatsApp msg   │
│  (rendered)  │     │  (S3/Vercel/CF)  │     │  with link      │
└─────────────┘     └──────────────────┘     └─────────────────┘
                           │
                    URL structure:
                    /newsletter/YYYY-MM-DD/index.html
                           │
                    og:meta tags for
                    rich WhatsApp preview:
                    ┌───────────────────┐
                    │ 📰 הניוזלטר של   │
                    │ משפחת בן-צבי ולד  │
                    │ 8 באפריל 2026     │
                    │ [thumbnail image]  │
                    └───────────────────┘
```

### הודעת WhatsApp

```
בוקר טוב נימרוד! ☀️

📰 הניוזלטר המשפחתי - יום רביעי
⛵ סקיפר ישראלי מתעד הפלגה ביוון
🎪 מעיין - CNAC פתחו הרשמה!
🧮 צליל - חידה חדשה מחכה לך

👉 https://newsletter.family/2026-04-08

יום נפלא! 💙
```

**כל בן משפחה מקבל הודעה מותאמת** - הכותרות משתנות לפי מה שרלוונטי לו.

### WhatsApp Business API Setup

```
Provider: Twilio (or Meta direct)
Template: "daily_newsletter" (pre-approved)
Webhook: receives replies → feedback processing
```

---

## 3. משוב - איך לומדים מה עבד?

### 3 ערוצי משוב

```
┌─────────────────────────────────────────────────────────┐
│                    FEEDBACK CHANNELS                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. PASSIVE (אוטומטי, בלי מאמץ מהמשתמש)              │
│     ├─ Click tracking: UTM params on all links          │
│     ├─ Read tracking: pixel per section                 │
│     ├─ Time on page: JS beacon on scroll/focus          │
│     └─ Share tracking: share button clicks              │
│                                                         │
│  2. ACTIVE-LIGHT (תגובה מהירה)                         │
│     ├─ Emoji rating in newsletter (😍😊😐👎)            │
│     ├─ WhatsApp survey at 21:00 (reply 1-4)            │
│     └─ "More like this" button per article              │
│                                                         │
│  3. ACTIVE-DEEP (פעם בשבוע/חודש)                       │
│     ├─ Weekly summary + "What did you like most?"       │
│     ├─ Monthly: "Add/remove topics?"                    │
│     └─ Quarterly: Full preference review                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### תהליך המשוב היומי

```
21:00  WhatsApp Bot sends:
       "היי נימרוד! איך היה הניוזלטר היום?
        1️⃣ מעולה   2️⃣ טוב   3️⃣ לא הפעם   4️⃣ הצעה"

User replies: "1" or "2" or "3" or "אני רוצה יותר תוכן על קייט"

       ┌──────────────┐
       │  Parse reply  │
       └──────┬───────┘
              │
       ┌──────▼───────┐     ┌───────────────────────┐
       │  Numeric?     │──Y──│ Save rating to DB      │
       │  (1/2/3/4)   │     │ Update source scores   │
       └──────┬───────┘     └───────────────────────┘
              │N
       ┌──────▼───────┐     ┌───────────────────────┐
       │  Free text    │────│ Claude analyzes intent  │
       │              │     │ → adjust interests      │
       └──────────────┘     │ → add/boost subtopics   │
                            └───────────────────────┘
```

### לולאת למידה

```
Feedback accumulates → weekly analysis:

  avg_rating < 2.5 for 3 days → alert: "content not landing"
  topic X clicked 80% of time → boost topic X priority
  source Y never clicked → lower source Y trust score
  free text "יותר קייט" → boost kite subtopics weight
  member hasn't opened in 3 days → send "we miss you" + adjust
```

---

## 4. שמירת מידע - הארכיון כנכס

### הנקודה המרכזית שהעלית:

> אחרי תקופה, התוכן שנאסף הופך למקור מידע ואפיון בפני עצמו.

זה בדיוק נכון. אחרי חודש ריצה יש לנו:
- 450+ פריטי תוכן שנאספו (15/יום × 30)
- 150+ סיכומים שנוצרו
- 30 ניוזלטרים שלמים
- ~150 נקודות משוב
- פרופיל העדפות שהשתכלל 30 פעם

אחרי שנה:
- 5,400+ פריטים
- מגמות עניין לאורך זמן
- "מה עניין את המשפחה בחורף vs קיץ"
- "איזה נושאים חדשים צצו"
- הארכיון הופך ל-**זיכרון משפחתי**

### סכמת מסד נתונים

```sql
-- כל פריט תוכן שנאסף אי פעם
CREATE TABLE content_archive (
    id TEXT PRIMARY KEY,           -- hash of URL
    url TEXT NOT NULL,
    title TEXT,
    source_name TEXT,
    source_type TEXT,              -- rss, website, youtube, family
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT NOW,
    language TEXT,                  -- he, en
    raw_summary TEXT,              -- original summary from source
    generated_summary_he TEXT,     -- our Hebrew summary
    generated_summary_en TEXT,     -- our English summary
    generated_headline TEXT,
    tags TEXT,                     -- JSON array
    image_url TEXT,
    full_text TEXT,                -- optional: full article text
    embedding BLOB                 -- vector embedding for similarity
);

-- כל ניוזלטר שנוצר
CREATE TABLE newsletters (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,     -- YYYY-MM-DD
    html_content TEXT,
    url TEXT,
    greeting TEXT,
    trivia TEXT,
    created_at TIMESTAMP DEFAULT NOW
);

-- איזה תוכן הופיע באיזה ניוזלטר, לאיזה בן משפחה
CREATE TABLE newsletter_items (
    newsletter_date TEXT,
    content_id TEXT,
    member_id TEXT,
    section TEXT,                  -- personal, discovery, family, trivia
    relevance_score REAL,
    position INTEGER,              -- order in newsletter
    was_clicked BOOLEAN DEFAULT 0,
    click_timestamp TIMESTAMP,
    FOREIGN KEY (content_id) REFERENCES content_archive(id)
);

-- משוב
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY,
    member_id TEXT NOT NULL,
    date TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW,
    type TEXT,                     -- rating, text, click, time_on_page
    value TEXT,                    -- "1"-"4", free text, URL clicked, seconds
    processed BOOLEAN DEFAULT 0,
    action_taken TEXT              -- what adjustment was made
);

-- פרופיל העדפות (מתעדכן עם הזמן)
CREATE TABLE member_preferences_log (
    member_id TEXT,
    date TEXT,
    preferences_snapshot TEXT,     -- JSON: full preferences at this point
    changes_made TEXT,             -- JSON: what changed and why
    trigger TEXT                   -- feedback, manual, weekly_analysis
);

-- תוכן שבני המשפחה שיתפו
CREATE TABLE family_content (
    id INTEGER PRIMARY KEY,
    member_id TEXT NOT NULL,
    received_at TIMESTAMP DEFAULT NOW,
    type TEXT,                     -- photo, link, text
    content TEXT,                  -- URL, text, or file path
    caption TEXT,
    used_in_newsletter TEXT,       -- newsletter date, or NULL
    media_url TEXT                 -- if photo/video
);
```

### פורמט שמירה

```
data/
├── famely.db                    ← SQLite: all structured data
├── archive/
│   ├── raw/
│   │   └── 2026-04-08.json      ← raw fetched items per day
│   ├── newsletters/
│   │   └── 2026-04-08.html      ← rendered newsletters
│   └── feedback/
│       └── 2026-04-08.json      ← daily feedback
├── embeddings/
│   └── content_vectors.npy      ← for similarity search
└── exports/
    └── monthly-report-2026-04.md ← monthly family digest
```

### שימושים עתידיים לארכיון

| שימוש | מתי | איך |
|-------|------|------|
| **Dedup חכם** | יומי | "כבר כתבנו על זה לפני שבוע" |
| **טרנד detection** | שבועי | "נימרוד קורא יותר על קייט מאז מרץ" |
| **סיכום שנתי** | שנתי | "2026 wrap-up: מה עניין את המשפחה" |
| **המלצות חכמות** | יומי | "Based on 3 months of data, Tzlil might like..." |
| **זיכרון משפחתי** | כל עת | "מה קרה אצלנו ב-8 באפריל שנה שעברה?" |
| **אופטימיזציית מקורות** | חודשי | "Yachting World gets 3x more clicks than SurferToday" |
| **Fine-tuning prompts** | חודשי | "Summaries that got 😍 vs 👎 - improve prompt" |

---

## 5. POC v1.0 - מה בונים עכשיו

```
Scope: End-to-end flow that WORKS, with real data

IN:   RSS feeds → real articles from today
OUT:  HTML file you can open in browser + SQLite archive

Flow: python poc.py → fetches → scores → curates → 
      calls Claude → renders HTML → saves to DB → done

What's real:
  ✅ Real RSS feeds (Yachting World, ArchDaily, etc.)
  ✅ Real scoring against family profiles
  ✅ Real Claude API summaries
  ✅ Real HTML from the approved template
  ✅ Real SQLite archive
  ✅ Math puzzle generated for Tzlil
  ✅ Shaked's section in English

What's mocked:
  🔲 WhatsApp send (prints message to console)
  🔲 Upload to server (saves locally)
  🔲 Feedback (no collection yet)
  🔲 Family-uploaded content (hardcoded sample)
```
