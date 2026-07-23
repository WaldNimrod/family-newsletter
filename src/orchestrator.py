"""
Family Newsletter — Orchestrator
CLI entry points per LOD400 §10.
Usage:
    python -m src.orchestrator weekly-build [--mock]
    python -m src.orchestrator weekly-send [--mock]
    python -m src.orchestrator weekly-survey [--mock]
    python -m src.orchestrator health-check
Note: daily-build/send/survey are aliases for backward compatibility.
"""

import argparse
import inspect
import json
import logging
import re
import sys
import os
import time
from datetime import datetime, timezone
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    pass

from src.m1_profiles import load_profiles, load_settings
from src import researcher
from src import editor
from src import teaser
from src import publisher
from src import llm
from src.m4_renderer import render, save_html, CHARACTER_SCHEDULE
from src.db import Database
from src.token_tracker import TokenTracker
from src.env_compat import newsletter_url_base
from src.models import NEO

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger('family')

# ─── Preflight guard (§2.7 / BUILD_DIRECTIVE) ─────────────────────────────────
# Asserts render() accepts `settings=` — catches build-order drift at
# import time, before any real work is done.
_render_sig = inspect.signature(render)
assert 'settings' in _render_sig.parameters, (
    "PREFLIGHT FAIL: render() does not accept a 'settings' parameter. "
    "WP007 (m4_renderer.py) must be built before this orchestrator runs. "
    "This is a build-order guard — DO NOT remove it."
)


# ─── §2.8 Zero-token assembly helpers ────────────────────────────────────────

def _fetch_weather(settings) -> list:
    """Salvaged from m3_normalizer.py, UNCHANGED except LOCATIONS now has
    only Pardes Hanna — Basel removed (module scope item 5; LOD200 §2
    item 4: 'Pardes Hanna ONLY — Basel REMOVED — Shaked home'; confirmed
    by TRANSCRIPT_MINING_2026-07-22.md: 'שקד חזר מבאזל -> הביתה').
    Real Open-Meteo network call, no API key, no --mock branch (Assumption
    14 — unchanged behavior from the salvaged original)."""
    import requests as _req

    LOCATIONS = [
        {'city': 'פרדס חנה', 'city_en': 'Pardes Hanna', 'lat': 32.47, 'lon': 34.97, 'icon': '🏠'},
    ]
    HEB_DAYS = ['ב׳', 'ג׳', 'ד׳', 'ה׳', 'ו׳', 'ש׳', 'א׳']

    weather_data = []
    for loc in LOCATIONS:
        try:
            resp = _req.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    'latitude': loc['lat'], 'longitude': loc['lon'],
                    'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max',
                    'timezone': 'auto', 'forecast_days': 7,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            daily_data = data.get('daily', {})
            dates = daily_data.get('time', [])
            highs = daily_data.get('temperature_2m_max', [])
            lows = daily_data.get('temperature_2m_min', [])
            precip = daily_data.get('precipitation_sum', [])
            wind = daily_data.get('wind_speed_10m_max', [])

            daily_list = []
            for i in range(min(7, len(dates))):
                dt = datetime.strptime(dates[i], '%Y-%m-%d')
                daily_list.append({
                    'date': dates[i], 'day': HEB_DAYS[dt.weekday()],
                    'high': round(highs[i]) if i < len(highs) else 25,
                    'low': round(lows[i]) if i < len(lows) else 15,
                    'precipitation': round(precip[i], 1) if i < len(precip) else 0,
                    'wind_speed': round(wind[i]) if i < len(wind) else 10,
                })

            today_high = round(highs[0]) if highs else 25
            today_precip = precip[0] if precip else 0
            today_wind = wind[0] if wind else 0

            if today_precip > 5:
                w_icon = '🌧️'
            elif today_precip > 0:
                w_icon = '⛅'
            elif today_high > 30:
                w_icon = '☀️'
            elif today_high > 20:
                w_icon = '🌤️'
            else:
                w_icon = '❄️' if today_high < 10 else '🌥️'

            wind_alert = today_wind >= 20
            avg_high = round(sum(highs[:7]) / min(7, len(highs)))
            max_wind = round(max(wind[:7])) if wind else 0
            total_precip = round(sum(precip[:7]), 1)

            summary_parts = [f"ממוצע {avg_high}°"]
            if total_precip > 0:
                summary_parts.append(f"משקעים {total_precip}mm")
            if max_wind >= 20:
                summary_parts.append(f"רוח עד {max_wind} קמ\"ש ⛵")

            weather_data.append({
                'city': loc['city'], 'city_en': loc['city_en'], 'icon': w_icon,
                'temp': f"{today_high}°", 'is_temp': False, 'wind_alert': wind_alert,
                'daily': daily_list, 'description': f"{loc['icon']} {loc['city']}",
                'week_summary': ' | '.join(summary_parts),
            })
            logger.info(f"[orchestrator] Weather fetched: {loc['city_en']} — {today_high}°, wind {today_wind}km/h")
        except Exception as e:
            logger.warning(f"[orchestrator] Weather fetch failed for {loc['city_en']}: {e}")
            continue

    return weather_data


def _format_hebrew_date(today: str) -> str:
    """Salvaged verbatim from m3_normalizer.py — no changes."""
    HEB_DAYS = ['שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת', 'ראשון']
    HEB_MONTHS = ['', 'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
                  'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
    try:
        dt = datetime.strptime(today, '%Y-%m-%d')
        return f"יום {HEB_DAYS[dt.weekday()]}, {dt.day} ב{HEB_MONTHS[dt.month]} {dt.year}"
    except (ValueError, IndexError):
        return today


def _character_metadata() -> dict:
    """Populates neo.metadata['character_emoji']/['character_name']/
    ['character_month'] from m4_renderer.CHARACTER_SCHEDULE. The template
    already reads these 3 keys (cover mascot-name line) via
    .get(key, default) — the OLD m3_normalizer.py never populated them,
    so that line always silently rendered the hardcoded '🎩 Cat in the
    Hat' fallback regardless of the real monthly schedule."""
    current_month = datetime.now(timezone.utc).strftime('%Y-%m')
    meta = CHARACTER_SCHEDULE.get(current_month, {
        'name': 'Character', 'emoji': '🎭', 'style': 'Custom',
    })
    return {
        'character_emoji': meta['emoji'],
        'character_name': meta['name'],
        'character_month': current_month,
    }


# ─── §2.9 Adapter functions ───────────────────────────────────────────────────

_TAG_STRIP_RE = re.compile(r'</?(strong|em)>', re.IGNORECASE)
_SENTENCE_END_RE = re.compile(r'[.!?׃]')


def _short_greeting(opener_html: str, max_len: int = 160) -> str:
    """Assumption 7. Derives a short, plain-text greeting from editor.py's
    full opener HTML — feeds BOTH neo.greeting's real consumers: the
    template's cover mascot-bubble (unconstrained) and teaser.py's small
    speech bubble (WP005 §2.6: max 3 wrapped lines, plain text, no HTML
    tags). Strips the two permitted opener tags (<strong>/<em>), then
    takes the first sentence if it ends within max_len, else a hard
    truncation with a trailing ellipsis. Zero-token, deterministic."""
    text = _TAG_STRIP_RE.sub('', opener_html or '').strip()
    if not text:
        return ''
    m = _SENTENCE_END_RE.search(text)
    if m and m.end() <= max_len:
        return text[:m.end()].strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + '…'


def _map_discovery_bridges(bridges: list, research_results: dict) -> list:
    """Assumption 6. Adapts editor.py's abstract {from_member, to_member,
    text} bridges (WP004 §2.2) onto the UNCHANGED (BACKFILL, kept-as-is)
    Discovery template block's actual required shape — confirmed by
    direct read of templates/newsletter.html.j2 lines 731-744:
    {bridge_text, title, url, summary (optional)}. Anchors each bridge to
    its from_member's own top-ranked researched item (items[0]) — the
    SAME item already shown in that member's Personal Corner, re-
    referenced (not re-selected) as the bridge's clickable target."""
    mapped = []
    for b in bridges:
        source_items = research_results.get(b.get('from_member', ''), [])
        anchor = source_items[0] if source_items else None
        mapped.append({
            'from_member': b.get('from_member', ''),
            'to_member': b.get('to_member', ''),
            'bridge_text': b.get('text', ''),
            'title': anchor['title'] if anchor else (b.get('text', '')[:60] or '...'),
            'url': anchor['url'] if anchor else '#',
            'summary': anchor['summary'] if anchor else '',
        })
    return mapped


def _map_viewing(screen_scout_result: dict) -> dict:
    """Assumption 5. Adapts researcher.screen_scout()'s return shape
    (WP003 §2.14) onto neo.metadata['viewing']'s template contract (WP007
    §2.3/§3). Neither sibling spec defines this mapping — see Assumption
    5 for the full citation trail."""
    def _one(pick, member_id=None):
        if not pick:
            return None
        out = {
            'title': pick.get('title', ''),
            'platform': pick.get('service', ''),
            'hebrew_subs': bool(pick.get('hebrew_subtitles_verified')),
            'available_il': bool(pick.get('availability_verified')),
            'note': pick.get('share_note') or pick.get('availability_note') or '',
        }
        if member_id:
            out['member_id'] = member_id
        return out

    return {
        'family_pick': _one(screen_scout_result.get('family_pick')),
        'personal_pick': _one(
            screen_scout_result.get('personal_pick'),
            member_id=screen_scout_result.get('personal_pick_member_id'),
        ),
    }


def _compute_edition_number(db: Database) -> int:
    """Assumption 8. Duplicates m4_renderer.render()'s own internal
    edition_number query verbatim (that function neither accepts nor
    returns edition_number, and its signature is not changed by this WP
    — see Assumption 8) so orchestrator.py can pass the SAME value to
    teaser.generate_teaser(). Safe by construction: no newsletters row is
    inserted between render()'s internal query and this call within one
    synchronous cmd_weekly_build run."""
    try:
        row = db.conn.execute(
            "SELECT COUNT(*) as cnt FROM newsletters WHERE status != 'build_failed'"
        ).fetchone()
        return row['cnt'] or 1
    except Exception:
        return 1


# ─── §2.10 _build_neo ─────────────────────────────────────────────────────────

def _build_neo(family, settings, today: str, date_formatted: str,
               research_results: dict, screen_scout_result: dict,
               editorial: dict, weather: list) -> NEO:
    """Builds the NEO object the UNCHANGED (BACKFILL) template + this WP's
    own render(..., settings=settings) call expect. member_order matches
    m3_normalizer.py's own hardcoded order (salvaged verbatim — the same
    order the Family Strip / Personal Corners render in, per LOD200 §2)."""
    member_order = ["nimrod", "michal", "shaked", "maayan", "tzlil"]
    member_map = {m.id: m for m in family.members}

    member_sections = []
    for mid in member_order:
        member = member_map.get(mid)
        if not member:
            continue
        lang = "en" if member.language_preference == "en" else "he"
        items = []
        for item in research_results.get(mid, []):
            share_note = item.get('share_note', '')
            summary = item.get('summary', '')
            items.append({
                'title': item.get('title', ''),
                'summary': summary,
                'full_text': f"{summary}\n\n{share_note}".strip(),
                'url': item.get('url', ''),
                'source_name': item.get('source', ''),
                'category': item.get('category', ''),
                'language': lang,
                'image_url': None,  # researcher.py never returns one (WP003 §4 item shape)
                'published_at': None,
            })
        member_sections.append({
            'member_id': mid,
            'member_name': member.nickname_newsletter,
            'member_name_en': member.name_en,
            'language': member.language_preference,
            'items': items,
        })

    discovery = _map_discovery_bridges(editorial.get('discovery_bridges', []), research_results)

    puzzle = editorial.get('puzzle', {})
    puzzle_text = f"{puzzle.get('intro', '')}\n\n{puzzle.get('question', '')}"
    trivia = {
        'puzzle': puzzle_text,
        # Rendered field = LAST week's reveal, never this week's secret — Assumption 3.
        'answer': puzzle.get('last_week_answer_reveal', ''),
        'history': (f"{editorial.get('today_in_history', {}).get('fact', '')} "
                    f"{editorial.get('today_in_history', {}).get('family_idea_callout', '')}").strip(),
    }

    qow = editorial.get('question_of_the_week', {})
    poll_q = qow.get('poll_question', '')
    poll_opts = qow.get('poll_options', [])
    survey_question = f"{poll_q} ({' / '.join(poll_opts)})" if poll_opts else poll_q
    if qow.get('preamble'):
        survey_question = f"{qow['preamble']} {survey_question}".strip()

    greeting = _short_greeting(editorial.get('opener', ''))

    editor_credit_val = editorial.get('editor_credit', '')

    # BUILD_DIRECTIVE: use non-empty "🚧 בהכנה" placeholders for unowned sections
    # so template sections are visible (not silent-empty). WP007 will render these.
    viewing = _map_viewing(screen_scout_result)
    if not viewing.get('family_pick') and not viewing.get('personal_pick'):
        viewing = {'family_pick': {'title': '🚧 בהכנה', 'platform': '', 'hebrew_subs': False, 'available_il': False, 'note': ''},
                   'personal_pick': None}

    metadata = {
        'opener_text': editorial.get('opener', ''),
        'closer_text': editorial.get('closer', ''),
        'weather': weather,
        'teaser_caption': editorial.get('teaser_caption', ''),
        'editor_credit': editor_credit_val,
        'editor_name': editor_credit_val,  # WP007 reads editor_name; set both
        'editors_choice': editorial.get('editors_choice', {}),
        'viewing': viewing,
        'whatsapp_group_link': '',  # WAHA has no public invite link (bot number only)
        'whatsapp_number': settings.distribution.get('whatsapp_number', ''),
        # --- OPEN RECONCILIATION ITEM (Assumption 2, §2.14, §6) ---
        # BUILD_DIRECTIVE: use "🚧 בהכנה" placeholders (non-empty) so
        # sections are visible while producers are pending (team_00 D1).
        'family_table_text': '🚧 בהכנה',
        'extended_family': [
            {
                'headline': '🚧 בהכנה',
                'name': '',
                'relation': '',
                'pointer_text': '',
                'link_url': '',
            }
        ],
        'shelf_pick': {'blurb': '🚧 בהכנה'},
    }
    metadata.update(_character_metadata())

    return NEO(
        date=today,
        family_name=family.family_name,
        greeting=greeting,
        family_content=[],  # Phase B (family-submission webhook ingestion) not active — LOD200 §7; Assumption 12
        member_sections=member_sections,
        discovery=discovery,
        trivia=trivia,
        survey_question=survey_question,
        date_formatted=date_formatted,
        metadata=metadata,
    )


# ─── §2.11 cmd_weekly_build ───────────────────────────────────────────────────

def cmd_weekly_build(args):
    """researcher -> editor -> assemble (no tokens) -> render -> teaser ->
    save + db.update_newsletter -> budget check. Replaces the OLD
    M1->M2->M3->M4 pipeline."""
    logger.info("=" * 60)
    logger.info("WEEKLY BUILD starting")
    logger.info("=" * 60)
    start_time = time.time()

    config_dir = args.config or "config/"
    family = load_profiles(config_dir)
    settings = load_settings(config_dir)
    logger.info(f"Family: {family.family_name} ({len(family.members)} members)")

    db = Database(args.db or "data/family.db")
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # Prior puzzle answer MUST be read BEFORE create_newsletter(today, ...)
    # below, or a same-day re-run would read today's own (incomplete) row
    # instead of last week's (Assumption 4).
    prior_row = db.get_last_newsletter()
    prior_puzzle_answer = None
    if prior_row and prior_row.get('date') != today:
        prior_puzzle_answer = prior_row.get('puzzle_answer') or None

    db.create_newsletter(today, 'building')

    tt = TokenTracker(db, mock=args.mock)
    llm.configure(db, settings.ai, mock=args.mock)  # REQUIRED before editor.generate_editorial() — Assumption 1

    try:
        research_results = researcher.research_all_members(tt, db, family, today)
        screen_scout_result = researcher.screen_scout(tt, db, family, today)

        research_highlights = {
            mid: [item.get('share_note', '') for item in items if item.get('share_note')]
            for mid, items in research_results.items()
        }

        editorial = editor.generate_editorial(
            family, research_highlights, prior_puzzle_answer, today, settings,
            mock=args.mock,
        )
    except (llm.LLMError, editor.EditorSchemaError) as e:
        logger.critical(f"[orchestrator] Editorial generation failed fatally: {e}")
        db.update_newsletter(today, status='build_failed')
        db.close()
        raise

    weather = _fetch_weather(settings)
    date_formatted = _format_hebrew_date(today)

    neo = _build_neo(family, settings, today, date_formatted, research_results,
                     screen_scout_result, editorial, weather)

    html = render(neo, template_path="templates/", db=db, settings=settings)
    html_path = save_html(html, today)

    edition_number = _compute_edition_number(db)
    teaser_path = None
    try:
        teaser_path = teaser.generate_teaser(neo, edition_number=edition_number)
    except teaser.TeaserRenderError as e:
        logger.critical(f"[orchestrator] Teaser generation failed: {e}")
        publisher.escalate_admin_alert(
            "Teaser generation failed", f"{today}: {e}", family, settings, mock=args.mock)

    items_selected = sum(len(v) for v in research_results.values())
    for pick_key in ('family_pick', 'personal_pick'):
        if screen_scout_result.get(pick_key):
            items_selected += 1

    url_base = newsletter_url_base(settings)
    db.update_newsletter(
        today, status='ready', html_path=html_path,
        public_url=f"{url_base}/{today}/index.html",
        greeting=neo.greeting,
        puzzle=neo.trivia.get('puzzle', ''),
        puzzle_answer=editorial['puzzle']['answer'],  # THIS week's raw secret — for next week (Assumption 3)
        survey_question=neo.survey_question,
        items_fetched=items_selected,   # legacy column, repurposed — Assumption 12
        items_selected=items_selected,
        submissions_count=0,            # Phase B not active this edition — Assumption 12
        build_duration_ms=int((time.time() - start_time) * 1000),
        neo_json=neo.to_json(),
    )

    weekly_cost = db.get_daily_cost(today)
    cap = settings.budget.get('weekly_alert_usd', 2.50)
    logger.info(f"BUILD COMPLETE: {today} — HTML {len(html)}B, "
                f"teaser={'yes' if teaser_path else 'no'}, cost=${weekly_cost:.4f}")
    if weekly_cost > cap:
        logger.critical(f"BUDGET BREACH: ${weekly_cost:.4f} exceeds cap ${cap:.2f}")
        publisher.escalate_admin_alert(
            "Weekly budget cap exceeded",
            f"{today}: cost ${weekly_cost:.4f} exceeded cap ${cap:.2f} (LOD200 §6). "
            f"Edition still built; review token_usage.",
            family, settings, mock=args.mock,
        )

    db.close()
    return html_path


# ─── §2.12 cmd_weekly_send / cmd_weekly_survey / cmd_health_check ────────────

def cmd_weekly_send(args):
    """publisher.publish(): FTP index.html+teaser.png -> verify -> email
    -> WhatsApp group hook. Replaces m5_distributor.distribute()."""
    logger.info("=" * 60)
    logger.info("WEEKLY SEND starting")
    logger.info("=" * 60)

    config_dir = args.config or "config/"
    family = load_profiles(config_dir)
    settings = load_settings(config_dir)
    db = Database(args.db or "data/family.db")

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    newsletter = db.get_newsletter(today)
    if not newsletter:
        logger.error(f"No newsletter found for {today}. Run weekly-build first!")
        db.close()
        return
    if newsletter['status'] != 'ready':
        logger.error(f"Newsletter status is '{newsletter['status']}', expected 'ready'")
        db.close()
        return

    html_path = newsletter['html_path']
    neo_json = newsletter.get('neo_json')
    if not neo_json:
        logger.error("No NEO data in newsletter record")
        db.close()
        return

    neo = NEO(**json.loads(neo_json))

    teaser_path_guess = f"data/archive/teasers/{today}.png"
    teaser_path = teaser_path_guess if Path(teaser_path_guess).exists() else None
    if teaser_path is None:
        logger.warning(f"[orchestrator] No teaser found at {teaser_path_guess} — "
                       f"publishing without one")

    result = publisher.publish(html_path, teaser_path, neo, family, settings, mock=args.mock)

    if result.ftp_success:
        db.update_newsletter(today, status='distributed', public_url=result.public_url)
        logger.info(f"DISTRIBUTED: {result.public_url}")
    else:
        db.update_newsletter(today, status='send_failed')
        logger.error("DISTRIBUTION FAILED")

    for r in result.email_results:
        status = "✓" if r['success'] else "✗"
        logger.info(f"  {status} {r['member_id']} via {r['channel']}")

    wa = result.whatsapp_result
    logger.info(f"  WhatsApp: attempted={wa.get('attempted')} success={wa.get('success')} "
                f"channel={wa.get('channel')} error={wa.get('error')}")

    db.close()


def cmd_weekly_survey(args):
    """Kept per module scope B.4 — see publisher.send_survey()'s docstring
    (Assumption 11) for why this is a manually-triggered, email-only
    utility, not part of the automatic Friday flow."""
    logger.info("=" * 60)
    logger.info("WEEKLY SURVEY starting")
    logger.info("=" * 60)

    config_dir = args.config or "config/"
    family = load_profiles(config_dir)
    settings = load_settings(config_dir)
    db = Database(args.db or "data/family.db")

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    newsletter = db.get_newsletter(today)
    if not newsletter or not newsletter.get('neo_json'):
        logger.error(f"No newsletter for {today}")
        db.close()
        return

    neo = NEO(**json.loads(newsletter['neo_json']))
    results = publisher.send_survey(family, neo, settings, mock=args.mock)
    db.update_newsletter(today, status='feedback_collecting')
    for r in results:
        logger.info(f"  Survey → {r['member_id']}: {r['status']} ({r['channel']})")
    db.close()


def cmd_health_check(args):
    """Drops the sources.json check (config/sources.json is archived —
    §2.13); adds a profiles/*.md presence check (researcher.py raises
    TasteProfileMissingError if any are absent — a real, likely deploy-
    time failure mode on a fresh server clone, per REVIVAL_PLAN §4 step
    7's 'clone נקי')."""
    logger.info("HEALTH CHECK")
    config_dir = args.config or "config/"

    family = None
    try:
        family = load_profiles(config_dir)
        logger.info(f"  ✓ family.json: {len(family.members)} members")
    except Exception as e:
        logger.error(f"  ✗ family.json: {e}")

    try:
        load_settings(config_dir)
        logger.info(f"  ✓ settings.json loaded")
    except Exception as e:
        logger.error(f"  ✗ settings.json: {e}")

    if family:
        missing = [m.id for m in family.members
                   if not (Path("profiles") / f"{m.id}.md").exists()]
        if missing:
            logger.error(f"  ✗ profiles/: missing taste profiles for {missing}")
        else:
            logger.info(f"  ✓ profiles/: all {len(family.members)} taste profiles present")

    try:
        db = Database(args.db or "data/family.db")
        last = db.get_last_newsletter()
        logger.info(f"  ✓ DB: last newsletter {last['date']} ({last['status']})" if last
                    else "  ✓ DB: no newsletters yet")
        db.close()
    except Exception as e:
        logger.error(f"  ✗ DB: {e}")

    tmpl_path = Path("templates/newsletter.html.j2")
    logger.info(f"  ✓ Template: {tmpl_path}") if tmpl_path.exists() \
        else logger.error(f"  ✗ Template not found: {tmpl_path}")

    env_path = Path(".env")
    logger.info(f"  ✓ .env exists") if env_path.exists() \
        else logger.warning(f"  ⚠ .env not found (needed for API keys)")

    import shutil
    _, _, free = shutil.disk_usage(".")
    logger.info(f"  ✓ Disk: {free // (1024*1024)}MB free")


def main():
    parser = argparse.ArgumentParser(description='Family Newsletter Orchestrator')
    parser.add_argument('command', choices=[
        'weekly-build', 'weekly-send', 'weekly-survey',
        'daily-build', 'daily-send', 'daily-survey',  # backward compat aliases
        'health-check',
    ])
    parser.add_argument('--mock', action='store_true', help='Use mock data (no external calls)')
    parser.add_argument('--config', default='config/', help='Config directory')
    parser.add_argument('--db', default='data/family.db', help='Database path')

    args = parser.parse_args()

    commands = {
        'weekly-build': cmd_weekly_build,
        'weekly-send': cmd_weekly_send,
        'weekly-survey': cmd_weekly_survey,
        'daily-build': cmd_weekly_build,
        'daily-send': cmd_weekly_send,
        'daily-survey': cmd_weekly_survey,
        'health-check': cmd_health_check,
    }
    commands[args.command](args)


if __name__ == '__main__':
    main()
