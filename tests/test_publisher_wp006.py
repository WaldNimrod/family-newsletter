"""
Tests for src/publisher.py — WP006
Covers §2.1–§2.6 acceptance criteria.
No real FTP, SMTP, or HTTP calls.
"""

import pytest
from unittest.mock import MagicMock, patch, call


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.ftp = {'retry_count': 3, 'retry_delay_seconds': 0}
    s.distribution = {'whatsapp_group_name': 'TestGroup', 'whatsapp_number': '972500000000', 'admin_email': ''}
    return s


@pytest.fixture
def mock_member():
    m = MagicMock()
    m.id = 'nimrod'
    m.nickname_newsletter = 'נימרוד'
    m.email = 'nimrod@example.com'
    m.language_preference = 'he'
    return m


@pytest.fixture
def mock_family(mock_member):
    f = MagicMock()
    f.members = [mock_member]
    return f


@pytest.fixture
def mock_neo():
    n = MagicMock()
    n.date = '2026-07-24'
    n.greeting = 'שלום משפחה!'
    n.survey_question = 'שאלת השבוע?'
    n.member_sections = []
    n.metadata = {'teaser_caption': 'קראו עוד: {EDITION_LINK}'}
    return n


# ─── §2.1 Module foundations ──────────────────────────────────────────────────

def test_import_publisher_no_error():
    import src.publisher as pub
    assert pub is not None


def test_whatsapp_module_is_none_when_absent():
    import src.publisher as pub
    assert pub._whatsapp_module is None


def test_publish_result_requires_public_url_and_ftp_success():
    from src.publisher import PublishResult
    with pytest.raises(TypeError):
        PublishResult()  # missing required fields


def test_publish_result_minimal():
    from src.publisher import PublishResult
    r = PublishResult(public_url='x', ftp_success=True)
    assert r.teaser_public_url is None
    assert r.email_results == []
    assert r.whatsapp_result == {}


def test_teaser_link_placeholder_value():
    from src.publisher import TEASER_LINK_PLACEHOLDER
    assert TEASER_LINK_PLACEHOLDER == "{EDITION_LINK}"


# ─── §2.2 FTP layer ───────────────────────────────────────────────────────────

def test_ftp_upload_file_success(mock_settings):
    import src.publisher as pub
    from unittest.mock import mock_open

    with patch.object(pub, 'ftp_credentials', return_value=('host', 'user', 'pass', 21)), \
         patch.object(pub, 'ftp_remote_base', return_value='/agents/newsletter'), \
         patch.object(pub, 'newsletter_url_base', return_value='https://nimrod.bio/agents/newsletter'), \
         patch('ftplib.FTP') as MockFTP, \
         patch('builtins.open', mock_open(read_data=b'data')):

        mock_ftp = MagicMock()
        MockFTP.return_value = mock_ftp

        url = pub.ftp_upload_file('local.html', 'index.html', '2026-07-24', mock_settings)

    assert url == 'https://nimrod.bio/agents/newsletter/2026-07-24/index.html'


def test_ftp_upload_file_teaser_success(mock_settings):
    import src.publisher as pub
    from unittest.mock import mock_open

    with patch.object(pub, 'ftp_credentials', return_value=('host', 'user', 'pass', 21)), \
         patch.object(pub, 'ftp_remote_base', return_value='/agents/newsletter'), \
         patch.object(pub, 'newsletter_url_base', return_value='https://nimrod.bio/agents/newsletter'), \
         patch('ftplib.FTP') as MockFTP, \
         patch('builtins.open', mock_open(read_data=b'data')):

        mock_ftp = MagicMock()
        MockFTP.return_value = mock_ftp

        url = pub.ftp_upload_file('teaser.png', 'teaser.png', '2026-07-24', mock_settings)

    assert url == 'https://nimrod.bio/agents/newsletter/2026-07-24/teaser.png'


def test_ftp_upload_file_raises_after_retries(mock_settings):
    import src.publisher as pub
    from src.models import FTPUploadError

    mock_settings.ftp = {'retry_count': 3, 'retry_delay_seconds': 0}

    with patch.object(pub, 'ftp_credentials', return_value=('host', 'user', 'pass', 21)), \
         patch.object(pub, 'ftp_remote_base', return_value='/newsletter'), \
         patch.object(pub, 'newsletter_url_base', return_value='https://example.com'), \
         patch('ftplib.FTP', side_effect=Exception("conn fail")), \
         patch('time.sleep') as mock_sleep:

        with pytest.raises(FTPUploadError):
            pub.ftp_upload_file('local.html', 'index.html', '2026-07-24', mock_settings)

        # sleep called retry_count - 1 times (never after the final attempt)
        assert mock_sleep.call_count == 2


def test_verify_http_200_success():
    import src.publisher as pub
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        ok, code = pub._verify_http_200('https://example.com/test')
    assert ok is True
    assert code == 200


def test_verify_http_200_non_200():
    import src.publisher as pub
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 404
        ok, code = pub._verify_http_200('https://example.com/test')
    assert ok is False
    assert code == 404


def test_verify_http_200_network_error():
    import src.publisher as pub
    import requests
    with patch('requests.get', side_effect=requests.ConnectionError("no network")):
        ok, code = pub._verify_http_200('https://example.com/test')
    assert ok is False
    assert code is None


def test_upload_and_verify_first_verify_200(mock_settings):
    import src.publisher as pub

    with patch.object(pub, 'ftp_upload_file', return_value='https://x.com/2026-07-24/index.html') as mock_upload, \
         patch.object(pub, '_verify_http_200', return_value=(True, 200)):

        url = pub._upload_and_verify('local.html', 'index.html', '2026-07-24', mock_settings)

    assert url == 'https://x.com/2026-07-24/index.html'
    assert mock_upload.call_count == 1  # no retry


def test_upload_and_verify_retry_on_503_then_200(mock_settings):
    import src.publisher as pub

    with patch.object(pub, 'ftp_upload_file', return_value='https://x.com/2026-07-24/index.html') as mock_upload, \
         patch.object(pub, '_verify_http_200', side_effect=[(False, 503), (True, 200)]):

        url = pub._upload_and_verify('local.html', 'index.html', '2026-07-24', mock_settings)

    assert url == 'https://x.com/2026-07-24/index.html'
    assert mock_upload.call_count == 2


def test_upload_and_verify_both_non_200_returns_none(mock_settings):
    import src.publisher as pub

    with patch.object(pub, 'ftp_upload_file', return_value='https://x.com/2026-07-24/index.html'), \
         patch.object(pub, '_verify_http_200', side_effect=[(False, 503), (False, 503)]):

        url = pub._upload_and_verify('local.html', 'index.html', '2026-07-24', mock_settings)

    assert url is None


def test_upload_and_verify_second_ftp_raises_propagates(mock_settings):
    import src.publisher as pub
    from src.models import FTPUploadError

    with patch.object(pub, 'ftp_upload_file', side_effect=[
            'https://x.com/2026-07-24/index.html',
            FTPUploadError("conn fail")
        ]), \
         patch.object(pub, '_verify_http_200', side_effect=[(False, 503)]):

        with pytest.raises(FTPUploadError):
            pub._upload_and_verify('local.html', 'index.html', '2026-07-24', mock_settings)


# ─── §2.3 Email delivery ─────────────────────────────────────────────────────

def test_send_email_no_email_returns_false(mock_member, mock_neo, mock_settings):
    import src.publisher as pub
    mock_member.email = None
    with patch.object(pub, 'smtp_deliver_message') as mock_deliver:
        result = pub.send_email(mock_member, mock_neo, 'https://x.com', mock_settings)
    assert result is False
    mock_deliver.assert_not_called()


def test_send_survey_mock_mode(mock_family, mock_neo, mock_settings):
    import src.publisher as pub
    with patch.object(pub, '_send_email_raw') as mock_raw:
        results = pub.send_survey(mock_family, mock_neo, mock_settings, mock=True)
    assert len(results) == len(mock_family.members)
    assert all(r['status'] == 'mock' for r in results)
    mock_raw.assert_not_called()


def test_send_survey_english_message(mock_settings):
    import src.publisher as pub

    member = MagicMock()
    member.id = 'shaked'
    member.language_preference = 'en'
    member.email = 'shaked@example.com'
    family = MagicMock()
    family.members = [member]

    neo = MagicMock()
    neo.survey_question = "What is your favourite food?"

    captured = []

    def capture(email, subject, body):
        captured.append((email, subject, body))
        return True

    with patch.object(pub, '_send_email_raw', side_effect=capture):
        results = pub.send_survey(family, neo, mock_settings, mock=False)

    assert len(captured) == 1
    assert "Weekly Question" in captured[0][1]
    assert "Weekly Question" in captured[0][2]


def test_send_survey_hebrew_message(mock_settings):
    import src.publisher as pub

    member = MagicMock()
    member.id = 'nimrod'
    member.language_preference = 'he'
    member.email = 'nimrod@example.com'
    family = MagicMock()
    family.members = [member]

    neo = MagicMock()
    neo.survey_question = "מה אתם אוהבים?"

    captured = []

    def capture(email, subject, body):
        captured.append(body)
        return True

    with patch.object(pub, '_send_email_raw', side_effect=capture):
        pub.send_survey(family, neo, mock_settings, mock=False)

    assert "שאלת השבוע" in captured[0]


# ─── §2.4 WhatsApp WAHA hook ─────────────────────────────────────────────────

def test_send_whatsapp_teaser_stub_when_module_none(mock_settings):
    import src.publisher as pub
    original = pub._whatsapp_module
    pub._whatsapp_module = None
    try:
        result = pub.send_whatsapp_teaser('teaser.png', 'caption', mock_settings, mock=False)
    finally:
        pub._whatsapp_module = original

    assert result['success'] is False
    assert result['channel'] == 'whatsapp_stub'
    assert 'P003 pending' in (result['error'] or '')


def test_send_whatsapp_teaser_mock_mode_returns_success(mock_settings):
    import src.publisher as pub
    result = pub.send_whatsapp_teaser('teaser.png', 'caption', mock_settings, mock=True)
    assert result['success'] is True
    assert result['channel'] == 'mock'
    assert result['error'] is None


def test_send_whatsapp_teaser_with_module_dict_return(mock_settings):
    import src.publisher as pub

    mock_module = MagicMock()
    mock_module.send_group_image.return_value = {
        'success': True, 'channel': 'whatsapp', 'error': None
    }

    original = pub._whatsapp_module
    pub._whatsapp_module = mock_module
    try:
        result = pub.send_whatsapp_teaser('teaser.png', 'caption', mock_settings, mock=False)
    finally:
        pub._whatsapp_module = original

    assert result['success'] is True
    assert result['channel'] == 'whatsapp'
    assert result['error'] is None


def test_send_whatsapp_teaser_with_object_return(mock_settings):
    import src.publisher as pub

    class FakeResult:
        success = True
        channel = 'whatsapp'
        error = None

    mock_module = MagicMock()
    mock_module.send_group_image.return_value = FakeResult()

    original = pub._whatsapp_module
    pub._whatsapp_module = mock_module
    try:
        result = pub.send_whatsapp_teaser('teaser.png', 'caption', mock_settings, mock=False)
    finally:
        pub._whatsapp_module = original

    assert result['success'] is True
    assert result['channel'] == 'whatsapp'
    assert result['error'] is None


def test_send_whatsapp_teaser_module_raises(mock_settings):
    import src.publisher as pub

    mock_module = MagicMock()
    mock_module.send_group_image.side_effect = RuntimeError("WAHA down")

    original = pub._whatsapp_module
    pub._whatsapp_module = mock_module
    try:
        result = pub.send_whatsapp_teaser('teaser.png', 'caption', mock_settings, mock=False)
    finally:
        pub._whatsapp_module = original

    assert result['success'] is False
    assert result['channel'] == 'whatsapp'
    assert 'WAHA down' in (result['error'] or '')


def test_send_whatsapp_teaser_reads_settings(mock_settings):
    import src.publisher as pub

    mock_settings.distribution = {
        'whatsapp_group_name': 'MyGroup',
        'whatsapp_number': '123456789',
        'admin_email': '',
    }

    mock_module = MagicMock()
    captured_group = {}

    def fake_send(image_path, caption, group_target, settings, mock=False):
        captured_group.update(group_target)
        return {'success': True, 'channel': 'whatsapp', 'error': None}

    mock_module.send_group_image.side_effect = fake_send

    original = pub._whatsapp_module
    pub._whatsapp_module = mock_module
    try:
        pub.send_whatsapp_teaser('t.png', 'cap', mock_settings, mock=False)
    finally:
        pub._whatsapp_module = original

    assert captured_group['group_name'] == 'MyGroup'
    assert captured_group['waha_number'] == '123456789'


# ─── §2.5 Admin escalation ───────────────────────────────────────────────────

def test_resolve_admin_email_uses_settings_first(mock_family, mock_settings):
    import src.publisher as pub
    mock_settings.distribution = {'admin_email': 'admin@example.com'}
    result = pub._resolve_admin_email(mock_family, mock_settings)
    assert result == 'admin@example.com'


def test_resolve_admin_email_falls_back_to_nimrod(mock_settings):
    import src.publisher as pub

    nimrod = MagicMock()
    nimrod.id = 'nimrod'
    nimrod.email = 'n@z.com'
    family = MagicMock()
    family.members = [nimrod]
    mock_settings.distribution = {}

    result = pub._resolve_admin_email(family, mock_settings)
    assert result == 'n@z.com'


def test_resolve_admin_email_no_nimrod_returns_none(mock_settings):
    import src.publisher as pub

    other = MagicMock()
    other.id = 'someone_else'
    other.email = 'x@y.com'
    family = MagicMock()
    family.members = [other]
    mock_settings.distribution = {}

    result = pub._resolve_admin_email(family, mock_settings)
    assert result is None


def test_escalate_admin_alert_mock_returns_true(mock_family, mock_settings):
    import src.publisher as pub
    with patch.object(pub, 'smtp_deliver_message') as mock_deliver:
        result = pub.escalate_admin_alert("Test", "body", mock_family, mock_settings, mock=True)
    assert result is True
    mock_deliver.assert_not_called()


def test_escalate_admin_alert_no_admin_email_returns_false(mock_settings):
    import src.publisher as pub

    family = MagicMock()
    family.members = []
    mock_settings.distribution = {}

    with patch.object(pub, 'smtp_deliver_message') as mock_deliver:
        result = pub.escalate_admin_alert("Alert", "body", family, mock_settings, mock=False)

    assert result is False
    mock_deliver.assert_not_called()


def test_escalate_admin_alert_smtp_raises_returns_false(mock_family, mock_settings):
    import src.publisher as pub

    mock_settings.distribution = {'admin_email': 'admin@x.com'}

    with patch.object(pub, 'smtp_config', return_value={'host': 'smtp', 'password': 'pass', 'from_addr': 'f@x.com'}), \
         patch.object(pub, 'smtp_deliver_message', side_effect=Exception("SMTP error")):
        result = pub.escalate_admin_alert("Alert", "body", mock_family, mock_settings, mock=False)

    assert result is False  # never propagates


def test_escalate_admin_alert_subject_format(mock_settings):
    import src.publisher as pub
    from email.mime.text import MIMEText

    mock_settings.distribution = {'admin_email': 'admin@x.com'}
    captured = []

    def capture_msg(msg):
        captured.append(msg['Subject'])

    with patch.object(pub, 'smtp_config', return_value={'host': 'smtp', 'password': 'pass', 'from_addr': 'f@x.com'}), \
         patch.object(pub, 'smtp_deliver_message', side_effect=capture_msg):
        family = MagicMock()
        family.members = []
        pub.escalate_admin_alert("Weekly budget cap exceeded", "body", family, mock_settings, mock=False)

    assert len(captured) == 1
    assert "Weekly budget cap exceeded" in captured[0]
    assert "⚠️ Family Newsletter ALERT —" in captured[0]


# ─── §2.6 publish() ──────────────────────────────────────────────────────────

def test_publish_mock_mode(mock_family, mock_neo, mock_settings):
    import src.publisher as pub

    result = pub.publish('html.html', 'teaser.png', mock_neo, mock_family, mock_settings, mock=True)

    assert result.ftp_success is True
    assert result.public_url == f"https://nimrod.bio/agents/newsletter/{mock_neo.date}/index.html"
    assert len(result.email_results) == len(mock_family.members)
    assert all(r['channel'] == 'mock' for r in result.email_results)


def test_publish_mock_no_teaser_no_teaser_url(mock_family, mock_neo, mock_settings):
    import src.publisher as pub
    result = pub.publish('html.html', None, mock_neo, mock_family, mock_settings, mock=True)
    assert result.teaser_public_url is None


def test_publish_html_ftp_raises_returns_failure(mock_family, mock_neo, mock_settings):
    import src.publisher as pub
    from src.models import FTPUploadError

    with patch.object(pub, '_upload_and_verify', side_effect=FTPUploadError("conn fail")), \
         patch.object(pub, 'send_email') as mock_email:

        result = pub.publish('html.html', None, mock_neo, mock_family, mock_settings, mock=False)

    assert result.ftp_success is False
    assert result.public_url == ''
    assert result.email_results == []
    mock_email.assert_not_called()


def test_publish_html_never_200_returns_failure(mock_family, mock_neo, mock_settings):
    import src.publisher as pub

    with patch.object(pub, '_upload_and_verify', return_value=None), \
         patch.object(pub, 'send_email') as mock_email:

        result = pub.publish('html.html', None, mock_neo, mock_family, mock_settings, mock=False)

    assert result.ftp_success is False
    assert result.email_results == []
    mock_email.assert_not_called()


def test_publish_teaser_ftp_raises_email_still_sent(mock_family, mock_neo, mock_settings):
    import src.publisher as pub
    from src.models import FTPUploadError

    call_count = {'html': 0, 'teaser': 0}

    def upload_side_effect(local_path, remote_filename, date, settings):
        if remote_filename == 'index.html':
            call_count['html'] += 1
            return 'https://example.com/2026-07-24/index.html'
        else:
            call_count['teaser'] += 1
            raise FTPUploadError("teaser fail")

    with patch.object(pub, '_upload_and_verify', side_effect=upload_side_effect), \
         patch.object(pub, 'send_email', return_value=True) as mock_email:

        result = pub.publish('html.html', 'teaser.png', mock_neo, mock_family, mock_settings, mock=False)

    assert result.ftp_success is True
    assert result.teaser_public_url is None
    assert mock_email.call_count == len(mock_family.members)


def test_publish_no_teaser_whatsapp_not_attempted(mock_family, mock_neo, mock_settings):
    import src.publisher as pub

    with patch.object(pub, '_upload_and_verify', return_value='https://example.com/2026-07-24/index.html'), \
         patch.object(pub, 'send_email', return_value=True), \
         patch.object(pub, 'send_whatsapp_teaser') as mock_wa:

        result = pub.publish('html.html', None, mock_neo, mock_family, mock_settings, mock=False)

    assert result.whatsapp_result.get('attempted') is False
    assert result.whatsapp_result.get('error') == 'no_teaser_available'
    mock_wa.assert_not_called()


def test_publish_teaser_caption_placeholder_replaced(mock_family, mock_settings):
    import src.publisher as pub

    neo = MagicMock()
    neo.date = '2026-07-24'
    neo.member_sections = []
    neo.greeting = 'hi'
    neo.metadata = {'teaser_caption': 'Read here: {EDITION_LINK} and again: {EDITION_LINK}'}

    call_count = {'html': 0, 'teaser': 0}
    captured_caption = []

    def upload_side_effect(local_path, remote_filename, date, settings):
        if remote_filename == 'index.html':
            return 'https://example.com/2026-07-24/index.html'
        return 'https://example.com/2026-07-24/teaser.png'

    def fake_wa(teaser_path, caption, settings, mock=False):
        captured_caption.append(caption)
        return {'success': True, 'channel': 'whatsapp', 'error': None}

    with patch.object(pub, '_upload_and_verify', side_effect=upload_side_effect), \
         patch.object(pub, 'send_email', return_value=True), \
         patch.object(pub, 'send_whatsapp_teaser', side_effect=fake_wa):

        pub.publish('html.html', 'teaser.png', neo, mock_family, mock_settings, mock=False)

    assert len(captured_caption) == 1
    assert 'https://example.com/2026-07-24/index.html' in captured_caption[0]
    assert '{EDITION_LINK}' not in captured_caption[0]


def test_publish_member_no_email_produces_no_email_entry(mock_settings, mock_neo):
    import src.publisher as pub

    member = MagicMock()
    member.id = 'shaked'
    member.email = None
    family = MagicMock()
    family.members = [member]

    with patch.object(pub, '_upload_and_verify', return_value='https://x.com/2026-07-24/index.html'), \
         patch.object(pub, 'send_email') as mock_email:

        result = pub.publish('html.html', None, mock_neo, family, mock_settings, mock=False)

    mock_email.assert_not_called()
    assert result.email_results[0]['success'] is False
    assert result.email_results[0]['error'] == 'No email on file'


def test_no_twilio_in_publisher():
    """AC-12: no Twilio API code in publisher.py (docstring provenance notes are OK)."""
    # Check import lines only — docstring says "all Twilio/...code is removed" which
    # is a provenance note from the spec. We verify no actual import/usage.
    import_lines = [
        line for line in open('/workspace/src/publisher.py').readlines()
        if line.strip().startswith(('import ', 'from '))
    ]
    import_text = '\n'.join(import_lines)
    assert 'twilio' not in import_text.lower(), "Found twilio import in publisher.py"

    # Also verify no client/SDK usage in non-comment non-docstring lines
    non_comment_lines = [
        line for line in open('/workspace/src/publisher.py').readlines()
        if not line.strip().startswith('#') and '"""' not in line and "'''" not in line
        and not line.strip().startswith('"') and not line.strip().startswith("'")
    ]
    code_text = '\n'.join(non_comment_lines)
    assert 'TwilioRestClient' not in code_text
    assert 'twilio.rest' not in code_text
