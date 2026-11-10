"""Contact form tests: validation, CSRF, honeypot, rate limiting, storage."""
import os
import re
import sqlite3

import pytest


def get_csrf_token(client):
    rv = client.get("/contact")
    html = rv.data.decode()
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "CSRF token not found on contact page"
    return match.group(1)


VALID_PAYLOAD = {
    "name": "Test Customer",
    "email": "customer@example.com",
    "phone": "9876543210",
    "service": "solar",
    "message": "I need a rooftop solar system for my factory in Salem.",
}


def db_rows(app):
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    try:
        return conn.execute("SELECT name, email, phone, service, message FROM enquiries").fetchall()
    finally:
        conn.close()


class TestContactForm:
    def test_valid_submission_stored(self, client, app):
        token = get_csrf_token(client)
        rv = client.post("/contact/send", data={**VALID_PAYLOAD, "csrf_token": token})
        assert rv.status_code == 302
        assert "/contact?sent=1" in rv.headers["Location"]

        rows = db_rows(app)
        assert len(rows) == 1
        assert rows[0][0] == "Test Customer"
        assert rows[0][1] == "customer@example.com"
        assert rows[0][3] == "solar"

    def test_csrf_missing_rejected(self, client, app):
        rv = client.post("/contact/send", data=VALID_PAYLOAD)
        assert rv.status_code == 400
        assert db_rows(app) == []

    def test_csrf_invalid_rejected(self, client, app):
        rv = client.post("/contact/send", data={**VALID_PAYLOAD, "csrf_token": "bad-token"})
        assert rv.status_code == 400
        assert db_rows(app) == []

    def test_honeypot_silent_reject(self, client, app):
        token = get_csrf_token(client)
        rv = client.post("/contact/send", data={
            **VALID_PAYLOAD, "csrf_token": token, "website": "http://spam.example"
        })
        assert rv.status_code == 302  # silently dropped
        assert db_rows(app) == []

    def test_invalid_email_rejected(self, client, app):
        token = get_csrf_token(client)
        rv = client.post("/contact/send", data={
            **VALID_PAYLOAD, "csrf_token": token, "email": "not-an-email"
        })
        assert rv.status_code == 422
        assert b"valid email" in rv.data
        assert db_rows(app) == []

    def test_short_message_rejected(self, client, app):
        token = get_csrf_token(client)
        rv = client.post("/contact/send", data={
            **VALID_PAYLOAD, "csrf_token": token, "message": "hi"
        })
        assert rv.status_code == 422
        assert db_rows(app) == []

    def test_unknown_service_rejected(self, client, app):
        token = get_csrf_token(client)
        rv = client.post("/contact/send", data={
            **VALID_PAYLOAD, "csrf_token": token, "service": "moon-power"
        })
        assert rv.status_code == 422
        assert db_rows(app) == []

    def test_invalid_phone_rejected(self, client, app):
        token = get_csrf_token(client)
        rv = client.post("/contact/send", data={
            **VALID_PAYLOAD, "csrf_token": token, "phone": "call me maybe"
        })
        assert rv.status_code == 422
        assert db_rows(app) == []

    def test_input_sanitised(self, client, app):
        token = get_csrf_token(client)
        rv = client.post("/contact/send", data={
            **VALID_PAYLOAD,
            "csrf_token": token,
            "name": "  Multi   space   name  ",
            "message": "  padded   message  that is long enough to pass  ",
        })
        assert rv.status_code == 302
        rows = db_rows(app)
        assert rows[0][0] == "Multi space name"
        assert rows[0][4].startswith("padded")

    def test_success_page_shows_confirmation(self, client, app):
        token = get_csrf_token(client)
        client.post("/contact/send", data={**VALID_PAYLOAD, "csrf_token": token})
        rv = client.get("/contact?sent=1")
        assert b"Thank you" in rv.data


class TestRateLimiting:
    def test_rate_limit_blocks_after_threshold(self, client, app):
        from routes.contact import rate_limiter
        limit = app.config["ENQUIRY_RATE_LIMIT"]

        token = get_csrf_token(client)
        # Burn through the allowance with invalid submissions (422 still counts)
        for _ in range(limit):
            client.post("/contact/send", data={
                **VALID_PAYLOAD, "csrf_token": token, "message": "too short"
            })
        rv = client.post("/contact/send", data={**VALID_PAYLOAD, "csrf_token": token})
        assert rv.status_code == 429
        rate_limiter.reset()
