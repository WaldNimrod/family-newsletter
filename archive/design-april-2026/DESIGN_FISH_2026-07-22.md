# April 2026 Design Archive — "Fish Worth Fishing"
*Mined 2026-07-22 from this archive + `SVG_MODULE_SPEC.md` (repo root) + current `templates/newsletter.html.j2` / `STYLE_GUIDE.md`. Feeds the LOD400 specs for `teaser.py` (WP005) and the template extension (WP007).*

## 1. Visual identity (canonical, comic style)
**Fonts** (Google): headers/labels/badges = **`Bangers`** (loud comic display); body = **`Patrick Hand`** (handwritten); metadata = system sans 9–12px.
**Palette** (`:root`, identical across comic prototypes + current template):
```
--red #c0392b (maayan)  --blue #2471a3 (nimrod)  --green #27ae60 (michal)
--purple #7d3c98 (shaked)  --yellow #f39c12  --orange #e67e22 (tzlil)
--bg #fdf6e3 (warm cream)  --ink #2c2c2c  --panel-bg #fff
```
Member tint bgs: nimrod `#e6f0fa`, michal `#e6f5ed`, shaked `#ece6f5`, maayan `#fce8ec`, tzlil `#fef3e2`.
**SVG_MODULE_SPEC.md adds a richer, UNWIRED 3-tier token set** — accent shades (nimrod `#1a5276`, michal `#1e8449`, shaked `#6c3483`, maayan `#a93226`, tzlil `#ca6f1e`), shared warm/cool/nature, and **seasonal 3-color palettes** (spring/summer/autumn/winter) never used.
**Comic mechanics:** halftone-dot page bg (`radial-gradient(circle,#e8dcc8 1px,transparent 1px);16px`); bold flat ink borders 4→3→2px; **flat offset shadows, zero blur** (`6px6px0` hero → `4px4px0` feature → `3px3px0` compact); radius 16→12px; cover masthead diagonal red→orange gradient + candy-stripe overlay (Dr. Seuss echo); mascot speech-bubble w/ CSS tail; accordion `togglePanel()`.
**Layout levels (exact CSS):** HERO L1 (1/edition, ≥220px, 4px border, 24px Bangers, member+source+level badges, 90×120 char placeholder); FEATURE L2 (2/row, 3px, 110px img **or mandatory gradient+emoji fallback** `.feat-visual-fallback`, 15px); COMPACT L3 (36×36 icon+title+tag, thinnest, 14px, no image).

## 2. The big fish — SVG hero + mascot system (designed, NEVER built)
`svg-hero-prototype.html` = a fully hand-illustrated **640×380 SVG hero**: sky/sea gradients (Nimrod's blue `#2471a3→#1a5276`), sun, clouds, waves, distant sailboat, red kite `#e74c3c`, jumping fish. Centerpiece **"Skipper Cat"** = Cat-in-the-Hat body (white + `#c0392b` stripes, tall hat) at a wooden ship's wheel `#8B4513`, waving, with an embedded RTL `<text>` speech bubble (greeting/headline/date).
**4 reusable mascot poses tied to section semantics:** Thinking (puzzle), Pointing (discovery), Reading (content), Waving (greeting) — plus **per-category costuming** inside feature cards (hard-hat+T-square cat for Michal architecture; cat in aerial hoop for Yoyo circus). Note in file: character rotates monthly (April Cat-in-the-Hat, May Popeye), structure stays "big hero + small poses".
**`SVG_MODULE_SPEC.md` §-level content (the richest source):**
- 5-member character design brief: נימרוד (beard, skipper cap; wheel/kite/laptop) · מיכל (long hair, work clothes; T-square/plant/berimbau) · שקד (tall, headphones; book/test-tube/Switch) · יויו (sportswear; aerial hoop/trapeze/phone) · צליל (glasses, clever smile; numbers/oven/VR).
- Art-direction one-liner: *"editorial illustration meets comic strip... flat colors, 2–3px bold outlines, rounded forms, minimal halftone... NO photorealism/3D (Quentin Blake meets Hergé)."*
- A topic→scene→character→decoration lookup table (10 rows: sailing→sea+Nimrod+wheel+sails; circus→tent+Yoyo+trapeze+stars; …) — directly reusable for teaser.py per-edition art selection.
Current template has only an empty dashed 90×120 placeholder; `assets/characters/2026-04|05|_placeholder/` are empty (.gitkeep only).

## 3. Lost fish worth reviving (not in current template/STYLE_GUIDE)
1. **SVG hero + mascot poses + costuming** (biggest — §2).
2. **Dark mode** — named a core principle in spec.md, implemented in `design-examples/style-3-magazine.html` via `@media (prefers-color-scheme:dark){:root{…}}`. Zero trace today.
3. **Inline one-tap emoji rating** (😍😊😐👎 as `#rate-N` anchors in footer) — in v1.0.1 + style-1/3/4. Lower-friction than WhatsApp-only survey.
4. **"מהמדף שלנו" (From Our Shelf)** — SVG_MODULE_SPEC §9: 15 real family books (photographed) mapped to members (Anthroposophy/Steiner ×4, sustainability). Raw list survived into family.json `bookshelf`, but the visible section never made STYLE_GUIDE's mandatory list. Revive alongside Viewing/Family-Table.
5. **Editorial techniques** used but never codified: discovery bridges closing with a concrete family-activity prompt (*"אולי רעיון לפרויקט משפחתי?"*); history/trivia paired with a "family idea" callout.
6. **YouTube thumbnail treatment** (`.yt-thumb/.yt-play` red overlay) — if YouTube sources return.
7. **Single wide L2 panel** for an odd leftover item (today's Jinja forces even pairs).

## 4. Chosen direction + lineage
**`newsletter-v3-preview.html` = the winner** — its `<style>` is byte-identical to current `templates/newsletter.html.j2`; canonical branding ("Family Newsletter!"+"בית ולד"), weekly framing, L2 image-or-fallback rule, advanced expandable weather w/ per-day bars, and fixes a `<strong>`-leak bug from v2.
Lineage: `newsletter-comic-prototype` (flat feed, "Dr. Seuss" literal name later corrected to "Cat in the Hat") → `newsletter-v2-levels`/`v2-official-preview` (hierarchy, old branding, a template bug) → **`v3-preview`** → today's template. Abandoned parallel "clean/soft corner" lineage: `newsletter-preview-poc` → `style-1..4` → `mockups/newsletter-mockup` (best specimen `style-4-light-clean`) — cherry-pick items #2/#3/#6 from it.

## 5. Product-spec content worth carrying (spec.md / process-v1.md / style-comparison.html)
- **Editorial-voice A/B test** (style-comparison.html, not preserved elsewhere): 4 voices drafted on identical content — Yedioth-tabloid, Geektime-casual, Calcalist-professional, Simaniya-warm — with tradeoffs (*"סגנון 3 מקצועי אבל עלול להרגיש יבש... סגנון 4 הכי חם אבל הכי פחות עיתון"*). Winners Simaniya (opener/closer) + Calcalist (headlines) codified in STYLE_GUIDE §2; fold the reasoning into editor.py's system prompt.
- Founding thesis (process-v1.md): *"אחרי תקופה, התוכן שנאסף הופך למקור מידע ואפיון בפני עצמו"* — origin of the monthly profile-editor (REVIVAL_PLAN §3.5 L3).
- 3-tier feedback taxonomy: Passive (UTM/read-pixels/scroll beacons/share), Active-light (in-page emoji, WhatsApp 1–4 survey, "more like this"), Active-deep (weekly/monthly/quarterly).
- Well-formed SQLite schema (content_archive, newsletters, newsletter_items w/ click tracking, feedback, member_preferences_log, family_content) — ancestor of current db.py.
- family.json shape ancestor; family-submitted content taxonomy (photo+caption→"מהמשפחה", link+comment, free text→story).
