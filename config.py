"""GV POWERS application configuration.

All values can be overridden through environment variables (see .env.example).
Values are evaluated when the config object is created (per app instance),
never hardcoded as secrets in this file.
"""
import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class BaseConfig:
    """Evaluates configuration from the environment on instantiation."""

    def __init__(self):
        self.SITE_URL = os.environ.get("SITE_URL", "https://gvpowers.in").rstrip("/")
        self.CATALOGUE_URL = os.environ.get(
            "CATALOGUE_URL", "https://catalog.gvpowers.in"
        )

        self.SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

        # Database (SQLite, stored inside the project's instance folder)
        self.DATABASE_PATH = os.environ.get(
            "DATABASE_PATH",
            os.path.join(BASE_DIR, "instance", "enquiries.db"),
        )

        # Sessions / cookies
        self.SESSION_COOKIE_HTTPONLY = True
        self.SESSION_COOKIE_SAMESITE = "Lax"
        self.SESSION_COOKIE_SECURE = _bool(os.environ.get("SESSION_COOKIE_SECURE", "false"))
        self.PERMANENT_SESSION_LIFETIME = 60 * 60 * 2  # 2 hours

        # Hard limits
        self.MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB

        # Contact form
        self.ENQUIRY_RATE_LIMIT = int(os.environ.get("ENQUIRY_RATE_LIMIT", "5"))
        self.ENQUIRY_RATE_WINDOW = int(os.environ.get("ENQUIRY_RATE_WINDOW", "900"))

        # Admin (password-only auth). The plaintext initial password lives in
        # the env/.env only; it is hashed into SQLite on first startup.
        self.ADMIN_INITIAL_PASSWORD = os.environ.get("ADMIN_INITIAL_PASSWORD", "")
        self.ADMIN_RATE_LIMIT = int(os.environ.get("ADMIN_RATE_LIMIT", "5"))
        self.ADMIN_RATE_WINDOW = int(os.environ.get("ADMIN_RATE_WINDOW", "600"))
        self.ADMIN_SESSION_LIFETIME = int(os.environ.get("ADMIN_SESSION_LIFETIME", "7200"))

        # Logging
        self.LOG_FILE = os.environ.get("LOG_FILE", "")

        # Debug flag (Flask reads this attribute)
        self.DEBUG = False
        self.TESTING = False
        self.PREFERRED_URL_SCHEME = "https"


class DevelopmentConfig(BaseConfig):
    def __init__(self):
        super().__init__()
        self.DEBUG = True
        self.SESSION_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    def __init__(self):
        super().__init__()
        self.DEBUG = False
        self.SESSION_COOKIE_SECURE = _bool(os.environ.get("SESSION_COOKIE_SECURE", "true"))


def get_config():
    env = os.environ.get("FLASK_ENV", "development").strip().lower()
    return ProductionConfig() if env == "production" else DevelopmentConfig()
