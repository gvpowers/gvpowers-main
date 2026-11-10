"""Shared pytest fixtures for the GV POWERS test suite."""
import os
import sys

import pytest

# Configure environment BEFORE the app package is imported
TEST_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "instance")
os.environ.setdefault("FLASK_ENV", "development")
os.environ["ADMIN_INITIAL_PASSWORD"] = "test-admin-password-1"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture()
def app(tmp_path, monkeypatch):
    """Create the Flask app pointed at a temporary database."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test_enquiries.db"))
    # Never let unit tests talk to a real SMTP server
    monkeypatch.setenv("SMTP_USER", "")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "")
    # Import here so env vars set above are honoured
    from app import create_app
    from routes import contact as contact_routes

    contact_routes.rate_limiter.reset()

    application = create_app()
    application.config.update(TESTING=True)
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()
