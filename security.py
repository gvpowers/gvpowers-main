"""Security helpers: CSRF tokens and a lightweight in-memory rate limiter."""
import hmac
import secrets
import threading
import time

from flask import session

_CSRF_SESSION_KEY = "_csrf_token"


def generate_csrf_token() -> str:
    """Return (creating if necessary) the CSRF token for the current session."""
    if _CSRF_SESSION_KEY not in session:
        session[_CSRF_SESSION_KEY] = secrets.token_hex(32)
    return session[_CSRF_SESSION_KEY]


def validate_csrf(submitted: str) -> bool:
    """Constant-time comparison of the submitted token against the session token."""
    expected = session.get(_CSRF_SESSION_KEY, "")
    if not expected or not submitted:
        return False
    return hmac.compare_digest(expected, submitted)


class RateLimiter:
    """Simple thread-safe sliding-window rate limiter (per process)."""

    def __init__(self):
        self._hits = {}
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = [t for t in self._hits.get(key, []) if now - t < window_seconds]
            if len(bucket) >= limit:
                self._hits[key] = bucket
                return False
            bucket.append(now)
            self._hits[key] = bucket
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
