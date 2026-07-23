"""
Family Newsletter — Publisher
FTP upload (index.html + teaser.png) + HTTP-200 verification + email
delivery, per LOD400 FNL-S001-P002-WP006. Replaces src/m5_distributor.py
(archived — §2.13): all Twilio/WhatsApp-direct-send code is removed.
WhatsApp delivery is now a single, family-GROUP-level HOOK for
src/whatsapp.py (WAHA), built by FNL-S001-P003-WP001 (OPS) — NOT this WP.
"""

import ftplib
import logging
import time
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests

from .models import NEO, FamilyConfig, Settings, MemberProfile, FTPUploadError
from .env_compat import (
    ftp_credentials,
    ftp_remote_base,
    newsletter_url_base,
    smtp_config,
    smtp_deliver_message,
)

logger = logging.getLogger('family.publisher')

# WhatsApp hook (§2.4). src/whatsapp.py does not exist yet at this WP's
# authoring time (built later by FNL-S001-P003-WP001). This import is
# deliberately soft (try/except) so publisher.py is fully correct and
# testable standalone today, and auto-activates the moment a conforming
# src/whatsapp.py is dropped in — ZERO further edits to THIS file are
# required for P003 to plug in.
try:
    from . import whatsapp as _whatsapp_module
except ImportError:
    _whatsapp_module = None

# Must match editor.TEASER_LINK_PLACEHOLDER (FNL-S001-P002-WP004 §1
# Assumption 7) EXACTLY. Duplicated here rather than imported across
# sibling modules, matching this codebase's established convention (see
# researcher.py §2.4's identical rationale for duplicating llm.py's JSON
# parsing helpers instead of importing them) — a one-string-constant
# import from editor.py into publisher.py would be a backwards, purely
# cosmetic dependency for zero real benefit.
TEASER_LINK_PLACEHOLDER = "{EDITION_LINK}"

DEFAULT_FTP_HTML_FILENAME = "index.html"
DEFAULT_FTP_TEASER_FILENAME = "teaser.png"


@dataclass
class PublishResult:
    """Returned by publish() (§2.6). Replaces m5_distributor.py's
    DistributionResult. Field-by-field diff from the old shape:
      - public_url: unchanged meaning (the HTML edition's public URL).
      - ftp_success: unchanged meaning (True iff the HTML upload+verify
        succeeded) — kept so orchestrator.cmd_weekly_send's existing
        if result.ftp_success: ... branch needs no logic change, only
        the attribute name on member_results -> email_results (below).
      - teaser_public_url: NEW. None if no teaser_path was given, or its
        upload/verify failed (non-fatal — see publish()'s docstring).
      - email_results: renamed from member_results (WhatsApp is no
        longer a per-member choice in this list — see whatsapp_result).
        Same inner shape: [{member_id, channel, success, error}].
      - whatsapp_result: NEW. A single dict (not a list — WhatsApp is
        now ONE family-group send, not per-member):
        {attempted: bool, success: bool, channel: str, error: Optional[str]}.
    """
    public_url: str
    ftp_success: bool
    teaser_public_url: Optional[str] = None
    email_results: list = field(default_factory=list)
    whatsapp_result: dict = field(default_factory=dict)


# ─── §2.2 FTP layer ──────────────────────────────────────────────────────────

def _ftp_connect(host: str, port: int) -> ftplib.FTP:
    """Unchanged from m5_distributor.py."""
    if port == 21:
        return ftplib.FTP(host, timeout=30)
    ftp = ftplib.FTP()
    ftp.connect(host, port, timeout=30)
    return ftp


def _ftp_mkd_recursive(ftp, path):
    """Unchanged from m5_distributor.py. Create remote directory
    recursively (like mkdir -p)."""
    dirs = path.strip('/').split('/')
    current = ''
    for d in dirs:
        current = f"{current}/{d}"
        try:
            ftp.mkd(current)
        except ftplib.error_perm:
            pass  # directory exists


def ftp_upload_file(local_path: str, remote_filename: str, date: str,
                    settings: Settings) -> str:
    """Same connect/retry/mkdir-recursive logic as m5_distributor.py's
    ftp_upload(), generalized to any remote_filename within the same
    dated directory. Returns the public URL of the uploaded file. Raises
    FTPUploadError only after settings.ftp.retry_count (default 3)
    consecutive connection/login/store failures — a hard, total
    connectivity failure, distinct from "connected fine but the URL
    later 404s," which is _verify_http_200's concern (below)."""
    host, user, passwd, port = ftp_credentials()
    remote_base = ftp_remote_base(settings)
    url_base = newsletter_url_base(settings)
    retry_count = settings.ftp.get('retry_count', 3)
    retry_delay = settings.ftp.get('retry_delay_seconds', 10)

    remote_dir = f"{remote_base}/{date}"
    remote_file = f"{remote_dir}/{remote_filename}"

    for attempt in range(retry_count):
        try:
            ftp = _ftp_connect(host, port)
            ftp.login(user, passwd)
            _ftp_mkd_recursive(ftp, remote_dir)
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_file}', f)
            ftp.quit()

            public_url = f"{url_base}/{date}/{remote_filename}"
            logger.info(f"[publisher] FTP upload success: {public_url}")
            return public_url

        except Exception as e:
            logger.warning(f"[publisher] FTP attempt {attempt+1} failed "
                           f"for {remote_filename}: {e}")
            if attempt < retry_count - 1:
                time.sleep(retry_delay)
            continue

    raise FTPUploadError(
        f"FTP upload of {remote_filename} failed after {retry_count} retries"
    )


def _verify_http_200(url: str, timeout: int = 15) -> tuple:
    """Returns (is_200: bool, status_code: Optional[int]). status_code is
    None only for a network-level exception (DNS/timeout/connection
    refused) — kept distinct from a real non-200 HTTP response for
    clearer logging."""
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.status_code == 200, resp.status_code
    except requests.RequestException as e:
        logger.warning(f"[publisher] HTTP verification request failed for {url}: {e}")
        return False, None


def _upload_and_verify(local_path: str, remote_filename: str, date: str,
                       settings: Settings) -> Optional[str]:
    """FTP upload -> verify HTTP 200 -> on non-200 (or a verification
    request failure), exactly ONE FTP re-upload -> re-verify. Returns the
    public URL on eventual success, or None if it is still not HTTP 200
    after the retry (does NOT raise for this case — a non-200 response is
    a publish-quality problem, not a connectivity problem). Propagates
    FTPUploadError unchanged if ftp_upload_file() itself exhausts its own
    internal connection retries (a hard connectivity failure) — on EITHER
    of the two ftp_upload_file() calls in this function."""
    public_url = ftp_upload_file(local_path, remote_filename, date, settings)
    ok, status = _verify_http_200(public_url)
    if ok:
        return public_url

    logger.warning(f"[publisher] {remote_filename}: HTTP verification "
                   f"returned {status!r} (expected 200) — retrying FTP upload once")
    public_url = ftp_upload_file(local_path, remote_filename, date, settings)
    ok, status = _verify_http_200(public_url)
    if ok:
        return public_url

    logger.error(f"[publisher] {remote_filename}: still not HTTP 200 "
                 f"after 1 retry (last status: {status!r})")
    return None


# ─── §2.3 Email delivery ─────────────────────────────────────────────────────

def _build_message(member: MemberProfile, neo: NEO, public_url: str) -> str:
    """Unchanged from m5_distributor.py."""
    headlines = []
    for section in neo.member_sections:
        if section['member_id'] == member.id:
            for item in section['items'][:3]:
                headlines.append(f"• {item['title']}")
            break
    headlines_text = '\n'.join(headlines) if headlines else "• Check today's edition!"
    if member.language_preference == 'en':
        return (f"Hey {member.nickname_newsletter}! 🌅\n{neo.greeting}\n\n"
                f"📰 Today for you:\n{headlines_text}\n\n👉 Read: {public_url}")
    else:
        return (f"שלום {member.nickname_newsletter}! 🌅\n{neo.greeting}\n\n"
                f"📰 הנה מה שחיכה לך היום:\n{headlines_text}\n\n👉 לקריאה: {public_url}")


def send_email(member: MemberProfile, neo: NEO, public_url: str,
               settings: Settings) -> bool:
    """Unchanged from m5_distributor.py."""
    try:
        cfg = smtp_config()
        if not cfg["host"] or not cfg["password"]:
            return False
        if not member.email:
            return False

        msg_text = _build_message(member, neo, public_url)
        subject = f"📰 הניוזלטר המשפחתי — {neo.date}"

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"Family Newsletter <{cfg['from_addr']}>"
        msg['To'] = member.email
        msg.attach(MIMEText(msg_text, 'plain', 'utf-8'))
        html_body = (f'<html><body dir="rtl" style="font-family: sans-serif;">'
                     f'<p>{msg_text.replace(chr(10), "<br>")}</p></body></html>')
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        smtp_deliver_message(msg)
        logger.info(f"[publisher] Email sent to {member.nickname_newsletter}")
        return True
    except Exception as e:
        logger.error(f"[publisher] Email failed for {member.id}: {e}")
        return False


def _send_email_raw(email: str, subject: str, body: str) -> bool:
    """Unchanged from m5_distributor.py."""
    try:
        cfg = smtp_config()
        if not cfg["host"] or not cfg["password"]:
            return False
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = f"Family Newsletter <{cfg['from_addr']}>"
        msg['To'] = email
        smtp_deliver_message(msg)
        return True
    except Exception:
        return False


def send_survey(family: FamilyConfig, neo: NEO, settings: Settings,
                mock: bool = False) -> list:
    """Kept for CLI-compatibility (weekly-survey verb, module scope B.4).
    NOT part of the automatic Friday 09:00/12:00 flow (REVIVAL_PLAN §3/§4
    schedule only build+send) — this is a manually-triggered, EMAIL-ONLY
    re-send of the survey_question already embedded in the edition. The
    old per-member Twilio WhatsApp send is removed with no replacement:
    the poll question already reaches the family via the main edition's
    WhatsApp GROUP teaser send (§2.6); a future WP may wire a standalone
    re-ping through the same WAHA hook (§2.4) if ever wanted."""
    results = []
    for member in family.members:
        if mock:
            results.append({'member_id': member.id, 'status': 'mock', 'channel': 'mock'})
            continue

        if member.language_preference == 'en':
            msg = (f"📊 Family Newsletter — Weekly Question\n\n"
                   f"{neo.survey_question}\n\n(Reply freely 🙂)")
        else:
            msg = (f"📊 הניוזלטר המשפחתי — שאלת השבוע\n\n"
                   f"{neo.survey_question}\n\n(שלחו תשובה בחופשיות 🙂)")

        success = _send_email_raw(member.email, "📊 Family Newsletter — Weekly Question", msg) \
            if member.email else False

        results.append({
            'member_id': member.id,
            'status': 'sent' if success else 'failed',
            'channel': 'email' if success else 'none',
        })
    return results


# ─── §2.4 WhatsApp WAHA hook ─────────────────────────────────────────────────

def send_whatsapp_teaser(teaser_path: str, caption: str, settings: Settings,
                         mock: bool = False) -> dict:
    """THE WAHA hook. Sends ONE image+caption message to the family
    WhatsApp GROUP.

    CONTRACT for src/whatsapp.py (FNL-S001-P003-WP001, OPS — NOT this WP)
    to satisfy: if present, that module must expose a callable

        send_group_image(image_path: str, caption: str,
                          group_target: dict, settings: Settings,
                          mock: bool = False) -> <dict-or-object>

    returning (at minimum) success/channel/error — either a plain dict
    {'success': bool, 'channel': str, 'error': Optional[str]} or any
    object exposing those 3 as attributes (see _normalize_whatsapp_result
    below — either shape is accepted). group_target is
    {'group_name': str, 'waha_number': str}, sourced from
    settings.distribution.whatsapp_group_name / .whatsapp_number
    (§2.14). This corresponds to WAHA Core's own REST `sendImage`
    endpoint on the implementation side — a detail for P003, opaque here.

    This function is picked up via the soft `from . import whatsapp` at
    the top of this file — P003 needs ZERO edits to publisher.py; dropping
    in a conforming src/whatsapp.py is sufficient. Until it exists, this
    always returns a safe, honestly-labeled 'not implemented yet' result
    — it never raises and never blocks publish()."""
    group_target = {
        'group_name': settings.distribution.get('whatsapp_group_name', 'בית ולד 📰'),
        'waha_number': settings.distribution.get('whatsapp_number', ''),
    }

    if mock:
        logger.info(f"[publisher-MOCK] Would send WhatsApp group image to "
                    f"{group_target['group_name']!r}")
        return {'success': True, 'channel': 'mock', 'error': None}

    if _whatsapp_module is not None and hasattr(_whatsapp_module, 'send_group_image'):
        try:
            raw_result = _whatsapp_module.send_group_image(
                teaser_path, caption, group_target, settings, mock=mock)
            return _normalize_whatsapp_result(raw_result)
        except Exception as e:
            logger.error(f"[publisher] whatsapp.send_group_image() raised: {e}")
            return {'success': False, 'channel': 'whatsapp', 'error': str(e)}

    logger.info(
        f"[publisher] WhatsApp hook stub — src/whatsapp.py not present yet "
        f"(FNL-S001-P003-WP001 pending). Would have sent teaser "
        f"({teaser_path}) + caption to group {group_target['group_name']!r}."
    )
    return {'success': False, 'channel': 'whatsapp_stub',
            'error': 'whatsapp.py not implemented (P003 pending)'}


def _normalize_whatsapp_result(raw) -> dict:
    """Accepts either a dict or an object exposing .success/.channel/.error
    attributes from whatsapp.py's real implementation, normalizing to a
    plain dict — P003's builder is free to return either shape."""
    if isinstance(raw, dict):
        return {'success': bool(raw.get('success', False)),
                'channel': raw.get('channel', 'whatsapp'),
                'error': raw.get('error')}
    return {'success': bool(getattr(raw, 'success', False)),
            'channel': getattr(raw, 'channel', 'whatsapp'),
            'error': getattr(raw, 'error', None)}


# ─── §2.5 Admin escalation ───────────────────────────────────────────────────

def _resolve_admin_email(family: FamilyConfig, settings: Settings) -> Optional[str]:
    """Resolves where operational alerts get emailed.
    settings.distribution.admin_email wins if set (§2.14); else falls
    back to the 'nimrod' member's family.json email; else None (caller
    then only logs — see escalate_admin_alert)."""
    configured = settings.distribution.get('admin_email', '')
    if configured:
        return configured
    for member in family.members:
        if member.id == 'nimrod' and member.email:
            return member.email
    return None


def escalate_admin_alert(subject: str, body: str, family: FamilyConfig,
                         settings: Settings, mock: bool = False) -> bool:
    """Best-effort operational escalation email (budget-cap breach —
    LOD200 §6; teaser-generation failure — orchestrator.cmd_weekly_build,
    §2.11). NEVER raises: a failed escalation attempt must not crash the
    build/send it is trying to report on. Returns True iff the email was
    (or, in mock mode, would have been) sent."""
    if mock:
        logger.info(f"[publisher-MOCK] Would escalate: {subject}")
        return True

    to_addr = _resolve_admin_email(family, settings)
    if not to_addr:
        logger.error(f"[publisher] Cannot escalate '{subject}' — no admin_email "
                     f"configured and no 'nimrod' member email on file")
        return False

    try:
        cfg = smtp_config()
        if not cfg["host"] or not cfg["password"]:
            logger.error(f"[publisher] Cannot escalate '{subject}' — SMTP not configured")
            return False

        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = f"⚠️ Family Newsletter ALERT — {subject}"
        msg['From'] = f"Family Newsletter <{cfg['from_addr']}>"
        msg['To'] = to_addr

        smtp_deliver_message(msg)
        logger.info(f"[publisher] Escalation email sent to {to_addr}: {subject}")
        return True
    except Exception as e:
        logger.error(f"[publisher] Escalation email failed: {e}")
        return False


# ─── §2.6 publish() — main entry point ───────────────────────────────────────

def publish(html_path: str, teaser_path: Optional[str], neo: NEO,
            family: FamilyConfig, settings: Settings,
            mock: bool = False) -> PublishResult:
    """THE public entry point — replaces m5_distributor.distribute().

    Flow: FTP-upload+verify index.html (fatal if it never reaches HTTP
    200 — nothing to link to) -> FTP-upload+verify teaser.png if given
    (degraded/non-fatal on failure — the edition still ships without a
    pretty image) -> email every family member -> WhatsApp group hook
    (§2.4), only attempted if a verified teaser is available (per
    REVIVAL_PLAN §3: image+caption+link is the WhatsApp delivery
    contract; there is nothing meaningful to send without the image)."""
    if mock:
        public_url = f"https://nimrod.bio/agents/newsletter/{neo.date}/index.html"
        teaser_public_url = (f"https://nimrod.bio/agents/newsletter/{neo.date}/teaser.png"
                             if teaser_path else None)
        logger.info(f"[publisher-MOCK] Skipping FTP, URL: {public_url}")
        email_results = [
            {'member_id': m.id, 'channel': 'mock', 'success': True, 'error': None}
            for m in family.members
        ]
        whatsapp_result = send_whatsapp_teaser(teaser_path or '', '', settings, mock=True)
        whatsapp_result = {'attempted': True, **whatsapp_result}
        return PublishResult(public_url=public_url, ftp_success=True,
                             teaser_public_url=teaser_public_url,
                             email_results=email_results,
                             whatsapp_result=whatsapp_result)

    # Step 1: HTML — fatal if it never verifies HTTP 200.
    try:
        public_url = _upload_and_verify(
            html_path, DEFAULT_FTP_HTML_FILENAME, neo.date, settings)
    except FTPUploadError as e:
        logger.critical(f"[publisher] FTP connection failed for "
                        f"{DEFAULT_FTP_HTML_FILENAME}: {e}")
        return PublishResult(
            public_url='', ftp_success=False, teaser_public_url=None,
            email_results=[], whatsapp_result={
                'attempted': False, 'success': False, 'channel': 'none',
                'error': 'ftp_connection_failed',
            })

    if public_url is None:
        logger.critical(f"[publisher] {DEFAULT_FTP_HTML_FILENAME} never "
                        f"verified HTTP 200")
        return PublishResult(
            public_url='', ftp_success=False, teaser_public_url=None,
            email_results=[], whatsapp_result={
                'attempted': False, 'success': False, 'channel': 'none',
                'error': 'html_not_200',
            })

    # Step 2: teaser — degraded, non-fatal.
    teaser_public_url = None
    if teaser_path:
        try:
            teaser_public_url = _upload_and_verify(
                teaser_path, DEFAULT_FTP_TEASER_FILENAME, neo.date, settings)
            if teaser_public_url is None:
                logger.error(f"[publisher] teaser.png never verified HTTP "
                             f"200 — continuing without it")
        except FTPUploadError as e:
            logger.error(f"[publisher] FTP connection failed for "
                         f"teaser.png: {e} — continuing without it")

    # Step 3: email — every member with an address on file.
    email_results = []
    for member in family.members:
        if not member.email:
            email_results.append({'member_id': member.id, 'channel': 'none',
                                  'success': False, 'error': 'No email on file'})
            continue
        success = send_email(member, neo, public_url, settings)
        email_results.append({'member_id': member.id, 'channel': 'email',
                              'success': success,
                              'error': None if success else 'Email send failed'})

    # Step 4: WhatsApp group hook — only if a teaser is actually live.
    if teaser_public_url:
        caption = (neo.metadata.get('teaser_caption', '') or '') \
            .replace(TEASER_LINK_PLACEHOLDER, public_url)
        hook_result = send_whatsapp_teaser(teaser_path, caption, settings, mock=mock)
        whatsapp_result = {'attempted': True, **hook_result}
    else:
        whatsapp_result = {'attempted': False, 'success': False,
                           'channel': 'whatsapp', 'error': 'no_teaser_available'}
        logger.info("[publisher] Skipping WhatsApp hook — no verified "
                    "teaser.png this edition")

    return PublishResult(public_url=public_url, ftp_success=True,
                         teaser_public_url=teaser_public_url,
                         email_results=email_results,
                         whatsapp_result=whatsapp_result)
