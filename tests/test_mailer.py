"""Tests for the enquiry email module (mailer.py)."""
from email.message import Message

import pytest

import mailer
from mailer import (
    SERVICE_LABELS,
    _build_company_message,
    _build_message,
    _smtp_settings,
    dispatch_enquiry_emails,
    is_configured,
    send_thank_you_sync,
)


@pytest.fixture()
def smtp_env(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test.local")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USER", "test@gvpowers.in")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "secret-password")
    monkeypatch.setenv("MAIL_FROM", "no-reply@gvpowers.in")
    monkeypatch.setenv("MAIL_FROM_NAME", "GV Powers")
    return _smtp_settings()


ENQUIRY = {
    "name": "Ravi Kumar",
    "email": "ravi@example.com",
    "service": "solar",
    "message": "Need a 5 kW rooftop system.",
}


class _FakeSMTP:
    """Captures login/send calls; records the newest instance for assertions."""

    last = None
    all_sent = []  # messages across all SMTP sessions
    port = None
    starttls_called = False

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port
        self.logged_in = None
        self.sent = []
        _FakeSMTP.last = self

    def starttls(self):
        _FakeSMTP.starttls_called = True

    def login(self, user, password):
        self.logged_in = (user, password)

    def send_message(self, msg):
        self.sent.append(msg)
        _FakeSMTP.all_sent.append(msg)

    def quit(self):
        pass


def _extract(payload, content_type):
    """Walk a MIME message and return the decoded body for a content type."""
    stack = [payload]
    while stack:
        part = stack.pop()
        if part.get_content_type() == content_type:
            return part.get_payload(decode=True).decode("utf-8")
        if part.is_multipart():
            stack.extend(part.get_payload())
    return ""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def test_not_configured_when_creds_missing(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "")
    assert is_configured() is False


def test_configured_with_creds(smtp_env):
    assert smtp_env["user"] == "test@gvpowers.in"
    assert is_configured() is True


def test_defaults_host_and_port(monkeypatch):
    for var in ("SMTP_HOST", "SMTP_PORT", "MAIL_FROM", "MAIL_FROM_NAME"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("SMTP_USER", "u@x.com")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "p")
    s = _smtp_settings()
    assert s["host"] == "smtp.gmail.com"
    assert s["port"] == 465
    assert s["from_addr"] == "u@x.com"
    assert s["from_name"] == "GV Powers"


# ---------------------------------------------------------------------------
# Message building
# ---------------------------------------------------------------------------

def test_build_message_headers(smtp_env):
    msg = _build_message("Ravi Kumar", "ravi@example.com", ENQUIRY, smtp_env)
    assert msg["Subject"] == "Thank you for contacting GV Powers"
    assert "GV Powers <no-reply@gvpowers.in>" == msg["From"]
    assert "Ravi Kumar <ravi@example.com>" == msg["To"]
    assert msg["Reply-To"] == "gvpowerssalem@gmail.com"


def test_build_message_has_logo_attachment(smtp_env):
    msg = _build_message("Ravi Kumar", "ravi@example.com", ENQUIRY, smtp_env)
    images = [p for p in msg.walk() if p.get_content_type() == "image/png"]
    assert images, "logo PNG must be attached"
    assert images[0]["Content-ID"] == "<gvpowers-logo>"
    assert len(images[0].get_payload(decode=True)) > 1000


def test_html_contains_details_and_credits(smtp_env):
    msg = _build_message("Ravi Kumar", "ravi@example.com", ENQUIRY, smtp_env)
    html = _extract(msg, "text/html")
    assert "Ravi Kumar" in html
    assert SERVICE_LABELS["solar"] in html
    assert "Need a 5 kW rooftop system." in html
    assert "kamleshvar.online" in html
    assert "techorigin.online" in html
    assert "cid:gvpowers-logo" in html


def test_plain_text_contains_details(smtp_env):
    msg = _build_message("Ravi Kumar", "ravi@example.com", ENQUIRY, smtp_env)
    plain = _extract(msg, "text/plain")
    assert "Thank you for contacting GV Powers" in plain
    assert "Generators" in plain or "solar" in plain.lower()


def test_unknown_service_falls_back(smtp_env):
    enquiry = dict(ENQUIRY, service="mystery")
    msg = _build_message("Ravi Kumar", "ravi@example.com", enquiry, smtp_env)
    html = _extract(msg, "text/html")
    assert "General Enquiry" in html


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------

def test_send_sync_uses_ssl_and_logs_in(monkeypatch, smtp_env):
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", _FakeSMTP)
    assert send_thank_you_sync("Ravi Kumar", "ravi@example.com", ENQUIRY) is True
    fake = _FakeSMTP.last
    assert fake.port == 465
    assert fake.logged_in == ("test@gvpowers.in", "secret-password")
    assert len(fake.sent) == 1


def test_send_sync_starttls_on_587(monkeypatch, smtp_env):
    monkeypatch.setenv("SMTP_PORT", "587")

    class _FakeStartTLS(_FakeSMTP):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)

    monkeypatch.setattr(mailer.smtplib, "SMTP", _FakeStartTLS)
    assert send_thank_you_sync("Ravi Kumar", "ravi@example.com", ENQUIRY) is True
    assert _FakeStartTLS.last.port == 587
    assert len(_FakeStartTLS.last.sent) == 1


def test_send_sync_skips_when_unconfigured(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "")
    assert send_thank_you_sync("Ravi Kumar", "ravi@example.com", ENQUIRY) is False


def test_send_sync_returns_false_on_smtp_error(monkeypatch, smtp_env):
    def _boom(*a, **kw):
        raise ConnectionError("no network")

    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", _boom)
    assert send_thank_you_sync("Ravi Kumar", "ravi@example.com", ENQUIRY) is False


def test_enqueue_runs_inline_under_testing(monkeypatch, smtp_env):
    """In TESTING mode both emails send synchronously (assert-able in tests)."""
    _FakeSMTP.all_sent = []
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", _FakeSMTP)

    class _App:
        config = {"TESTING": True}

    dispatch_enquiry_emails(_App(), "Ravi Kumar", "ravi@example.com", ENQUIRY)
    # 1 company notification + 1 customer thank-you
    assert len(_FakeSMTP.all_sent) == 2


def test_enqueue_spawns_thread_outside_testing(monkeypatch, smtp_env):
    import threading
    import time

    started = threading.Event()
    calls = []

    class _App:
        config = {}

        def app_context(self):
            import contextlib

            return contextlib.nullcontext()

    def _fake_send(name, email, enquiry):
        calls.append(("customer", email))
        started.set()

    def _fake_company(enquiry):
        calls.append(("company", enquiry.get("email")))

    monkeypatch.setattr(mailer, "send_thank_you_sync", _fake_send)
    monkeypatch.setattr(mailer, "send_company_notification_sync", _fake_company)
    dispatch_enquiry_emails(_App(), "Ravi Kumar", "ravi@example.com", ENQUIRY)
    assert started.wait(timeout=5)
    time.sleep(0.05)  # let the daemon thread finish
    assert ("company", "ravi@example.com") in calls
    assert ("customer", "ravi@example.com") in calls


# ---------------------------------------------------------------------------
# Company notification
# ---------------------------------------------------------------------------

def _extract_company(smtp_env, enquiry):
    """Build the company notification and return it plus its plain/html bodies."""
    msg = _build_company_message(enquiry, smtp_env)
    return {
        "msg": msg,
        "plain": _extract(msg, "text/plain"),
        "html": _extract(msg, "text/html"),
    }


def test_company_message_reaches_gv_powers(smtp_env):
    out = _extract_company(smtp_env, ENQUIRY)
    assert out["msg"]["To"] == "gvpowerssalem@gmail.com"
    assert "New website enquiry" in out["msg"]["Subject"]


def test_company_message_reply_to_customer(smtp_env):
    out = _extract_company(smtp_env, ENQUIRY)
    assert out["msg"]["Reply-To"] == "Ravi Kumar <ravi@example.com>"


def test_company_message_contains_lead_details(smtp_env):
    enquiry = dict(ENQUIRY, phone="+91 99887 76655")
    out = _extract_company(smtp_env, enquiry)
    assert "Ravi Kumar" in out["html"]
    assert "ravi@example.com" in out["html"]
    assert "+91 99887 76655" in out["html"]
    assert SERVICE_LABELS["solar"] in out["html"]
    assert "Need a 5 kW rooftop system." in out["plain"]


def test_company_default_recipient(monkeypatch):
    monkeypatch.delenv("COMPANY_NOTIFY_EMAIL", raising=False)
    assert mailer._company_recipient() == "gvpowerssalem@gmail.com"


def test_sent_message_is_valid_mime(smtp_env):
    msg = _build_message("Ravi Kumar", "ravi@example.com", ENQUIRY, smtp_env)
    assert isinstance(msg, Message)
    assert msg.is_multipart()
