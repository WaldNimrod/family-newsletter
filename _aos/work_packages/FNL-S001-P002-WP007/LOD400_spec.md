---
lod_target: LOD400
lod_status: DRAFT
track: A
authoring_team: team_100 (familynewsletter_arch)
consuming_team: familynewsletter_build
date: 2026-07-22
version: v1.0.0
supersedes: null
---

# Template Extension — Missing Sections, Personal Corners, Dark Mode & Design-Fish — LOD400 Implementation Spec

**work_package_id:** FNL-S001-P002-WP007
**parent_lod200:** _aos/work_packages/FNL-S001-P001-WP001/LOD200.md
**parent_lod300:** N/A — Track A only
**approved_by:** [PENDING — familynewsletter_build sign-off at L-GATE_SPEC]
**approved_at:** [PENDING]

## 1. Scope reminder

This WP **extends the existing** `templates/newsletter.html.j2` (842 lines today) and its renderer glue — it does not replace the file or its comic visual identity. Today's template renders 8 of LOD200 §2's 13 mandatory sections and is missing: **Viewing** (🍿 מה רואים השבוע), **Family-Table** (🍽️ שולחן שישי — and it silently drops the already-built `neo.family_content` field), and **Extended-Family** (👨‍👩‍👧 מהמשפחה המורחבת). It also pools all members' content into one shared HERO/FEATURE/COMPACT grid rather than the 5 named "פינה אישית" (Personal Corner) blocks LOD200 §2 item 5 restores. This WP:

1. Restructures the pooled grid into **5 sequential Personal Corner blocks** (§2.2) — the single biggest change in this spec.
2. Adds the 3 missing sections (§2.3–§2.4, §2.6), plus a bonus 14th section **"מהמדף שלנו" / From Our Shelf** (§2.5) that DESIGN_FISH assigns to this WP but that is not one of LOD200's 13.
3. Wires the already-built-but-unused `character_html()` helper (`src/m4_renderer.py`) into 5 mascot slots across the page (§2.2, §2.7), replacing the static dashed "character placeholder" and bare emoji spans.
4. Adds a static illustrated SVG hero backdrop (sea/sky/boat/kite/fish, ported from `archive/design-april-2026/svg-hero-prototype.html`) as the new no-image fallback for each corner's lead card (§2.2).
5. Adds dark mode (§2.8), the inline one-tap emoji rating + missing "עורכת" editor credit in the footer (§2.9), and points `og:image` at the WP005 teaser (§2.10).

**Files this WP touches:** `templates/newsletter.html.j2` (primary), `src/m4_renderer.py` (renderer glue — new `settings` param, `og_image_url` computation), `src/models.py` (4 new `GeneratedContent` fields). Two additional **companion edits** are specified because without them the new fields/params are dead code: one line in `src/orchestrator.py` (threads `settings` into the `render()` call already in scope there) and one small dict addition in `src/m3_normalizer.py` (threads the 4 new `GeneratedContent` fields into `neo.metadata`, mirroring the existing `opener_text`/`closer_text`/`weather` pattern already there verbatim). Both companion edits are 1–4 lines, mechanical, and called out explicitly in §2.1 and §3 — this WP does **not** otherwise touch `m3_normalizer.py` or `orchestrator.py`.

**Baseline preserved byte-for-byte where not explicitly changed.** DESIGN_FISH_2026-07-22.md §4 confirms `archive/design-april-2026/newsletter-v3-preview.html`'s `<style>` block is byte-identical to today's template — this spec is a **diff against that exact baseline**, not a rewrite. Every existing CSS class not named in §2 below (fonts, colors, halftone background, border/shadow mechanics, `togglePanel()`/`toggleWeather()` JS, Cover/Opener/Family-Strip/Weather/Puzzle/History/Survey/Closer markup) is unchanged.

### Assumptions (where the brief was silent, or where this WP had to make a scoping call — flag these at L-GATE_VALIDATE if wrong)

1. **Personal Corners ×5 fully replace the pooled HERO/FEATURE/COMPACT grid** (§2.2) rather than adding per-member corners alongside/on top of it. Decided from LOD200 §2 item 5's explicit "פינה אישית ×5" naming — "HERO"/"FEATURE"/"COMPACT" do not appear anywhere in LOD200's 13-item list — over STYLE_GUIDE §3's older, weaker "≥1 item across L1+L2 combined" rule, which the pooled grid already satisfied without literal corners. Accepted consequence: the page is longer (5 hero-style cards instead of 1) — a deliberate trade-off, not a defect (LOD200 §1: "completeness over speed... accepted"). Full rationale in §2.2.
2. **YouTube-source detection (§2.1 point 7, used throughout §2.2) uses URL pattern matching** (`youtube.com`/`youtu.be` substring in `item.url`), not `NCI.source_type` — verified that `m3_normalizer.py`'s per-item dict construction does not currently copy `source_type` into the dicts the template sees, and editing that file's item-shaping logic is out of this WP's file scope (§6).
3. **The "SVG hero + monthly-rotating character slots" fish is built as static rendering infrastructure only.** One fixed, topic-agnostic decorative SVG scene (sea/sky/boat/kite/fish) is reused identically across all 5 corners and all editions; the 4 existing `POSE_EMOJI_MAP` poses are wired into 5 template slots via the already-built (previously unused) `character_html()` helper. Per-topic bespoke scene selection (`SVG_MODULE_SPEC.md` §4's topic→scene→character lookup table, §5's "SVG Generator Agent") is treated as a future AI-generation/content-selection concern (teaser.py/WP005's territory, or a future researcher/editor enhancement) — not rebuilt here. See §6.
4. **The inline one-tap emoji rating (§2.9) is wired to real `wa.me` deep links**, reusing the Survey section's existing `whatsapp_number`/`whatsapp_group_link` metadata keys — not the archived prototypes' dead `href="#"` placeholders. A static, FTP-uploaded page has no endpoint to receive a bare anchor click, and LOD200 §7 explicitly defers real reply-ingestion/per-item feedback to Phase B; shipping 4 non-functional buttons was rejected as worse than reusing an existing, working mechanism.
5. **`og:image` is a pure addition, not a modification** — the current template has zero `og:`/`twitter:` meta tags today (verified), so there is no existing line to "point" at the teaser; §2.10 adds the block fresh. Its URL is derived via the exact same `env_compat.newsletter_url_base()` helper `m5_distributor.ftp_upload()` already uses for `index.html`'s own public URL, so the teaser is guaranteed to resolve into the same dated directory once WP005 (image) and WP006 (FTP publish) ship — no second, hand-rolled copy of the URL scheme.
6. **4 new `NEO.metadata` contract fields are defined and rendered (`viewing`, `family_table_text`, `extended_family`, `shelf_pick`), but no WP is currently chartered to populate any of them.** Cross-checked against sibling spec **FNL-S001-P002-WP004** (`editor.py`), whose own §3 mapping table explicitly places Viewing/Family-Table/Extended-Family outside its scope (its line-296 note: *"a separate section this module does not touch"*). Every corresponding section is `{% if %}`-guarded to render nothing (not an error) until that future content-generation work lands — see §2.1 point 1's coordination note and §6.
7. **LOD200 §2 item 13's literal "עורכת: צליל" editor-credit text was missing from the footer entirely** (not merely unstyled — confirmed absent by string search). Added in §2.9 as a small, in-scope fix since footer work was already in this WP's scope, and WP004 independently names the general area a WP007 concern. WP004's own richer `editors_choice` per-item highlight/badge concept is explicitly **not** built here (§6) — only the plain-text credit line LOD200 §13 literally asks for.
8. **Dark mode requires one new CSS token, `--shadow-color`, decoupled from `--ink`** (§2.8) — `--ink` today serves triple duty as text color, border color, and every zero-blur comic shadow's color. Flipping `--ink` alone to a light tone for dark-mode text/border legibility would also flip every shadow to a light color, which reads as "no shadow" rather than depth. `--shadow-color` defaults to `var(--ink)` in light mode (byte-identical output to today) and is pinned to a fixed dark value only under `prefers-color-scheme: dark`.

## 2. Technical specification

### 2.1 Shared foundation — renderer, data-model, and context changes (read this subsection first)

Every other subsection in §2 depends on the fields and conventions defined here.

**What to implement:**

1. **`src/models.py` — 4 new fields on `GeneratedContent`.** Locate the dataclass by name (`@dataclass\nclass GeneratedContent:`); its last field today is `weather: list = field(default_factory=list)`. Append exactly these 4 lines immediately after it (order matters only for readability — all 4 have defaults, so field ordering is dataclass-legal regardless of position, but keep them last since every other field in this dataclass is currently populated by `m3_normalizer.py`'s existing `_generate_*` functions and these 4 are not yet populated by anything):

```python
    viewing: dict = field(default_factory=dict)  # {family_pick: {...}, personal_pick: {...}} — see WP007 LOD400 §2.3
    family_table_text: str = ""  # שולחן שישי — conversation-starter + open question (Style A), rendered with |safe like opener_text/closer_text
    extended_family: list = field(default_factory=list)  # [{name, relation, headline, pointer_text, link_url}] — public-only, NEVER an image field — see §2.6
    shelf_pick: dict = field(default_factory=dict)  # {title_he, title_en, author, category, member_id, blurb} — shape mirrors config/family.json shared_interests.bookshelf.books[]
```

   **Coordination note (not a code change, informational):** sibling spec **FNL-S001-P002-WP004** (`editor.py`) explicitly declines to edit `models.py` (its own §1 Assumption 6) and documents a *non-binding* mapping of its own output fields (`opener`, `closer`, `puzzle.*`, `today_in_history.*`, `question_of_the_week.*`, `discovery_bridges`, `teaser_caption`, `editors_choice`) onto `GeneratedContent`/`NEO`. None of WP004's field names collide with the 4 added here — WP004's own §3 table confirms Viewing/Family-Table/Extended-Family/Shelf are outside its scope (its line-296 note: *"Extended family is out of scope for `discovery_bridges`... a separate section this module does not touch"*). **This WP's task brief explicitly directs adding fields to `models.py`** (unlike WP004, which made an independent, brief-absent judgment call to avoid it) — the two specs are not in conflict, just differently chartered. **Open gap, flagged not resolved:** as of this spec, no WP is chartered to actually *populate* `viewing`/`family_table_text`/`extended_family`/`shelf_pick` (that is future `researcher.py`/`editor.py` work) — until it lands, these 4 fields stay at their dataclass defaults (`{}`/`""`/`[]`/`{}`), `m3_normalizer.py` threads those defaults into `neo.metadata` unchanged, and every `{% if %}`-guarded section this WP adds for them (§2.3–§2.6) simply does not render — no error, no empty section, by construction (verified in §2.3–§2.6's ACs).

2. **`src/m4_renderer.py` — imports.** Add `Settings` to the existing `from .models import NEO` import (→ `from .models import NEO, Settings`), and add a new import line `from .env_compat import newsletter_url_base`.

3. **`src/m4_renderer.py` — `render()` signature.** Change:

```python
def render(neo: NEO, template_path: str = "templates/",
           db: Database = None) -> str:
```

   to:

```python
def render(neo: NEO, template_path: str = "templates/",
           db: Database = None, settings: Settings = None) -> str:
```

4. **`src/m4_renderer.py` — `og_image_url` computation.** Inside `render()`, after the existing `character_meta = CHARACTER_SCHEDULE.get(...)` block and before the `html = template.render(...)` call, insert:

```python
    # og:image — points at the WP005 teaser.png, uploaded by WP006 to the
    # same dated FTP directory as index.html (REVIVAL_PLAN §3: "index.html +
    # teaser.png — the proven path"). Mirrors m5_distributor.ftp_upload()'s
    # own public_url construction exactly via the same env_compat helper, so
    # this module carries no second, hand-rolled copy of the URL scheme.
    # None whenever settings is not supplied (e.g. ad-hoc/test renders) —
    # the template omits the og:image tags entirely in that case (§2.10).
    og_image_url = None
    if settings is not None:
        try:
            og_image_url = f"{newsletter_url_base(settings)}/{neo.date}/teaser.png"
        except Exception as e:
            logger.warning(f"[M4] Could not compute og_image_url: {e}")
```

   Then add `og_image_url=og_image_url,` as a new kwarg to the existing `template.render(neo=neo, edition_number=edition_number, ...)` call.

5. **Companion edit — `src/orchestrator.py`, one line.** `settings` is already loaded and in scope at the existing `render()` call site (`cmd_weekly_build`, confirmed at the line immediately calling `render`). Change:

```python
    html = render(neo, template_path="templates/", db=db)
```

   to:

```python
    html = render(neo, template_path="templates/", db=db, settings=settings)
```

6. **Companion edit — `src/m3_normalizer.py`, `_build_neo()`'s `metadata={...}` dict.** Locate the dict literal ending `'weather': generated.weather,`. Add 4 lines immediately after it, mirroring the existing pattern exactly:

```python
            'viewing': generated.viewing,
            'family_table_text': generated.family_table_text,
            'extended_family': generated.extended_family,
            'shelf_pick': generated.shelf_pick,
```

7. **Shared Jinja convention — YouTube-source detection (used in §2.2).** Wherever this spec says "apply the YouTube thumbnail treatment," it means this exact, self-contained expression (no new NEO/context field — pure URL pattern match, robust to `url` being `None`/missing):

```jinja
{% set is_youtube = 'youtube.com' in (item.url or '') or 'youtu.be' in (item.url or '') %}
```

   **Why URL matching, not `source_type`:** `NCI.source_type` (`db.py`/`m2_scanner.py`) already distinguishes `'youtube'`, but the dict-construction code in `m3_normalizer.py` (`_build_neo`'s `section_items.append({...})`) does **not** currently copy `source_type` into the per-item dicts the template sees (verified: the dict there has `nci_id, title, summary, url, source_name, category, score, language, published_at, image_url` — no `source_type`). Adding it would require editing `m3_normalizer.py`'s item-shaping logic — out of this WP's file scope (§6). URL-pattern matching is self-contained inside the template and needs no upstream change.

8. **Shared Jinja convention — member tint backgrounds become CSS-variable references (needed for dark mode, §2.8).** Locate the existing line (currently near the top of the `<body>`, immediately after the opening `<div class="page">`):

```jinja
{% set member_bg = {'nimrod': '#e6f0fa', 'michal': '#e6f5ed', 'shaked': '#ece6f5', 'maayan': '#fce8ec', 'tzlil': '#fef3e2'} %}
```

   Replace with:

```jinja
{% set member_bg = {'nimrod': 'var(--nimrod-bg)', 'michal': 'var(--michal-bg)', 'shaked': 'var(--shaked-bg)', 'maayan': 'var(--maayan-bg)', 'tzlil': 'var(--tzlil-bg)'} %}
```

   `--nimrod-bg` etc. are new CSS custom properties defined in §2.8, with **light-mode values identical to the literal hex codes above** — this line change alone causes **zero visual difference in light mode** (a CSS variable that resolves to the same hex it replaced renders identically); it only enables dark mode (§2.8) to override those 5 properties. `member_bg` is consumed by 3 existing/new inline-`style` sites (Family Strip chip, and — after §2.2 — the corner hero/feature fallback backgrounds); all 3 automatically become theme-aware for free once this one dict changes, with no further edits needed at any of those 3 call sites.

**Acceptance criteria:**
- [ ] AC-01: `GeneratedContent` has exactly 4 new fields — `viewing: dict`, `family_table_text: str`, `extended_family: list`, `shelf_pick: dict` — each with the exact default shown; `GeneratedContent()` (no args) does not raise (all fields have defaults, matching the existing dataclass's all-defaults-after-`history` convention).
- [ ] AC-02: `render(neo)` (no `settings` arg, matching every pre-existing call site) does not raise; `og_image_url` is `None`; the rendered HTML contains no `<meta property="og:image"` tag (verified in §2.10).
- [ ] AC-03: `render(neo, settings=some_settings)` where `some_settings.newsletter`/env vars resolve successfully produces `og_image_url == f"{newsletter_url_base(some_settings)}/{neo.date}/teaser.png"` exactly — byte-identical to what `m5_distributor.ftp_upload()` would construct as the sibling `index.html`'s directory, with `teaser.png` as the filename.
- [ ] AC-04: If `newsletter_url_base(settings)` raises (e.g. malformed `settings` object), `render()` does not propagate the exception — `og_image_url` stays `None`, a `logger.warning` is emitted, and the rest of the render proceeds normally.
- [ ] AC-05: `git diff` for `src/orchestrator.py` touches exactly the one line in §2.1 point 5 — no other line changes.
- [ ] AC-06: `git diff` for `src/m3_normalizer.py` touches exactly the 4 added lines in §2.1 point 6, inserted after the existing `'weather': generated.weather,` line — no other line changes, no reordering of existing keys.
- [ ] AC-07: A rendered edition where every one of `neo.metadata['viewing']`, `['family_table_text']`, `['extended_family']`, `['shelf_pick']` is absent from the dict entirely (simulating a `neo.to_json()`/archived-edition fixture predating this WP) does not raise `jinja2.exceptions.UndefinedError` — every read in §2.3–§2.6 goes through `.get(key, default)`, never bare subscript access on `neo.metadata`.
- [ ] AC-08: `{% set is_youtube = ... %}` evaluates to `False` (not an exception) when `item.url` is `None` or the key is absent from the item dict.
- [ ] AC-09: The 3 existing inline-style call sites that read `member_bg` (Family Strip chip; and — post-§2.2 — the two corner fallback-background sites) render `style="background:var(--nimrod-bg)"` (or the matching member) literally in the output HTML — i.e. the **string** `var(--nimrod-bg)` appears in the HTML, not a pre-resolved hex value (CSS variables resolve in the browser, not in Jinja).
- [ ] AC-10: A byte-diff of the rendered HTML's `<body>` between this WP's build and today's baseline, **restricted to the Family Strip chip's `style` attribute**, shows only the value change from a literal hex to a `var(--...)` reference — no other attribute or surrounding markup in that one element changes.

### 2.2 Personal Corners ×5 — replaces the pooled HERO/FEATURE/COMPACT grid

**This is the centerpiece decision of this WP.** LOD200 §2 item 5 names this section **"פינה אישית ×5"** (Personal Corner ×5) — "one per member... every member ≥1 item (hard rule)" — as its own numbered section, distinct from and not naming "HERO/FEATURE/COMPACT" anywhere in its 13-item list. The task brief for this WP is explicit that April's prototype had literal per-member corners, v2 pooled them into today's cross-member tiered grid, and **LOD200 restores per-member**. Decision (with rationale, since the brief asks this WP to make and justify the call):

**Decision: replace the cross-member pooled grid with 5 sequential per-member corner blocks, one per `neo.member_sections` entry, in the order the pipeline already provides them** (`m3_normalizer.py`'s `member_order = ["nimrod", "michal", "shaked", "maayan", "tzlil"]` — confirmed the literal order `member_sections` is built in; this template never re-sorts it, matching how the existing Family Strip already renders `neo.member_sections` in given order — corners and chips will visually match). **Within each corner**, that member's own items reuse the exact same tier logic and CSS classes as today's global grid, just re-scoped to one member: item `[0]` gets `.panel-level1` (hero) treatment, `[1:]` get `.panel-level2` (feature) treatment, paired 2-per-row with a single wide panel for a leftover odd item (this subsumes DESIGN_FISH's "single wide L2" fish — see the `panel-level2-solo` logic below). **There is no compact (`.panel-level3`) tier inside a corner** — corners are kept to hero + feature only, deliberately simpler than the old global 3-tier grid, since a corner already IS the member-diversity guarantee that today's `.panel-level3`/`min_l2` machinery existed to force; removing that machinery is a net simplification (the ~30-line `ns.l2_count`/`min_l2`/force-even pre-computation block is deleted entirely, replaced by one Jinja loop-index test).

**Rejected alternative — "the existing magazine grid already satisfies it":** STYLE_GUIDE §3's weaker rule ("every member ≥1 item somewhere across L1+L2 combined") is technically satisfied by today's grid, but LOD200 (later, team_00-approved, more specific) explicitly reframes this as 5 named corners, not a pooled/tagged grid — a member-tag chip on a shared tile is not "a corner." Keeping the pooled grid **and** adding literal corners on top (the other rejected alternative) would duplicate every item's content twice on the page — rejected as bloat.

**Accepted consequence:** the page is longer than today (5 hero-style cards instead of 1). This is a deliberate, LOD200-mandated trade-off (LOD200 §1: "**FULL section set**, completeness over speed — ~10-day timeline accepted" — team_00's own words), not a defect.

**What to implement:**

1. **Delete** the entire existing block from the `<!-- ============================== -->` / `<!-- LEVEL 1: HERO -->` comment through the closing `{% endif %}` of the `<!-- LEVEL 3: COMPACT -->` block — i.e. everything currently between the `<div class="grid">` opening tag and the `<!-- ===== DISCOVERY ===== -->` comment. This is the `{% set ns = namespace(all_items=[], l2_count=0) %}` flatten-loop, the HERO panel, the FEATURE row-pairing/member-diversity computation, the FEATURE panel loop, and the COMPACT panel loop — all of it, replaced by the block below. Discovery's own markup (immediately after) is untouched and now simply follows the corners instead of following the old COMPACT loop.

2. **Insert** in its place:

```jinja
  {% for section in neo.member_sections %}
  {% set corner_items = section['items'] %}
  {% if corner_items %}
  {% set corner_lang_cls = ' ltr' if section.language == 'en' else '' %}
  <div class="section-sep">{{ member_emoji.get(section.member_id, '📰') }} {{ member_names.get(section.member_id, section.member_id) }} {{ member_emoji.get(section.member_id, '📰') }}</div>

  <div class="member-corner{{ corner_lang_cls }}">
    <div class="corner-header" style="border-color:{{ member_colors.get(section.member_id, 'var(--ink)') }};">
      <div class="corner-icon" style="background:{{ member_colors.get(section.member_id, '#888') }};">{{ member_emoji.get(section.member_id, '📰') }}</div>
      <h2>{% if section.language == 'en' %}{{ section.member_name_en }}&#39;s Corner{% else %}הפינה של {{ member_names.get(section.member_id, section.member_id) }}{% endif %}</h2>
    </div>

    {% set corner_hero = corner_items[0] %}
    {% set corner_rest = corner_items[1:] %}
    {% set hero_is_yt = 'youtube.com' in (corner_hero.url or '') or 'youtu.be' in (corner_hero.url or '') %}

    <div class="panel-level1{% if corner_hero.language == 'en' %} ltr{% endif %}" onclick="togglePanel(this)">
      <div class="hero-visual{% if hero_is_yt and corner_hero.image_url %} yt-thumb{% endif %}"{% if not corner_hero.image_url %} style="background: linear-gradient(135deg, {{ member_bg.get(section.member_id, '#e8f4fd') }}, #d6eaf8);"{% endif %}>
        {% if corner_hero.image_url %}
        <img src="{{ corner_hero.image_url }}" alt="{{ corner_hero.title }}" loading="lazy">
        {% if hero_is_yt %}<span class="yt-play"></span>{% endif %}
        {% else %}
        <svg class="hero-scene" viewBox="0 0 640 380" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="corner-dots-{{ section.member_id }}" width="8" height="8" patternUnits="userSpaceOnUse">
              <circle cx="4" cy="4" r="1" fill="rgba(0,0,0,0.06)"/>
            </pattern>
            <linearGradient id="corner-sky-{{ section.member_id }}" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#87CEEB"/>
              <stop offset="60%" stop-color="#E0F0FF"/>
              <stop offset="100%" stop-color="#F5E6D3"/>
            </linearGradient>
            <linearGradient id="corner-sea-{{ section.member_id }}" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#2471a3"/>
              <stop offset="100%" stop-color="#1a5276"/>
            </linearGradient>
          </defs>
          <rect width="640" height="380" fill="url(#corner-sky-{{ section.member_id }})"/>
          <rect width="640" height="380" fill="url(#corner-dots-{{ section.member_id }})"/>
          <g opacity="0.7">
            <ellipse cx="120" cy="60" rx="50" ry="22" fill="white"/>
            <ellipse cx="95" cy="55" rx="30" ry="18" fill="white"/>
            <ellipse cx="145" cy="55" rx="35" ry="20" fill="white"/>
            <ellipse cx="450" cy="80" rx="40" ry="18" fill="white"/>
            <ellipse cx="425" cy="75" rx="25" ry="14" fill="white"/>
            <ellipse cx="475" cy="75" rx="30" ry="16" fill="white"/>
          </g>
          <circle cx="560" cy="70" r="35" fill="#f39c12" opacity="0.9"/>
          <circle cx="560" cy="70" r="28" fill="#f9e79f"/>
          <path d="M0 240 Q80 225 160 240 Q240 255 320 240 Q400 225 480 240 Q560 255 640 240 L640 380 L0 380 Z" fill="url(#corner-sea-{{ section.member_id }})"/>
          <path d="M0 260 Q80 250 160 260 Q240 270 320 260 Q400 250 480 260 Q560 270 640 260" fill="none" stroke="rgba(255,255,255,0.3)" stroke-width="2"/>
          <path d="M0 280 Q80 272 160 280 Q240 288 320 280 Q400 272 480 280 Q560 288 640 280" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1.5"/>
          <g transform="translate(480, 210)">
            <path d="M0 0 L-8 30 L8 30 Z" fill="white" stroke="#2c2c2c" stroke-width="1"/>
            <line x1="0" y1="0" x2="0" y2="30" stroke="#2c2c2c" stroke-width="1.5"/>
            <path d="M-12 30 Q0 28 12 30" fill="#5a3a1a" stroke="#2c2c2c" stroke-width="1"/>
          </g>
          <g transform="translate(350, 140)">
            <path d="M0 -20 L15 0 L0 20 L-15 0 Z" fill="#e74c3c" stroke="#2c2c2c" stroke-width="1.5" opacity="0.8"/>
            <path d="M0 20 Q10 35 5 50 Q0 65 -5 80" fill="none" stroke="#2c2c2c" stroke-width="1" opacity="0.5"/>
          </g>
          <g transform="translate(400, 250)">
            <path d="M0 0 Q5 -15 15 -12 Q25 -10 20 0" fill="#87CEEB" stroke="#2c2c2c" stroke-width="1.5"/>
            <circle cx="18" cy="-8" r="1.5" fill="#2c2c2c"/>
            <path d="M-5 2 Q0 -5 5 2" fill="none" stroke="white" stroke-width="1" opacity="0.6"/>
          </g>
        </svg>
        {% endif %}
        <div class="source-badge">{{ corner_hero.source_name }}</div>
        <div class="level-badge">HERO</div>
        <div class="hero-character-slot">{{ character_html('hero-greeting', current_month) | safe }}</div>
      </div>
      <div class="hero-body">
        <div class="category" style="color: {{ member_colors.get(section.member_id, 'var(--ink)') }};">{{ corner_hero.category }}</div>
        <h3><a href="{{ corner_hero.url }}">{{ corner_hero.title }}</a></h3>
        <div class="excerpt">{{ corner_hero.summary }}</div>
        <div class="hero-meta">
          {{ corner_hero.source_name }} &bull; {{ neo.date }} &bull; <span style="background:#eee;padding:1px 6px;border-radius:4px;font-size:10px;">{{ corner_hero.language|upper }}</span>
        </div>
      </div>
      <div class="expand-hint">לחצו לפרטים</div>
      <div class="panel-detail">
        <p>{{ corner_hero.get('full_text', corner_hero.summary) }}</p>
        <a href="{{ corner_hero.url }}" class="read-more">{% if corner_hero.language == 'en' %}Read more &rarr;{% else %}למאמר המלא &larr;{% endif %}</a>
      </div>
    </div>

    {% if corner_rest %}
    {% for item in corner_rest %}
      {% set item_is_yt = 'youtube.com' in (item.url or '') or 'youtu.be' in (item.url or '') %}
      {% if loop.index is odd %}
    <div class="level2-row">
      {% endif %}
      <div class="panel-level2{% if item.language == 'en' %} ltr{% endif %}{% if loop.index == loop.length and loop.index is odd %} panel-level2-solo{% endif %}" onclick="togglePanel(this)">
        {% if item.image_url %}
        <div class="feat-visual{% if item_is_yt %} yt-thumb{% endif %}">
          <img src="{{ item.image_url }}" alt="{{ item.title }}" loading="lazy">
          {% if item_is_yt %}<span class="yt-play"></span>{% endif %}
        </div>
        {% else %}
        <div class="feat-visual-fallback" style="background-color: {{ member_bg.get(section.member_id, '#f0f0f0') }};">
          <span class="fallback-emoji">{{ member_emoji.get(section.member_id, '📰') }}</span>
        </div>
        {% endif %}
        <div class="feat-body">
          <div class="category" style="color:{{ member_colors.get(section.member_id, 'var(--ink)') }};">{{ item.category }}</div>
          <h3><a href="{{ item.url }}">{{ item.title }}</a></h3>
          <div class="feat-excerpt">{{ item.summary }}</div>
        </div>
        <div class="expand-hint">{% if item.language == 'en' %}tap for more{% else %}לחצו לפרטים{% endif %}</div>
        <div class="panel-detail">
          <p>{{ item.get('full_text', item.summary) }}</p>
          <a href="{{ item.url }}" class="read-more">{% if item.language == 'en' %}Read more &rarr;{% else %}למאמר &larr;{% endif %}</a>
        </div>
      </div>
      {% if loop.index is even or loop.last %}
    </div>
      {% endif %}
    {% endfor %}
    {% endif %}
  </div>
  {% endif %}
  {% endfor %}
```

   **Note on the `member-tag` chip:** deliberately **omitted** from every corner card (hero and feature alike) — the corner header already establishes member identity for the whole block, and every card's `category` label is already member-color-tinted, so a repeated chip on each card would be redundant noise. This is the one visible difference from today's per-card treatment; it is intentional, not an oversight.

   **The single-wide-L2 fish, explained:** `loop.index == loop.length and loop.index is odd` is `True` exactly once per `corner_rest` list, if and only if that list has odd length — for the last item, when there is one. It replaces the deleted `ns.l2_count`/force-even block, which previously made this state *impossible* by construction (borrowing or returning an item to force an even count). No pre-computation is needed: the existing row-open/close logic (`loop.index is odd` opens a `.level2-row`, `loop.index is even or loop.last` closes it) already isolates a lone trailing item into a single-item row on its own — this spec only adds the `panel-level2-solo` class to that lone item so CSS can make it fill the row (see new CSS below).

3. **New CSS** — append to the existing `<style>` block (anywhere after the `.footer-strip` rules is fine; ordering within `<style>` does not affect the cascade here since no selector below conflicts in specificity with anything above):

```css
  /* ===== PERSONAL CORNERS ===== */
  .member-corner { display: flex; flex-direction: column; gap: 10px; margin-bottom: 4px; }
  .corner-header {
    display: flex; align-items: center; gap: 10px;
    background: var(--panel-bg);
    border: 3px solid var(--ink);
    border-radius: 12px;
    padding: 8px 14px;
    box-shadow: 3px 3px 0 var(--shadow-color);
  }
  .corner-icon {
    width: 40px; height: 40px; border-radius: 10px;
    border: 2px solid var(--ink);
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; color: #fff; flex-shrink: 0;
  }
  .corner-header h2 { font-family: 'Bangers', cursive; font-size: 19px; letter-spacing: 0.5px; }
  .panel-level2-solo { flex: 1; }

  /* ===== HERO SVG SCENE (no-image fallback backdrop) ===== */
  .hero-scene { width: 100%; height: 220px; display: block; border-bottom: 3px solid var(--ink); }
  .hero-character-slot { position: absolute; bottom: 10px; left: 10px; z-index: 2; }

  /* ===== CHARACTER SLOTS (character_html() output — PNG-or-emoji, §2.1/§2.7) ===== */
  .character-emoji, .character-img { display: inline-block; }
  .character-hero-greeting.character-emoji { font-size: 64px; filter: drop-shadow(2px 2px 0 rgba(0,0,0,0.25)); }
  .character-hero-greeting.character-img { width: 90px; height: 120px; object-fit: contain; }
  .character-thinking.character-emoji, .character-pointing.character-emoji, .character-reading.character-emoji { font-size: 26px; vertical-align: middle; }
  .character-thinking.character-img, .character-pointing.character-img, .character-reading.character-img { width: 34px; height: 34px; object-fit: contain; vertical-align: middle; }
  .character-goodbye.character-emoji { font-size: 40px; }
  .character-goodbye.character-img { width: 56px; height: 56px; object-fit: contain; }

  /* ===== YOUTUBE THUMBNAIL TREATMENT (ported verbatim from newsletter-preview-v1.0.1.html) ===== */
  .yt-thumb { position: relative; }
  .yt-thumb::after { content: ''; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 48px; height: 48px; background: rgba(255,0,0,0.85); border-radius: 12px; }
  .yt-play { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 0; height: 0; border-top: 12px solid transparent; border-bottom: 12px solid transparent; border-left: 20px solid white; z-index: 2; margin-left: 3px; }
```

**Acceptance criteria:**
- [ ] AC-11: The old `<!-- LEVEL 1: HERO -->` / `<!-- LEVEL 2: FEATURE -->` / `<!-- LEVEL 3: COMPACT -->` comments, the `ns.all_items`/`ns.l2_count`/`ns.unique_member_count`/`ns.min_l2` namespace variables, and the force-even correction block are **fully removed** from the template — `grep -c "ns\.l2_count" templates/newsletter.html.j2` returns `0`.
- [ ] AC-12: For a fixture `neo.member_sections` with all 5 members present, each having ≥1 item, the rendered HTML contains exactly 5 `class="member-corner"` blocks, in the order `nimrod, michal, shaked, maayan, tzlil` (i.e. `neo.member_sections`' given order, unmodified).
- [ ] AC-13: A member section with an empty `items` list is skipped entirely — no `.member-corner` div, no `.section-sep`, no empty corner-header — for that member (verified via the outer `{% if corner_items %}` guard).
- [ ] AC-14: Within a corner, item `[0]` always renders as `.panel-level1` (never `.panel-level2`/`.panel-level3`), regardless of how many total items the member has (including exactly 1).
- [ ] AC-15: A corner with `corner_rest` of length 1 renders that single item inside its own `.level2-row`, with class `panel-level2 panel-level2-solo` (both classes present, exact order not asserted).
- [ ] AC-16: A corner with `corner_rest` of length 2, 3, and 4 renders `panel-level2-solo` on **zero** items for lengths 2 and 4 (even), and on exactly the **last** item for length 3 (odd) — verified for all three lengths in one parametrized test.
- [ ] AC-17: A corner with `corner_rest` of length 0 (member has exactly 1 item total) renders no `.level2-row` and no `.panel-level2` at all — only the corner header and the single hero panel.
- [ ] AC-18: No `class="member-tag"` div appears anywhere inside a `.member-corner` block (hero or feature cards) — verified by scoping the assertion to `.member-corner .member-tag` (0 matches), while confirming `.member-tag` still exists elsewhere in the page (Family Strip is unaffected — out of scope for this AC, just confirming the omission is corner-local).
- [ ] AC-19: When `corner_hero.image_url` is falsy, the rendered hero-visual contains a `<svg class="hero-scene" viewBox="0 0 640 380" ...>` element with `<defs>` ids suffixed by the member's own `member_id` (e.g. `corner-sky-nimrod`) — confirms 5 corners on the same page never collide on SVG `<defs>` id uniqueness (a real HTML-validity bug if the suffix were omitted and 2+ corners fell back to the SVG scene on the same page).
- [ ] AC-20: When `corner_hero.image_url` is truthy, no `<svg class="hero-scene"...>` is rendered — the existing `<img>`-based path is used, unchanged from today's HERO markup (same `src`/`alt`/`loading="lazy"` attributes).
- [ ] AC-21: `{{ character_html('hero-greeting', current_month) | safe }}` is called with the `| safe` filter at every one of its 5 call sites across this WP (corner hero, puzzle, discovery, shelf, closer — §2.2 and §2.7) — grep for `character_html(` in the final template and confirm every match is immediately followed by `| safe`. **This is the single highest-risk line-item in this WP**: `m4_renderer.py`'s `Environment(..., autoescape=True)` means a bare `{{ character_html(...) }}` (no `| safe`) renders literal escaped `&lt;img...&gt;` text on the page instead of an image or emoji — a silent, highly visible content bug, not a crash, so it will not be caught by any exception-based test.
- [ ] AC-22: With no PNG assets present at `assets/characters/{current_month}/{pose}.png` (today's actual repo state — only `.gitkeep` files exist), every `character_html()` call renders the emoji-fallback `<span class="character-emoji character-{pose}">` branch, and each such span is visibly sized per the CSS in this subsection (i.e. `.character-hero-greeting.character-emoji` etc. match — not the base 1em browser default).
- [ ] AC-23: `is_youtube`/`item_is_yt`/`hero_is_yt` are each scoped with `{% set %}` **inside** their respective loop iteration (not hoisted outside the loop) — a test with a `corner_rest` list where item 1's URL is a YouTube URL and item 2's is not must show `.yt-thumb`/`.yt-play` on item 1's card only.
- [ ] AC-24: A YouTube-sourced item with `image_url` **absent** (fallback-gradient branch) does **not** get the `.yt-thumb`/`.yt-play` treatment (there is no image to overlay the play button on) — verified by the explicit `{% if hero_is_yt and corner_hero.image_url %}` / equivalent guard for the feature-card branch.

### 2.3 🍿 Viewing section (מה רואים השבוע)

Reads the new `neo.metadata['viewing']` contract (§2.1/§3): `{'family_pick': {...}, 'personal_pick': {...}}`, each an optional dict with keys `title, platform, hebrew_subs (bool), available_il (bool), note`. LOD200 §2 item 7: "1 family pick + 1 rotating personal pick" — singular personal pick (which member it belongs to rotates week-to-week upstream, in future editor.py content, not in this template).

**What to implement.** Insert immediately after the existing Discovery block's closing `{% endif %}` (i.e. right before the existing `<!-- ===== PUZZLE ===== -->` comment):

```jinja
  <!-- ===== VIEWING (מה רואים השבוע) ===== -->
  {% set viewing = neo.metadata.get('viewing', {}) %}
  {% if viewing.get('family_pick') or viewing.get('personal_pick') %}
  <div class="section-sep">🍿 מה רואים השבוע 🍿</div>

  <div class="panel-level3 viewing-panel">
    <div style="padding: 14px 16px;">
      {% if viewing.get('family_pick') %}
      {% set fp = viewing['family_pick'] %}
      <div class="viewing-pick">
        <div class="viewing-pick-label">👨‍👩‍👧‍👦 בחירת המשפחה</div>
        <h4 class="viewing-title">{{ fp.get('title', '') }}</h4>
        <div class="viewing-badges">
          {% if fp.get('platform') %}<span class="viewing-badge">{{ fp['platform'] }}</span>{% endif %}
          {% if fp.get('hebrew_subs') %}<span class="viewing-badge viewing-badge-ok">כתוביות עברית ✓</span>{% endif %}
          {% if fp.get('available_il') == false %}<span class="viewing-badge viewing-badge-warn">⚠️ בדקו זמינות בישראל</span>{% endif %}
        </div>
        {% if fp.get('note') %}<p class="viewing-note">{{ fp['note'] }}</p>{% endif %}
      </div>
      {% endif %}
      {% if viewing.get('personal_pick') %}
      {% set pp = viewing['personal_pick'] %}
      <div class="viewing-pick"{% if viewing.get('family_pick') %} style="border-top:2px dashed #eee; margin-top:10px; padding-top:10px;"{% endif %}>
        <div class="viewing-pick-label" style="color:{{ member_colors.get(pp.get('member_id'), 'var(--ink)') }};">{{ member_emoji.get(pp.get('member_id'), '🎬') }} הבחירה האישית של {{ member_names.get(pp.get('member_id'), '') }}</div>
        <h4 class="viewing-title">{{ pp.get('title', '') }}</h4>
        <div class="viewing-badges">
          {% if pp.get('platform') %}<span class="viewing-badge">{{ pp['platform'] }}</span>{% endif %}
          {% if pp.get('hebrew_subs') %}<span class="viewing-badge viewing-badge-ok">כתוביות עברית ✓</span>{% endif %}
          {% if pp.get('available_il') == false %}<span class="viewing-badge viewing-badge-warn">⚠️ בדקו זמינות בישראל</span>{% endif %}
        </div>
        {% if pp.get('note') %}<p class="viewing-note">{{ pp['note'] }}</p>{% endif %}
      </div>
      {% endif %}
    </div>
  </div>
  {% endif %}
```

**New CSS:**

```css
  /* ===== VIEWING ===== */
  .viewing-panel { background: #eaf6fb; border-color: var(--blue); }
  .viewing-pick-label { font-family: 'Bangers', cursive; font-size: 13px; letter-spacing: 0.5px; color: var(--blue); margin-bottom: 4px; }
  .viewing-title { font-family: 'Bangers', cursive; font-size: 17px; margin-bottom: 6px; }
  .viewing-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 4px; }
  .viewing-badge { font-size: 11px; font-family: sans-serif; padding: 2px 8px; border-radius: 10px; background: #eee; color: #666; }
  .viewing-badge-ok { background: #e6f5ed; color: var(--green); }
  .viewing-badge-warn { background: #fce8ec; color: var(--red); }
  .viewing-note { font-size: 13px; color: #666; margin-top: 4px; }
```

**Acceptance criteria:**
- [ ] AC-25: With `neo.metadata['viewing']` absent from the dict, the whole section (including `.section-sep`) does not render — `.viewing-panel` does not appear in the output.
- [ ] AC-26: With only `family_pick` present (`personal_pick` absent/falsy), only the family-pick block renders — no `border-top` dashed-divider styling is applied to it (that inline style is conditional on `family_pick` being present when rendering `personal_pick`, not the reverse).
- [ ] AC-27: `fp.get('available_il') == false` (Jinja2 lowercase literal) correctly matches a Python `False` value passed into the template context (not just a missing key) — verified with an explicit `available_il: False` fixture producing the `viewing-badge-warn` span, versus an `available_il` key entirely absent producing neither badge.
- [ ] AC-28: `hebrew_subs: True` and `available_il: True` together produce exactly one `viewing-badge-ok` span and zero `viewing-badge-warn` spans for that pick.
- [ ] AC-29: The section-sep and panel appear between Discovery and Puzzle in the rendered HTML's DOM order (string-index comparison: the offset of `viewing-panel` is greater than `discovery-panel`'s and less than `puzzle-panel`'s, when both are present).
- [ ] AC-30: A `title` containing HTML-significant characters (`<`, `&`) renders escaped (autoescape default, no `| safe` used anywhere in this block) — confirms this section does not accidentally introduce an XSS/markup-injection surface via unescaped user-ish content.

### 2.4 🍽️ Family Table section (שולחן שישי) — and rendering the already-built `neo.family_content`

`neo.family_content` (`src/models.py` `NEO.family_content: list[dict]`) has been built by `m3_normalizer.py`'s `_build_neo()` since before this WP (dict shape confirmed from that function: `submission_id, member_id, member_name, headline, summary, message_type, link_url, media_local_path`) but **no template code reads it today** — `grep -c "family_content" templates/newsletter.html.j2` returns `0` on the current file. This section renders it, plus the new `neo.metadata['family_table_text']` conversation-starter/open-question string (LOD200 §2 item 8: "one conversation-starter for everyone + an open question").

**What to implement.** Insert immediately after the Viewing block (§2.3):

```jinja
  <!-- ===== FAMILY TABLE (שולחן שישי) ===== -->
  {% set family_table_text = neo.metadata.get('family_table_text', '') %}
  {% if neo.family_content or family_table_text %}
  <div class="section-sep">🍽️ שולחן שישי 🍽️</div>

  <div class="panel-level3 family-table-panel">
    <div style="padding: 14px 16px;">
      {% if family_table_text %}
      <p class="family-table-prompt">{{ family_table_text | safe }}</p>
      {% endif %}
      {% if neo.family_content %}
      <div class="family-table-items"{% if family_table_text %} style="margin-top:10px; padding-top:10px; border-top:2px dashed #eee;"{% endif %}>
        {% for fc in neo.family_content %}
        <div class="family-table-item">
          <div class="family-table-who">{{ fc.get('member_name', '') }} שיתפ/ה</div>
          <div class="family-table-headline">{{ fc.get('headline', '') }}</div>
          {% if fc.get('summary') %}<p class="family-table-summary">{{ fc['summary'] }}</p>{% endif %}
          {% if fc.get('link_url') %}<a href="{{ fc['link_url'] }}" class="read-more">קישור &larr;</a>{% endif %}
        </div>
        {% endfor %}
      </div>
      {% endif %}
    </div>
  </div>
  {% endif %}
```

   `family_table_text` uses `| safe`, exactly matching the existing `opener_text`/`closer_text` convention (`neo.metadata.get('opener_text') | safe` — already in the template) — per STYLE_GUIDE §7, whichever future WP populates this field is responsible for converting any markdown to HTML before it reaches this field (this WP does not add a markdown filter; `env.filters['md']` already exists in `m4_renderer.py` via `strip_markdown` for that future WP to use, unchanged here). `fc.get('summary')`/`headline` are **not** `| safe` (plain autoescaped text) — matches how every other family-submission-adjacent field in the template is rendered today (no precedent for `| safe` on submission text).

**New CSS:**

```css
  /* ===== FAMILY TABLE ===== */
  .family-table-panel { background: #fdf0e3; border-color: var(--orange); }
  .family-table-prompt { font-size: 15px; line-height: 1.7; }
  .family-table-item { padding: 8px 0; border-bottom: 1px dashed #eee; }
  .family-table-item:last-child { border-bottom: none; }
  .family-table-who { font-family: 'Bangers', cursive; font-size: 12px; color: var(--orange); letter-spacing: 0.5px; }
  .family-table-headline { font-size: 15px; font-weight: bold; margin-top: 2px; }
  .family-table-summary { font-size: 13px; color: #666; margin-top: 2px; }
```

**Acceptance criteria:**
- [ ] AC-31: With `neo.family_content == []` and `family_table_text == ""` (both falsy), the section does not render at all.
- [ ] AC-32: With `neo.family_content` non-empty and `family_table_text == ""`, the section renders with only the items list (no `.family-table-prompt` paragraph, no dashed-divider style on `.family-table-items`).
- [ ] AC-33: With `family_table_text` non-empty and `neo.family_content == []`, the section renders with only the prompt paragraph (no `.family-table-items` div at all — not an empty one).
- [ ] AC-34: For each `neo.family_content` entry, all 4 conditionally-rendered fields (`summary`, `link_url`) independently omit their markup when falsy/absent — a fixture with `summary` present but `link_url` absent produces a `<p class="family-table-summary">` but no `<a class="read-more">` for that item, and vice versa.
- [ ] AC-35: `db.update_submission(..., status='published', ...)` in `m3_normalizer.py`'s existing `archive()` function (unchanged by this WP) iterates `neo.family_content` regardless of whether the template renders it — confirms this WP's change is purely additive on the rendering side and does not alter the existing archival side-effect of family submissions being marked `published` (out of scope to verify further here, noted for the validator's awareness only).
- [ ] AC-36: A `neo.family_content` item whose `member_name` key is absent renders `''` before "שיתפ/ה" (via `.get('member_name', '')`) rather than raising — degrades gracefully, does not block the rest of the section from rendering.

### 2.5 📚 From Our Shelf (מהמדף שלנו)

Not one of LOD200's 13 numbered sections — a 14th, additive section DESIGN_FISH assigns to this WP (§1 decision block: *"'מהמדף שלנו / From Our Shelf' section"*, required). Reads `neo.metadata['shelf_pick']`, shape mirrors `config/family.json`'s existing `shared_interests.bookshelf.books[]` entries (`title_he, title_en, author, category` — verified live in that file) plus 2 new fields (`blurb`, optional `member_id`) this section needs that the raw book list doesn't carry. **Placement:** after Family Table (§2.4), before Puzzle — a deliberate, documented placement choice (both are "family togetherness" content; it does not disturb the relative order of any of LOD200's 13 numbered sections, only slots between two of them).

**What to implement.** Insert immediately after the Family Table block (§2.4), before the existing `<!-- ===== PUZZLE ===== -->` comment:

```jinja
  <!-- ===== FROM OUR SHELF (מהמדף שלנו) ===== -->
  {% set shelf = neo.metadata.get('shelf_pick', {}) %}
  {% if shelf.get('title_he') or shelf.get('title_en') %}
  <div class="section-sep">📚 מהמדף שלנו 📚</div>

  <div class="panel-level3 shelf-panel">
    <div style="padding: 14px 16px; display: flex; gap: 12px; align-items: flex-start;">
      <div class="shelf-icon character-reading">{{ character_html('reading', current_month) | safe }}</div>
      <div>
        <h4 class="shelf-title">{{ shelf.get('title_he', shelf.get('title_en', '')) }}</h4>
        {% if shelf.get('title_en') and shelf.get('title_he') %}<div class="shelf-title-en">{{ shelf['title_en'] }}</div>{% endif %}
        <div class="shelf-meta">{{ shelf.get('author', '') }}{% if shelf.get('category') %} &bull; {{ shelf['category'] }}{% endif %}</div>
        {% if shelf.get('blurb') %}<p class="shelf-blurb">{{ shelf['blurb'] }}</p>{% endif %}
        {% if shelf.get('member_id') %}
        <div class="viewing-badge" style="background:{{ member_bg.get(shelf['member_id'], '#f0f0f0') }}; color:{{ member_colors.get(shelf['member_id'], 'var(--ink)') }}; margin-top:6px;">{{ member_emoji.get(shelf['member_id'], '📖') }} מדף {{ member_names.get(shelf['member_id'], '') }}</div>
        {% endif %}
      </div>
    </div>
  </div>
  {% endif %}
```

   Reuses `.viewing-badge` from §2.3 (same visual language — small rounded chip) rather than a new badge class, keeping the CSS surface smaller.

**New CSS:**

```css
  /* ===== FROM OUR SHELF ===== */
  .shelf-panel { background: #f3ede3; border-color: #8B4513; }
  .shelf-icon { flex-shrink: 0; }
  .shelf-title { font-family: 'Bangers', cursive; font-size: 16px; line-height: 1.3; }
  .shelf-title-en { font-size: 12px; color: #888; font-style: italic; margin-top: 1px; }
  .shelf-meta { font-size: 12px; color: #888; margin-top: 3px; }
  .shelf-blurb { font-size: 13px; color: #666; margin-top: 6px; line-height: 1.6; }
```

**Acceptance criteria:**
- [ ] AC-37: With `neo.metadata['shelf_pick']` absent, or present but both `title_he` and `title_en` falsy/absent, the section does not render.
- [ ] AC-38: With only `title_he` present, `shelf.get('title_he', shelf.get('title_en',''))` resolves to `title_he`'s value and no `.shelf-title-en` div renders (the `and` guard on both keys being present).
- [ ] AC-39: The rendered HTML places this section's `.shelf-panel` after `.family-table-panel` and before `.puzzle-panel` in DOM order (string-offset comparison, same technique as AC-29).
- [ ] AC-40: `character_html('reading', current_month) | safe` is the exact call — confirms the `reading` pose (not `hero-greeting`/`thinking`/`pointing`/`goodbye`) is used here, matching the semantic pose-to-section mapping documented in §2.7.
- [ ] AC-41: This section reads `neo.metadata['shelf_pick']` only — it does **not** read `config/family.json`'s `shared_interests.bookshelf` directly (the template has no file-system access to `config/family.json` and none should be added; selecting *which* book from the family bookshelf to feature this week is upstream content-generation logic, out of scope here — see §6).

### 2.6 👨‍👩‍👧 Extended Family section (מהמשפחה המורחבת)

LOD200 §2 item 10: "1–2 items... **public-only, pointer+link not copy, loving tone**"; §5's content checklist repeats: "Extended-family items: public-only, pointer+link (not copied media), loving tone, opt-out honored." **Hard rule enforced at the template layer, not just the content layer:** this section must never render an `<img>`, `<video>`, or any embedded media for an extended-family item, even if a future data source were to add an `image_url`-shaped key — the template simply has no code path that could render one, as defense in depth alongside the content-authoring guardrail.

**What to implement.** Insert immediately after the existing Puzzle block's closing `{% endif %}`, before the existing `<!-- ===== TODAY IN HISTORY ===== -->` comment:

```jinja
  <!-- ===== EXTENDED FAMILY (מהמשפחה המורחבת) ===== -->
  {% set extended_family = neo.metadata.get('extended_family', []) %}
  {% if extended_family %}
  <div class="section-sep">👨‍👩‍👧 מהמשפחה המורחבת 👨‍👩‍👧</div>

  <div class="panel-level3 extended-family-panel">
    <div style="padding: 14px 16px;">
      {% for ef in extended_family %}
      <div class="ext-family-item">
        <div class="ext-family-name">{{ ef.get('name', '') }}{% if ef.get('relation') %} <span class="ext-family-relation">&middot; {{ ef['relation'] }}</span>{% endif %}</div>
        <div class="ext-family-headline">{{ ef.get('headline', '') }}</div>
        {% if ef.get('pointer_text') %}<p class="ext-family-pointer">{{ ef['pointer_text'] }}</p>{% endif %}
        {% if ef.get('link_url') %}<a href="{{ ef['link_url'] }}" class="read-more">לצפייה &larr;</a>{% endif %}
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}
```

**New CSS:**

```css
  /* ===== EXTENDED FAMILY ===== */
  .extended-family-panel { background: #fdeef2; border-color: var(--maayan); }
  .ext-family-item { padding: 8px 0; border-bottom: 1px dashed #eee; }
  .ext-family-item:last-child { border-bottom: none; }
  .ext-family-name { font-family: 'Bangers', cursive; font-size: 14px; }
  .ext-family-relation { font-family: 'Patrick Hand', cursive; font-size: 12px; color: #888; font-weight: normal; }
  .ext-family-headline { font-size: 14px; margin-top: 2px; }
  .ext-family-pointer { font-size: 13px; color: #666; margin-top: 3px; line-height: 1.6; }
```

**Acceptance criteria:**
- [ ] AC-42: With `neo.metadata['extended_family']` absent or `[]`, the section does not render.
- [ ] AC-43: `grep -n "extended-family-panel" templates/newsletter.html.j2` shows **no** `<img`, `<video`, `<source`, or `style="background-image` anywhere between this section's opening and closing tags — mechanically enforceable, zero-tolerance check for the "pointer+link not copy" rule.
- [ ] AC-44: 1 item and 2 items both render correctly (LOD200 says "1–2 items" — this section places no upper or lower bound beyond the outer `{% if %}` truthiness check; a 3rd+ item, if ever present, also renders — the "1–2" cap is a content-authoring guideline for whichever future WP populates this list, not something this template enforces or needs to enforce).
- [ ] AC-45: `ef.get('relation')` absent renders the name alone with no `&middot;` separator and no empty `<span class="ext-family-relation">` — the whole conditional span is omitted, not rendered empty.
- [ ] AC-46: This section's placement is verified between `.puzzle-panel` and `.history-panel` in DOM order (matches LOD200 §2's exact ordering: item 9 Puzzle, item 10 Extended-family, item 11 History).

### 2.7 Mascot pose wiring — Puzzle, Discovery, Closer

DESIGN_FISH §1: "4 reusable mascot poses tied to section semantics: Thinking (puzzle), Pointing (discovery), Reading (content), Waving (greeting)." `POSE_EMOJI_MAP` in `src/m4_renderer.py` already defines exactly these pose keys (`'thinking', 'pointing', 'reading', 'hero-greeting', 'goodbye'`) — this subsection wires the 3 remaining slots (`hero-greeting` was wired in §2.2; `reading` was wired in §2.5) into their semantically-matching **existing** sections, replacing bare static emoji spans with real `character_html()` calls. All 3 are small, surgical, single-element diffs.

**What to implement — 3 exact find/replace pairs, all inside existing, unmoved markup:**

1. **Puzzle** (existing `<!-- ===== PUZZLE ===== -->` block). Find:

```jinja
        <span class="mini-mascot" style="font-size:24px;">{{ neo.metadata.get('character_emoji', '🎩') }}</span>
```

   (the one inside `.puzzle-panel`, immediately before "חידת השבוע"). Replace with:

```jinja
        <span class="mini-mascot character-thinking">{{ character_html('thinking', current_month) | safe }}</span>
```

2. **Discovery** (existing `<!-- ===== DISCOVERY ===== -->` block, inside the `{% for item in neo.discovery %}` loop). Find:

```jinja
      <div class="bridge-text">🔮 {{ item.bridge_text }}</div>
```

   Replace with:

```jinja
      <div class="bridge-text"><span class="mini-mascot character-pointing">{{ character_html('pointing', current_month) | safe }}</span> {{ item.bridge_text }}</div>
```

3. **Closer** (existing `<!-- ===== CLOSER ===== -->` block). Find:

```jinja
    <div style="margin-top:10px; text-align:center;">
      <span style="font-size:40px;">{{ neo.metadata.get('character_emoji', '🎩') }}</span>
    </div>
```

   Replace with:

```jinja
    <div style="margin-top:10px; text-align:center;" class="character-goodbye">
      {{ character_html('goodbye', current_month) | safe }}
    </div>
```

**Left unchanged (explicit, not an oversight):** the cover's `.mascot-name` credit line (`{{ neo.metadata.get('character_emoji', '🎩') }} {{ neo.metadata.get('character_name', ...) }} — {{ character_month }}`) and the Survey section's mini-mascot both keep their existing static-emoji rendering — neither is one of DESIGN_FISH's 4 named poses (the cover credit line is a small text-scale attribution, not a pose slot; Survey has no corresponding `POSE_EMOJI_MAP` entry). Touching either would be scope creep beyond the 4 named poses.

**Acceptance criteria:**
- [ ] AC-47: `grep -c "neo.metadata.get('character_emoji'" templates/newsletter.html.j2` decreases from its current count by exactly 2 (Puzzle and Closer's bare-emoji usages removed) — the Cover credit line's and Survey's usages remain, so the count does not drop to 0.
- [ ] AC-48: All 3 replacements use `character_html(<pose>, current_month) | safe` — `| safe` present on every one (same class of bug as AC-21; re-verified here specifically for these 3 additional call sites since they are easy to miss in a find/replace pass).
- [ ] AC-49: `current_month` (not a literal string) is passed as the second argument at all 3 sites — confirms monthly rotation actually works (a hardcoded `'2026-04'` would silently freeze the character forever past April).
- [ ] AC-50: The Discovery bridge-text change preserves `item.bridge_text`'s existing autoescaping (no `| safe` added to that part of the line) — only the new mascot span is `| safe`'d, not the pre-existing dynamic text next to it.
- [ ] AC-51: Rendering with no character PNGs present (today's real repo state) shows the `thinking`/`pointing`/`goodbye` emoji fallbacks (🤔/👉/👋 per `POSE_EMOJI_MAP`) at each of the 3 sites, sized per §2.2's `.character-thinking`/`.character-pointing`/`.character-goodbye` CSS (not the bare, unstyled `font-size:24px`/`40px` inline styles this replaces — those inline styles are deleted along with the elements they were on).

### 2.8 Dark mode

DESIGN_FISH §3 item 2: named a core principle in `spec.md`, implemented once in `archive/design-april-2026/design-examples/style-3-magazine.html` via `@media (prefers-color-scheme: dark) { :root {...} }`, "zero trace today" in the real template. This subsection ports the **mechanism** (a `:root`-token override under `prefers-color-scheme: dark`) to this template's own token set — style-3-magazine.html's tokens (`--card`, `--text`, `--muted`, `--border`) do not exist in this file and are not introduced; this template's existing tokens (`--bg`, `--ink`, `--panel-bg`, member colors) are extended and overridden instead.

**Design problem worth stating explicitly (why this isn't a 6-line `:root` override):** `--ink` today does triple duty — text color, border color, **and** every `box-shadow`'s color (all of this template's comic shadows are zero-blur solid offsets, e.g. `box-shadow: 6px 6px 0 var(--ink)`). In dark mode, text and borders correctly need to go *light* (readable against a dark page) — but shadows must stay *dark* regardless of theme, or "shadow" stops reading as depth at all. Splitting these requires exactly one new token, `--shadow-color`, defaulting to `var(--ink)` in light mode (byte-identical output to today, since today's `--ink` already **is** the dark shadow color) and pinned to a fixed dark value in dark mode (decoupled from the now-light `--ink`).

**What to implement:**

1. Add 7 new custom properties to the existing `:root { ... }` block (append before its closing `}`, i.e. after the existing `--tzlil: #e67e22;` line):

```css
    --shadow-color: var(--ink);
    --dot-color: #e8dcc8;
    --nimrod-bg: #e6f0fa;
    --michal-bg: #e6f5ed;
    --shaked-bg: #ece6f5;
    --maayan-bg: #fce8ec;
    --tzlil-bg: #fef3e2;
```

   (the 5 `--*-bg` values are the exact literals `member_bg`'s Python dict held before §2.1 point 8's edit — this is what makes that edit visually a no-op in light mode.)

2. Immediately after the `:root { ... }` block's closing `}` (before the existing `* { margin: 0; ... }` rule), insert a new block:

```css
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #1a1815;
      --ink: #eee8dc;
      --panel-bg: #241f19;
      --shadow-color: #000000;
      --dot-color: #2a251e;
      --nimrod-bg: #16324a;
      --michal-bg: #123a26;
      --shaked-bg: #2e2140;
      --maayan-bg: #45202a;
      --tzlil-bg: #4a3410;
    }
    .opener { background: linear-gradient(135deg, #2e2a12 0%, #26220d 100%); }
    .closer { background: linear-gradient(135deg, #0f2620, #0c2118); }
    .discovery-panel { background: #241b2e; }
    .puzzle-panel { background: #2e2a12; }
    .history-panel { background: #2e2413; }
    .survey-panel { background: linear-gradient(135deg, #12212e, #0d1b26); }
    .viewing-panel { background: #0f2530; }
    .family-table-panel { background: #2b2013; }
    .shelf-panel { background: #241f18; }
    .extended-family-panel { background: #2b1720; }
  }
```

3. **Mechanical substring replacement inside the existing `<style>` block:** every `box-shadow` declaration currently reading `... 0 var(--ink);` (verified today at exactly these rule targets: `.cover`, `.weather-section`, `.panel-level1` base + `:hover`, `.panel-level2` base + `:hover`, `.panel-level3`, `.family-strip`, `.wa-btn` base + `:hover` — 10 declarations total) must have `var(--ink)` replaced with `var(--shadow-color)`. Every other use of `var(--ink)` in the file (borders, the masthead `text-shadow`, the mascot-bubble triangle) is **left unchanged** — those are correct to keep following `--ink` directly (light-on-dark borders in dark mode is the intended, correct look; the masthead `text-shadow` sits on the Cover's own hardcoded red/orange gradient, unaffected by theme either way).
4. **Explicitly out of scope, by design (not an oversight):** the existing `.opener`/`.closer`/`.discovery-panel`/`.puzzle-panel`/`.history-panel`/`.survey-panel` `box-shadow: ... rgba(0,0,0,0.1)` / `rgba(0,0,0,0.3)` declarations (member-tag, level-badge, opener, closer) are **not** retargeted to `--shadow-color` — doing so would change their opacity/weight in *light* mode too (they are currently soft, semi-transparent accents, not solid `--ink` shadows), which would be an unrequested light-mode visual change. They remain visually subtle in dark mode as an accepted, minor, explicitly-flagged limitation (§6). Secondary/muted text colors hardcoded as literal grays (`#555`, `#666`, `#888`, `#999`, `#aaa` — excerpts, meta text, footer fine-print) are likewise not individually retargeted; primary body text (`color: var(--ink)` on `<body>`) is already theme-aware for free and carries the main readability burden.
5. The existing halftone background-image declaration on `body` (`background-image: radial-gradient(circle, #e8dcc8 1px, transparent 1px);`) has its literal `#e8dcc8` replaced with `var(--dot-color)`.

**Acceptance criteria:**
- [ ] AC-52: Rendering with no `prefers-color-scheme` media feature active (or explicitly `light`) produces **byte-identical** HTML to this WP's non-dark-mode output — dark mode is CSS-only and adds no new Jinja branches, so this AC is really "confirm no Jinja logic was accidentally made dark-mode-conditional," verified by inspecting the diff contains only `<style>` block changes for this subsection.
- [ ] AC-53: All 10 `box-shadow` declarations enumerated in point 3 read `var(--shadow-color)`, not `var(--ink)`, after this edit; `grep -c "0 var(--ink))\?;" templates/newsletter.html.j2` (box-shadow-specific pattern) returns `0` for the box-shadow context specifically (border declarations using `var(--ink)` are unaffected and still present — this AC targets only the box-shadow substring, not every `var(--ink)` occurrence in the file).
- [ ] AC-54: Loading the rendered HTML in a headless browser with emulated `prefers-color-scheme: dark` (see §7's qa_probe.mjs recipe) shows the computed `background-color` of `<body>` resolving to `#1a1815`, and of `.panel-level1`/`.cover`/`.weather-section` resolving to `#241f19` — confirms the cascade actually reaches rendered elements, not just the `:root` declaration.
- [ ] AC-55: Under emulated dark mode, `.member-corner .panel-level1 .hero-visual` (no-image fallback) and `.feat-visual-fallback` both resolve their gradient/background-color to one of the 5 dark `--*-bg` values (never the light pastel), for a fixture item belonging to each of the 5 members in turn.
- [ ] AC-56: Under emulated light mode (default / explicit `light`), the same 2 selectors from AC-55 resolve to the original light pastel hex values, unchanged from today.
- [ ] AC-57: `--shadow-color` computed value is `#000000` under dark mode and equals `--ink`'s **light-mode** value (`#2c2c2c`) under light mode — confirms the light-mode "alias" behaves as documented (not literally `#2c2c2c` hardcoded twice, but resolving to the same value via `var(--ink)` indirection — verified by computed style, not source text).
- [ ] AC-58: The 4 new panel classes added in §2.3–§2.6 (`viewing-panel`, `family-table-panel`, `shelf-panel`, `extended-family-panel`) each have both a light-mode background (defined in their own subsection's CSS) and a dark-mode override (defined in this subsection's `@media` block) — cross-checked so no new section from this WP is accidentally left with a bright light-only background bleeding through in dark mode.
- [ ] AC-59: `.hero-scene` SVG (§2.2) is **not** patched for dark mode — its sky/sea colors are illustrative and intentionally theme-invariant (a blue daytime sea scene doesn't have a meaningful "dark mode" version within this WP's scope); confirmed by absence of any `.hero-scene` rule inside the new `@media` block. Flagged here so the validator does not read this omission as a gap.

### 2.9 Footer enhancements — editor credit + inline one-tap emoji rating

LOD200 §2 item 13 requires the footer to contain: "family emoji strip, edition #, **'עורכת: צליל' editor credit**, 'by AgentsOS @ nimrod.bio'" — the editor-credit text is **currently absent** from the footer (confirmed: no "עורכת"/"editor" string anywhere in the current template). Sibling spec **FNL-S001-P002-WP004** (`editor.py`) independently anticipates an `editors_choice` field it explicitly defers as *"template concern (WP007...)"* — that richer per-item "editor's pick" highlight is **not** built by this WP (see §6); only the plain-text credit line LOD200 §13 literally asks for is added here. Separately, DESIGN_FISH assigns this WP the inline one-tap emoji rating fish (§3 item 3: "😍😊😐👎 as `#rate-N` anchors in footer... lower-friction than WhatsApp-only survey").

**Design decision — the rating buttons must actually do something.** The archived prototypes (`newsletter-preview-v1.0.1.html`) used bare `href="#"` placeholders — inert. This is a static, FTP-uploaded HTML page (no backend endpoint to receive a click), and LOD200 §7 explicitly defers "reply ingestion / per-item feedback" to Phase B. Rather than ship 4 dead links, this WP routes each button through the **exact same** `whatsapp_group_link`/`whatsapp_number` metadata keys and `wa.me` deep-link pattern the existing Survey section already uses — each tap opens WhatsApp with the rating pre-filled as text (when `whatsapp_number` is configured) or opens the group chat (when only `whatsapp_group_link` is configured, same no-pre-fill limitation the existing Survey section already has in that branch — not a new gap this WP introduces). Each button additionally carries `id="rate-N"`, satisfying DESIGN_FISH's literal `#rate-N` anchor naming even though the primary interaction is the `href`, not fragment navigation.

**What to implement.** Locate the existing footer:

```jinja
  <!-- ===== FOOTER ===== -->
  <div class="footer-strip">
    <div class="family-icons">⛵ 🌿 ⚗️ 🎪 🧮</div>
    Family Newsletter &bull; #{{ edition_number or '1' }} &bull; {{ neo.date_formatted or neo.date }}
    <br><span style="font-family:sans-serif; font-size:11px; color:#bbb; letter-spacing:0.5px;">by <strong style="color:#999;">AgentsOS</strong> @ nimrod.bio</span>
    <br><span style="font-family:monospace; font-size:10px; color:#ccc;">v{{ system_version or '3.0.0' }} &bull; built {{ build_timestamp or '' }}</span>
  </div>
```

   Replace with:

```jinja
  <!-- ===== FOOTER ===== -->
  <div class="footer-strip">
    <div class="family-icons">⛵ 🌿 ⚗️ 🎪 🧮</div>
    Family Newsletter &bull; #{{ edition_number or '1' }} &bull; {{ neo.date_formatted or neo.date }}
    <br><span style="font-family:'Patrick Hand',cursive; font-size:13px; color:#999;">עורכת: {{ neo.metadata.get('editor_name', 'צליל') }}</span>

    {% set footer_wa_link = neo.metadata.get('whatsapp_group_link', '') %}
    {% set footer_wa_number = neo.metadata.get('whatsapp_number', '') %}
    {% if footer_wa_link or footer_wa_number %}
    <div class="rating-row">
      {% set ratings = [
        {'emoji': '😍', 'label': 'מעולה', 'text': 'הניוזלטר השבוע: מעולה! 😍'},
        {'emoji': '😊', 'label': 'טוב', 'text': 'הניוזלטר השבוע: טוב 😊'},
        {'emoji': '😐', 'label': 'ככה ככה', 'text': 'הניוזלטר השבוע: ככה ככה 😐'},
        {'emoji': '👎', 'label': 'לא טוב', 'text': 'הניוזלטר השבוע: לא טוב 👎'}
      ] %}
      {% for r in ratings %}
      {% if footer_wa_number %}
      <a href="https://wa.me/{{ footer_wa_number }}?text={{ r.text | urlencode }}" class="rate-btn" id="rate-{{ loop.index }}"><span class="emoji">{{ r.emoji }}</span><span class="label">{{ r.label }}</span></a>
      {% else %}
      <a href="{{ footer_wa_link }}" class="rate-btn" id="rate-{{ loop.index }}"><span class="emoji">{{ r.emoji }}</span><span class="label">{{ r.label }}</span></a>
      {% endif %}
      {% endfor %}
    </div>
    {% endif %}

    <br><span style="font-family:sans-serif; font-size:11px; color:#bbb; letter-spacing:0.5px;">by <strong style="color:#999;">AgentsOS</strong> @ nimrod.bio</span>
    <br><span style="font-family:monospace; font-size:10px; color:#ccc;">v{{ system_version or '3.0.0' }} &bull; built {{ build_timestamp or '' }}</span>
  </div>
```

   `footer_wa_link`/`footer_wa_number` are deliberately **not** named `wa_link`/`wa_number` (which the existing Survey section already `{% set %}`s earlier in the same template) — using distinct names avoids any reader confusion about variable reuse across sections, even though Jinja itself would tolerate the reuse harmlessly (top-level `{% set %}` simply reassigns).

**New CSS:**

```css
  /* ===== INLINE EMOJI RATING (footer) ===== */
  .rating-row { display: flex; justify-content: center; gap: 8px; margin: 10px 0; flex-wrap: wrap; }
  .rate-btn {
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    text-decoration: none;
    padding: 8px 14px;
    border-radius: 12px;
    background: var(--panel-bg);
    border: 2px solid var(--ink);
    box-shadow: 2px 2px 0 var(--shadow-color);
    transition: transform 0.15s, box-shadow 0.15s;
  }
  .rate-btn:hover { transform: translate(-1px, -1px); box-shadow: 3px 3px 0 var(--shadow-color); }
  .rate-btn .emoji { font-size: 24px; }
  .rate-btn .label { font-size: 10px; color: #888; font-family: 'Patrick Hand', cursive; }
```

**Acceptance criteria:**
- [ ] AC-60: The string "עורכת:" appears exactly once in the rendered HTML, followed by `neo.metadata.get('editor_name', 'צליל')`'s resolved value — with no `editor_name` key set, this defaults to "צליל" (matching LOD200 §13's literal example verbatim).
- [ ] AC-61: With neither `whatsapp_group_link` nor `whatsapp_number` set in `neo.metadata`, no `.rating-row` div renders at all (not an empty one) — the footer degrades to exactly today's 3 lines plus the new editor-credit line.
- [ ] AC-62: With `whatsapp_number` set, all 4 buttons render `href="https://wa.me/{{ number }}?text=..."` with **4 distinct** URL-encoded `text` values (one per rating) — verified by decoding each `href`'s `text` query param and confirming they are pairwise different.
- [ ] AC-63: With only `whatsapp_group_link` set (`whatsapp_number` absent/falsy), all 4 buttons render the **same** `href` (the group link, no per-rating differentiation) — this is the accepted, pre-existing limitation carried over from the Survey section's identical branch, not a new bug.
- [ ] AC-64: Each button has a unique `id="rate-1"` through `id="rate-4"` in that order, regardless of which `href` branch is active.
- [ ] AC-65: `r.text | urlencode` correctly percent-encodes the Hebrew text and the emoji — verified by confirming the resulting `href` attribute contains no literal raw Hebrew/emoji bytes unescaped in a way that would break URL parsing (i.e. the `urlencode` filter is applied, not skipped).

### 2.10 `og:image` and social meta tags

LOD200 §8 / REVIVAL_PLAN §3: WP005 (`teaser.py`, not yet spec'd) produces `teaser.png`, a 1080×1350 Pillow-rendered card; WP006 (FTP publish, not yet spec'd) uploads it to the **same dated directory** as `index.html` (REVIVAL_PLAN: *"FTP ל-uPress: index.html + teaser.png ← המסלול המוכח"* — "the proven path"). **The current template has zero `og:`/`twitter:` meta tags today** (`grep -c "og:image" templates/newsletter.html.j2` on the current file returns `0`) — this is a pure addition, not a modification of an existing line (the task brief's phrasing "og:image line → point at teaser.png" is read here as "add the og:image line, pointed at teaser.png," since no such line exists yet to redirect).

**What to implement.** Insert immediately after the existing `<title>Family Newsletter - {{ neo.date }}</title>` line, before the Google Fonts `<link>`:

```jinja
{% if og_image_url %}
<meta property="og:image" content="{{ og_image_url }}">
<meta property="og:image:width" content="1080">
<meta property="og:image:height" content="1350">
<meta property="og:title" content="Family Newsletter — {{ neo.date_formatted or neo.date }}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
{% endif %}
```

   `og_image_url` comes from `m4_renderer.py`'s `render()` (§2.1) — `1080`/`1350` are literal per REVIVAL_PLAN's stated teaser dimensions, not computed (this WP has no way to inspect the actual PNG's dimensions at template-render time, and WP005 — out of scope here — is the module responsible for producing a PNG matching these exact dimensions; if WP005 ever ships a different size, updating these two literals is a 1-line follow-up to whichever WP notices the mismatch, not a structural change).

**Acceptance criteria:**
- [ ] AC-66: With `og_image_url` falsy (the `render(neo)` no-`settings` case, AC-02), none of the 6 new meta tags appear in the output — the whole block is inside one `{% if %}` guard, no partial rendering.
- [ ] AC-67: With `og_image_url` truthy, all 6 tags render, and the `og:image` tag's `content` is exactly `og_image_url`'s value with no additional transformation (no trailing slash added/removed, no re-encoding).
- [ ] AC-68: `og:title`'s content uses `neo.date_formatted or neo.date` — the same fallback pattern the existing `<title>` tag and `.cover-top .edition-badge` already use elsewhere in this file, for consistency.
- [ ] AC-69: The new meta-tag block sits entirely within `<head>`, before `<style>` opens — verified by string-offset comparison in the rendered output.

## 3. Data model changes

**No DDL, no database migration.** All changes are in-process Python dataclass fields and a Jinja-context dict key.

**`src/models.py` — `GeneratedContent` (4 new fields, all with defaults — see §2.1 point 1 for the exact diff):**

| Field | Type | Default | Populated by (future, unclaimed) |
|---|---|---|---|
| `viewing` | `dict` | `{}` | Not yet chartered — see §2.1 coordination note |
| `family_table_text` | `str` | `""` | Not yet chartered |
| `extended_family` | `list` | `[]` | Not yet chartered |
| `shelf_pick` | `dict` | `{}` | Not yet chartered |

**`neo.metadata` — Jinja-context contract this WP's template code reads (all optional, all `.get()`-guarded, never a bare dataclass field on `NEO` itself — threaded through by the `m3_normalizer.py` companion edit, §2.1 point 6):**

| Key | Shape | Consumed by |
|---|---|---|
| `viewing` | `{'family_pick': {title, platform, hebrew_subs: bool, available_il: bool, note}, 'personal_pick': {member_id, title, platform, hebrew_subs, available_il, note}}` | §2.3 |
| `family_table_text` | `str` (rendered `\| safe`, matches `opener_text`/`closer_text` convention) | §2.4 |
| `extended_family` | `list[{name, relation, headline, pointer_text, link_url}]` — **no image key ever rendered** | §2.6 |
| `shelf_pick` | `{title_he, title_en, author, category, member_id, blurb}` — mirrors `config/family.json shared_interests.bookshelf.books[]` shape plus `blurb`/`member_id` | §2.5 |
| `editor_name` | `str`, default `'צליל'` if absent | §2.9 |

**`neo.family_content`** — **no shape change.** Already built by the existing (pre-this-WP) `m3_normalizer.py` code; this WP is purely a new consumer (§2.4), not a producer or shape-changer.

## 4. Renderer / template context contract

No HTTP endpoints (batch pipeline, not a web service). The relevant contract is `render()`'s Python signature and the full set of names available inside the Jinja template.

| Symbol | Kind | Signature / Shape | Change |
|---|---|---|---|
| `render` | function | `render(neo: NEO, template_path: str = "templates/", db: Database = None, settings: Settings = None) -> str` | `settings` param **added** (optional, backward-compatible — every existing call site with no `settings` arg keeps working, §2.1 AC-02) |
| `og_image_url` | new Jinja context var | `str \| None` | New — computed inside `render()`, §2.1 point 4 |
| `character_html` | Jinja context var (function) | `(pose: str, month: str = None) -> str` (returns raw HTML) | **Unchanged function** — pre-existing in `m4_renderer.py`, was already passed into context but never called from the template before this WP. Every call site **must** use `\| safe` (§2.2 AC-21, §2.7 AC-48) |
| `current_month` | Jinja context var | `str` (`YYYY-MM`) | **Unchanged** — pre-existing, was already in context, now actually consumed |
| `member_bg` | Jinja `{% set %}` dict | `{member_id: 'var(--<id>-bg)'}` | Values changed from literal hex to CSS variable references (§2.1 point 8) — same 5 keys, same call sites |

## 5. Error handling requirements

| Error case | Expected behavior |
|---|---|
| `settings=None` passed to `render()` (or omitted) | `og_image_url` stays `None`; §2.10's meta-tag block does not render; no exception (AC-02, AC-66). |
| `newsletter_url_base(settings)` raises inside `render()` | Caught, logged via `logger.warning`, `og_image_url` stays `None`; render proceeds (AC-04). |
| `neo.metadata` missing any of `viewing`/`family_table_text`/`extended_family`/`shelf_pick`/`editor_name` entirely (e.g. an edition archived before this WP shipped, replayed through the new template) | Every read goes through `.get(key, default)` — the corresponding new section simply does not render (or, for `editor_name`, falls back to `'צליל'`); no `jinja2.exceptions.UndefinedError` (AC-07). |
| A `neo.member_sections` entry with `items: []` | That member's corner is skipped entirely — no empty corner, no crash (AC-13). This is a **rendering** behavior only; LOD200 §2 item 5's "every member ≥1 item (hard rule)" is enforced upstream in content curation/scoring (out of scope for this template — if it is ever violated, the symptom is a missing corner on the page, not a template exception, which is the correct fail-open behavior for a Friday-morning cron job over silently blocking the whole build). |
| `corner_items[0]` accessed when `corner_items` is falsy | Never reached — guarded by the outer `{% if corner_items %}` (AC-13); Jinja would otherwise raise on `[0]`-indexing an empty list. |
| `item.url` / `corner_hero.url` is `None` or key-absent when computing `is_youtube` | `(item.url or '')` guards every occurrence — evaluates to `False`, never raises (AC-08, AC-23). |
| `character_html(pose, month)` called for a `pose`/`month` combination with no asset on disk | Pre-existing, unchanged behavior in `get_character_html()` — falls back to the emoji span (AC-22). Not re-specified here; this WP only adds call sites, not new fallback logic. |
| A bare (non-`\|safe`) `{{ character_html(...) }}` call anywhere | **Not a runtime error** — `autoescape=True` silently HTML-escapes the returned markup into visible `&lt;...&gt;` text on the page. Prevented by code review at spec-authoring time (AC-21, AC-48), not caught by any exception-based test; the cross-engine validator (§7) must specifically grep for this. |
| Extended-family item dict ever gaining an `image_url`-shaped key from a future data source | No code path renders it — §2.6's markup has no `<img>` regardless of what keys are present on `ef` (AC-43). |
| `r.text` (rating message) containing Hebrew + emoji, passed through `\| urlencode` | Correctly percent-encoded — standard Jinja2 filter behavior, no custom escaping needed (AC-65). |

## 6. Out of scope (explicit)

- **The teaser image itself** (`teaser.py`, pixel-level PNG generation, character art) — **WP005**, not yet spec'd. This WP only computes the **URL** it will live at (§2.10) and renders an `og:image` tag pointing there; the tag will 404 until WP005 ships and WP006 uploads the file — accepted, matches this WP's brief instruction verbatim.
- **FTP publish** (`m5_distributor.py`, uPress upload) — **WP006**, not yet spec'd. Unmodified by this WP.
- **Content authoring** for any of the new fields (`viewing`, `family_table_text`, `extended_family`, `shelf_pick`, and WP004's own `editors_choice`) — future `researcher.py`/`editor.py` work, not yet chartered to any WP (§2.1, §3). This WP defines the render-side contract only; every new section degrades to "does not render" until that future work lands, by construction (§2.3–§2.6 ACs).
- **`editors_choice`** (WP004's anticipated per-item "editor's pick" highlight/badge, e.g. within Tzlil's corner) — explicitly named by WP004 as a WP007 template concern, but **not built here**. Only LOD200 §13's plain-text "עורכת: [name]" footer credit line is added (§2.9). The richer per-item highlight remains an open, unclaimed gap for a future WP.
- **Per-topic SVG scene selection** (`SVG_MODULE_SPEC.md` §4's topic→scene→character→decoration lookup table; the full "SVG Generator Agent" pipeline in that spec's §5) — this WP ships one **fixed, static** decorative hero scene (sea/sky/boat/kite/fish) reused identically across all 5 corners and all editions; it does not vary by topic/content. Per-topic bespoke scene generation is an AI-generation/content-selection concern (teaser.py/WP005's territory per DESIGN_FISH §2, or a future researcher/editor enhancement), not a template-rendering one. LOD200 §7 already defers "monthly character art" broadly to Phase C; this WP builds only the static rendering infrastructure (scene backdrop + the `character_html()` slot-calling convention) so that future work has something to plug into without touching the template again.
- **Reply ingestion / click-through analytics for the emoji rating** — LOD200 §7 explicitly defers "reply ingestion / per-item feedback" to Phase B. §2.9's rating buttons are a one-way `wa.me` deep link (a real, working interaction), not a tracked/logged event; DESIGN_FISH §5's "Passive: read-pixels/scroll beacons" feedback tier is not implemented by this WP.
- **Retargeting every hardcoded soft-shadow (`rgba(0,0,0,0.1)`/`rgba(0,0,0,0.3)`) and every muted-gray text color (`#555`/`#666`/`#888` etc.) to dark-mode-aware tokens** — explicitly scoped out in §2.8 point 4 as an accepted, minor, flagged limitation. Primary structural colors and primary body text are fully theme-aware; secondary decorative/muted accents are not individually retargeted in this pass.
- **Changing `render()`'s existing `len(html) < 1000` fatal-size guard** to reflect LOD200 §3's `≥30KB` bar — left untouched. That guard is a crude internal sanity floor for arbitrary/test inputs (including sparse mock fixtures with 1 member and no optional sections, which can legitimately render under 30KB); `≥30KB` is an **edition-level acceptance criterion** (LOD200 §3), checked in §7 against a realistic full-content build, not hardcoded as a new internal assertion that could break minimal test fixtures.
- **Any WhatsApp/email send-side change** (`m5_distributor.py`'s `_build_message`, `send_whatsapp`, `send_survey`) — the rating buttons and Survey section both only ever *link out to* WhatsApp; nothing on the send/distribution side is touched.
- **Wiring `llm.py`/`token_tracker.research()`** (WP001/WP002) into anything — unrelated layer, not touched.

## 7. Test requirements

- **Render-without-exception, per new/changed code path** — construct fixture `NEO`/`GeneratedContent` objects covering: (a) all 5 members present with 1/2/3/4/5 items each (exercises AC-14–AC-17's corner-tiering boundary conditions across every parity); (b) a member with 0 items (AC-13); (c) each of `viewing`/`family_table_text`/`extended_family`/`shelf_pick` independently present and independently absent (16 combinations minimum, or at least each field's on/off pair in isolation); (d) `settings=None` vs. a real `Settings` fixture (AC-02–AC-04); (e) at least one item per member whose `url` is a `youtube.com`/`youtu.be` link and at least one that isn't (AC-23–AC-24). Assert via string/substring checks on the returned HTML (the template has no unit-testable Python logic of its own beyond `m4_renderer.py`'s `render()`/`get_character_html()`, which are plain functions callable directly in a `pytest` file — no browser needed for this tier).
- **The `\| safe` grep check (AC-21, AC-48) is mandatory and separate from any rendering test** — a missing `\| safe` does not raise, so no exception-based test catches it. Run: `grep -n "character_html(" templates/newsletter.html.j2` and manually (or via a small script asserting each matched line contains `| safe`) confirm all 5 call sites qualify.
- **Section-count / DOM-order checks (AC-12, AC-29, AC-39, AC-46, §7 below):** parse the rendered HTML (Python's `html.parser` or a simple string-offset comparison, per the ACs above — no need for a full DOM library) and confirm all **13 LOD200 sections** are present via these concrete markers, in this order:

  | # | LOD200 section | Marker |
  |---|---|---|
  | 1 | Cover | `class="cover"` + text `Family Newsletter!` |
  | 2 | Opener | `class="opener"` (fixture must set `opener_text`) |
  | 3 | Family Strip | `class="family-strip"` |
  | 4 | Weather | `class="weather-section"` (fixture must set `weather`) |
  | 5 | Personal Corners | `class="member-corner"` (≥1; ideally 5 in a full fixture) |
  | 6 | Discovery | `class="discovery-panel"` (fixture must set `discovery`) |
  | 7 | Viewing | `class="viewing-panel"` |
  | 8 | Family Table | `class="family-table-panel"` |
  | 9 | Puzzle | `class="puzzle-panel"` (fixture must set `trivia.puzzle`) |
  | 10 | Extended Family | `class="extended-family-panel"` |
  | 11 | History | `class="history-panel"` (fixture must set `trivia.history`) |
  | 12 | Survey | `class="survey-panel"` (fixture must set `survey_question`) |
  | 13 | Closer + Footer | `class="closer"` + `class="footer-strip"` |

  Plus the bonus 14th, non-LOD200 section: `class="shelf-panel"`. A fixture exercising **all 13** simultaneously (plus all 4 new optional fields set) is the canonical "full edition" test case this row's own ordering assertions run against.
- **HTML size ≥30KB (LOD200 §3):** run a real (or `--mock`) end-to-end build via `orchestrator.py` with the full-content fixture above and confirm `len(html) >= 30_000` — an edition-level check, not a unit assertion inside `render()` itself (§6).
- **Dark mode + RTL/overflow — browser-QA runner required, curl is not sufficient for any of this (per this repo's CLAUDE.md discipline: curl sees only HTML, never the rendered box model).** Use `_aos/lean-kit/modules/validation-quality/scripts/qa/qa_probe.mjs` (Node 18+, zero npm/pip deps) against a locally-served copy of the rendered HTML:

  ```bash
  # 1. Render the full-content fixture to data/archive/html/<date>.html
  #    (via orchestrator.py --mock, or a small standalone script calling
  #    m4_renderer.render() + m4_renderer.save_html() directly)

  # 2. Serve that directory locally
  cd data/archive/html && python3 -m http.server 8123 &

  # 3. Run the QA probe — checks horizontal-overflow (RTL's classic failure
  #    mode) at mobile + desktop viewports, screenshots both
  node _aos/lean-kit/modules/validation-quality/scripts/qa/qa_probe.mjs \
    --base http://localhost:8123 --paths /<date>.html \
    --absent "TBD,undefined,None,{{,{%" --shots
  ```

  Exit code `0` required (no horizontal overflow at either viewport, no forbidden substrings — the `{{`/`{%` entries in `--absent` specifically catch unrendered/leaked Jinja syntax, a real risk given this spec's volume of new template code). **Dark-mode rendering** is not covered by `qa_probe.mjs`'s CLI flags as of this WP — verify it via a headless-browser session (Puppeteer/Playwright/Chrome DevTools Protocol, matching `qa_probe.mjs`'s own `chrome-headless-shell` mechanism) with `Emulation.setEmulatedMedia({features: [{name: 'prefers-color-scheme', value: 'dark'}]})` set before capture, then assert the computed styles per §2.8 AC-54–AC-57 and take a screenshot for human/validator review. Full curl-vs-CDP-vs-Lighthouse guidance: `_aos/lean-kit/modules/validation-quality/docs/BROWSER_QA_HARNESS_CANON_v1.0.0.md`.
- **Cross-engine validation** (required at L-GATE_VALIDATE per Iron Rule #1 — the validator engine must differ from the builder engine): re-verify, independently of the builder's own claims —
  1. Every `character_html(...)` call site (5 total: corner hero, puzzle, discovery, shelf, closer) is immediately followed by `| safe` — the single highest-risk item in this whole WP (§2.2 AC-21, §5).
  2. The deleted `ns.l2_count`/force-even block is fully gone, not merely dead-code-commented-out (AC-11).
  3. `extended-family-panel`'s markup contains zero `<img`/`<video`/`<source`/`background-image` occurrences (AC-43) — mechanically grep-able, zero tolerance.
  4. The `panel-level2-solo` single-wide condition (`loop.index == loop.length and loop.index is odd`) is present verbatim inside the corner's `corner_rest` loop, not accidentally applied to the (deleted) old global grid or omitted entirely.
  5. `settings: Settings = None` is genuinely optional — `render(neo)` with no other args still succeeds (AC-02), i.e. no hidden new required parameter was introduced under a different name.
  6. `git diff` for `src/orchestrator.py` and `src/m3_normalizer.py` (the 2 companion-edit files) touches **only** the exact lines specified in §2.1 points 5–6 — no incidental changes to either file beyond those.
  7. The 10 `box-shadow: ... var(--ink)` → `var(--shadow-color)` substitutions (§2.8 point 3) are complete and exact — no accidental 11th/12th change, no missed one among the 10.

## 8. Consuming team sign-off
> I confirm this spec is executable and unambiguous. All open questions are resolved.
> **Signature:** familynewsletter_build | [PENDING — sign at L-GATE_SPEC]

---

## Cross-Engine Validation — Iron Rule

Documents at LOD400+ require cross-engine validation at L-GATE_VALIDATE.
**The validator engine MUST differ from the builder engine — IRON RULE.**
No exception. No waiver. See `gates/L-GATE_VALIDATE_VALIDATE_AND_LOCK.md`.
