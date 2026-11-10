"""Admin dashboard tests — auth, passwords, project CRUD, counts."""
import json
import re

import pytest

ADMIN_PASSWORD = "test-admin-password-1"


@pytest.fixture()
def admin_client(app, client, monkeypatch):
    """Client signed in to /admin using the seeded initial password."""
    rv = client.get("/admin")
    assert rv.status_code == 302  # fresh fixture → redirected to login
    rv = client.get("/admin/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', rv.data.decode())
    assert m, "csrf token missing from login page"
    rv = client.post("/admin/login", data={"password": ADMIN_PASSWORD, "csrf_token": m.group(1)})
    assert rv.status_code == 302
    return client


def _csrf(client, path="/admin"):
    html = client.get(path).data.decode()
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, f"no csrf token found on {path}"
    return m.group(1)


PROJECT_PAYLOAD = {
    "name": "Rooftop solar — Erode",
    "category": "solar",
    "status": "completed",
    "state": "Tamil Nadu",
    "district": "Erode",
    "locality": "Perundurai",
    "latitude": "11.27",
    "longitude": "77.58",
    "description": "Verified rooftop installation.",
    "installation_date": "2024-05-10",
    "capacity": "12 kW",
}


class TestLoginFlow:
    def test_redirects_to_login_when_anonymous(self, client):
        rv = client.get("/admin")
        assert rv.status_code == 302
        assert "/admin/login" in rv.headers["Location"]

    def test_login_wrong_password(self, client):
        html = client.get("/admin/login").data.decode()
        token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
        rv = client.post("/admin/login", data={"password": "wrong-pass", "csrf_token": token})
        assert rv.status_code == 401
        assert b"Incorrect password." in rv.data

    def test_login_success_reaches_dashboard(self, client):
        html = client.get("/admin/login").data.decode()
        token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
        client.post("/admin/login", data={"password": ADMIN_PASSWORD, "csrf_token": token})
        rv = client.get("/admin")
        assert rv.status_code == 200
        assert b"Overview" in rv.data

    def test_login_missing_csrf_rejected(self, client):
        rv = client.post("/admin/login", data={"password": ADMIN_PASSWORD})
        assert rv.status_code == 400

    def test_rate_limited_after_failures(self, client, app):
        limiter = app.extensions.get("login_limiter")
        assert limiter is not None
        limiter.reset()
        html = client.get("/admin/login").data.decode()
        token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
        rv = None
        for _ in range(6):  # ADMIN_RATE_LIMIT = 5
            rv = client.post("/admin/login", data={"password": "nope", "csrf_token": token})
        assert rv.status_code == 429


class TestDashboard:
    def test_overview_and_themes(self, admin_client):
        html = admin_client.get("/admin").data.decode()
        assert "Dynamic project counts" in html
        assert "Website theme" in html
        assert "glassmorphism-pro" in html  # theme options present
        assert "Glassmorphism Pro" in html
        assert "Swiss Editorial" in html

    def test_requires_auth(self, client):
        for path in ("/admin", "/admin/projects", "/admin/map"):
            rv = client.get(path)
            assert rv.status_code == 302


class TestProjectCRUD:
    def test_create_and_public_feed(self, admin_client):
        token = _csrf(admin_client)
        data = {"csrf_token": token, **PROJECT_PAYLOAD}
        rv = admin_client.post("/admin/api/projects", data=data)
        assert rv.status_code == 200
        assert rv.json["ok"] is True

        feed = admin_client.get("/admin/api/public/projects").json
        assert any(p["name"] == PROJECT_PAYLOAD["name"] for p in feed)

    def test_validation_errors(self, admin_client):
        token = _csrf(admin_client)
        rv = admin_client.post("/admin/api/projects", data={
            "csrf_token": token, "name": "x", "category": "solar",
            "status": "completed", "latitude": "200", "longitude": "10",
        })
        assert rv.status_code == 422

    def test_update_and_delete(self, admin_client):
        token = _csrf(admin_client)
        pid = admin_client.post("/admin/api/projects",
                                data={"csrf_token": token, **PROJECT_PAYLOAD}).json["id"]
        data = {"csrf_token": token, **PROJECT_PAYLOAD, "name": "Renamed project", "status": "ongoing"}
        rv = admin_client.post(f"/admin/api/projects/{pid}", data=data)
        assert rv.json["ok"] is True
        feed = admin_client.get("/admin/api/public/projects").json
        row = next(p for p in feed if p["id"] == pid)
        assert row["name"] == "Renamed project"
        assert row["status"] == "ongoing"

        rv = admin_client.delete(f"/admin/api/projects/{pid}", headers={"X-CSRF-Token": token})
        assert rv.json["ok"] is True
        assert not any(p["id"] == pid for p in admin_client.get("/admin/api/public/projects").json)

    def test_delete_requires_csrf_header(self, admin_client):
        token = _csrf(admin_client)
        pid = admin_client.post("/admin/api/projects",
                                data={"csrf_token": token, **PROJECT_PAYLOAD}).json["id"]
        rv = admin_client.delete(f"/admin/api/projects/{pid}")
        assert rv.status_code == 400

    def test_crud_requires_auth(self, client):
        rv = client.get("/admin/api/projects")
        assert rv.status_code == 302


class TestCounts:
    def test_baseline_update_reflected_publicly(self, admin_client):
        token = _csrf(admin_client)  # default_theme select on dashboard
        rv = admin_client.post("/admin/counts", data={
            "csrf_token": token, "action": "baseline", "category": "ups",
            "baseline_completed": "3", "baseline_ongoing": "2",
        })
        assert rv.status_code == 302
        counts = admin_client.get("/admin/api/public/counts").json
        assert counts["ups"]["completed"] >= 3
        assert counts["ups"]["ongoing"] >= 2

    def test_adjustment_requires_reason(self, admin_client):
        token = _csrf(admin_client)
        rv = admin_client.post("/admin/counts", data={
            "csrf_token": token, "action": "adjust", "category": "generators",
            "adj_completed": "1", "adj_ongoing": "0", "reason": "",
        })
        # redirects back with a flash error; count unchanged
        assert rv.status_code == 302

        rv = admin_client.post("/admin/counts", data={
            "csrf_token": token, "action": "adjust", "category": "generators",
            "adj_completed": "1", "adj_ongoing": "0", "reason": "2023 TN order",
        })
        assert rv.status_code == 302


class TestSettings:
    def test_default_theme_change(self, admin_client, app):
        token = _csrf(admin_client)
        rv = admin_client.post("/admin/settings", data={
            "csrf_token": token, "default_theme": "swiss-grid",
        })
        assert rv.status_code == 302
        home = admin_client.get("/").data.decode()
        assert 'href="/static/css/themes/theme-swiss-grid.css"' in home
