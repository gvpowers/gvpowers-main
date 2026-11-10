"""SQLite helpers for the GV POWERS website.

Uses the standard library sqlite3 with one connection per request,
stored on the Flask application context.

Tables (migrations are additive — existing data is never destroyed):
  enquiries          — contact-form submissions (existing table, preserved)
  admin              — single password-only administrator (hashed password)
  project            — mapped project locations managed from /admin
  count_adjustment   — manual "historical projects" count adjustments
  counts_baseline    — editable verified baseline (solar 10 completed / 4 ongoing)
  site_settings      — global settings (default theme)
"""
import os
import sqlite3
from datetime import date

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS enquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    service TEXT NOT NULL,
    message TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_enquiries_created_at
    ON enquiries (created_at);

CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('solar','ups','generators','other')),
    status TEXT NOT NULL CHECK (status IN ('completed','ongoing')),
    state TEXT,
    district TEXT,
    locality TEXT,
    latitude REAL NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude REAL NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    description TEXT DEFAULT '',
    installation_date TEXT,
    capacity TEXT,
    image_path TEXT,
    is_public INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_project_category ON project (category);
CREATE INDEX IF NOT EXISTS idx_project_status ON project (status);
CREATE INDEX IF NOT EXISTS idx_project_state ON project (state);

CREATE TABLE IF NOT EXISTS count_adjustment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL CHECK (category IN ('solar','ups','generators','other')),
    completed_adjustment INTEGER NOT NULL DEFAULT 0,
    ongoing_adjustment INTEGER NOT NULL DEFAULT 0,
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS counts_baseline (
    category TEXT PRIMARY KEY CHECK (category IN ('solar','ups','generators','other')),
    completed_base INTEGER NOT NULL DEFAULT 0 CHECK (completed_base >= 0),
    ongoing_base INTEGER NOT NULL DEFAULT 0 CHECK (ongoing_base >= 0)
);

CREATE TABLE IF NOT EXISTS site_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    default_theme TEXT NOT NULL DEFAULT 'swiss-editorial',
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# Initial verified historical baseline. Never reset silently.
INITIAL_BASELINE = {
    "solar": {"completed_base": 10, "ongoing_base": 4},
    "ups": {"completed_base": 0, "ongoing_base": 0},
    "generators": {"completed_base": 0, "ongoing_base": 0},
    "other": {"completed_base": 0, "ongoing_base": 0},
}


def get_db() -> sqlite3.Connection:
    """Return the per-request database connection."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA busy_timeout = 5000")
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(app) -> None:
    """Create/upgrade the database file. Additive migration only."""
    path = app.config["DATABASE_PATH"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    app.logger.info("Initialising database at %s", path)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        # Seed the verified baseline once (never overwrites existing rows).
        for category, base in INITIAL_BASELINE.items():
            conn.execute(
                """INSERT OR IGNORE INTO counts_baseline (category, completed_base, ongoing_base)
                   VALUES (?, ?, ?)""",
                (category, base["completed_base"], base["ongoing_base"]),
            )
        conn.execute("INSERT OR IGNORE INTO site_settings (id) VALUES (1)")
        _migrate_legacy_theme(conn)
        _ensure_admin(conn, app)
        conn.commit()
    finally:
        conn.close()


def _migrate_legacy_theme(conn: sqlite3.Connection) -> None:
    """One-shot rewrite of pre-2026 theme ids stored in site_settings.

    Legacy glass defaults move to the new non-glass default; every other
    legacy id keeps the administrator's chosen look via the canonical map.
    Never touches rows that already hold a current theme id.
    """
    from routes.themes import LEGACY_THEME_MAP, DEFAULT_THEME, canonical_theme

    row = conn.execute("SELECT default_theme FROM site_settings WHERE id = 1").fetchone()
    if row is None:
        return
    stored = row[0]

    if stored is not None and stored in ("sage-glass", "glass-pro"):
        conn.execute(
            "UPDATE site_settings SET default_theme = ?, updated_at = datetime('now') WHERE id = 1",
            (DEFAULT_THEME,),
        )
    elif stored in LEGACY_THEME_MAP:
        conn.execute(
            "UPDATE site_settings SET default_theme = ?, updated_at = datetime('now') WHERE id = 1",
            (canonical_theme(stored),),
        )


def _ensure_admin(conn: sqlite3.Connection, app) -> None:
    """Create the single administrator row from the initial env password.

    The plaintext password is read from ADMIN_INITIAL_PASSWORD (env / .env),
    hashed immediately with Werkzeug's scrypt-compatible pw-hashing and never
    stored in plaintext, logged, or exposed anywhere.
    """
    from werkzeug.security import generate_password_hash

    row = conn.execute("SELECT password_hash FROM admin WHERE id = 1").fetchone()
    if row is not None:
        return
    initial = (app.config.get("ADMIN_INITIAL_PASSWORD") or "").strip()
    if not initial:
        app.logger.warning("ADMIN_INITIAL_PASSWORD not set — using generated placeholder. Set it before first login!")
        import secrets
        initial = secrets.token_urlsafe(24)  # effectively disables login until set
        conn.execute(
            "INSERT INTO admin (id, password_hash) VALUES (1, ?)",
            (generate_password_hash(initial, method="scrypt"),),
        )
        app.logger.warning("Placeholder admin password generated (not printed). Configure ADMIN_INITIAL_PASSWORD and reset via README.")
        return
    conn.execute(
        "INSERT INTO admin (id, password_hash) VALUES (1, ?)",
        (generate_password_hash(initial, method="scrypt"),),
    )
    app.logger.info("Admin account initialised from ADMIN_INITIAL_PASSWORD.")


# ---------------------------------------------------------------------------
# Enquiries (existing behaviour preserved)
# ---------------------------------------------------------------------------

def insert_enquiry(data: dict) -> int:
    """Persist a validated enquiry. Returns the new row id."""
    db = get_db()
    cur = db.execute(
        """
        INSERT INTO enquiries (name, email, phone, service, message, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["name"],
            data["email"],
            data["phone"],
            data["service"],
            data["message"],
            data.get("ip_address"),
            data.get("user_agent"),
        ),
    )
    db.commit()
    return cur.lastrowid


def list_enquiries(limit: int = 200) -> list:
    return get_db().execute(
        "SELECT * FROM enquiries ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()


def count_enquiries() -> int:
    return get_db().execute("SELECT COUNT(*) AS c FROM enquiries").fetchone()["c"]


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

def get_admin() -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM admin WHERE id = 1").fetchone()


def update_admin_password(password_hash: str) -> None:
    db = get_db()
    db.execute(
        """INSERT INTO admin (id, password_hash) VALUES (1, ?)
           ON CONFLICT(id) DO UPDATE SET password_hash = excluded.password_hash,
                                      updated_at = datetime('now')""",
        (password_hash,),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Projects (mapped locations)
# ---------------------------------------------------------------------------

PROJECT_FIELDS = (
    "name", "category", "status", "state", "district", "locality",
    "latitude", "longitude", "description", "installation_date",
    "capacity", "image_path", "is_public",
)


def list_projects(public_only: bool = False) -> list:
    sql = "SELECT * FROM project"
    if public_only:
        sql += " WHERE is_public = 1"
    sql += " ORDER BY id DESC"
    return get_db().execute(sql).fetchall()


def get_project(project_id: int) -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM project WHERE id = ?", (project_id,)).fetchone()


def insert_project(data: dict) -> int:
    db = get_db()
    fields = [f for f in PROJECT_FIELDS if f in data]
    placeholders = ", ".join("?" for _ in fields)
    cur = db.execute(
        f"INSERT INTO project ({', '.join(fields)}) VALUES ({placeholders})",
        [_cast(fields[i], data[fields[i]]) for i in range(len(fields))],
    )
    db.commit()
    return cur.lastrowid


def update_project(project_id: int, data: dict) -> bool:
    fields = [f for f in PROJECT_FIELDS if f in data and f != "id"]
    if not fields:
        return False
    sets = ", ".join(f"{f} = ?" for f in fields) + ", updated_at = datetime('now')"
    params = [_cast(f, data[f]) for f in fields] + [project_id]
    db = get_db()
    cur = db.execute(
        f"UPDATE project SET {sets} WHERE id = ?",
        params,
    )
    db.commit()
    return cur.rowcount > 0


def delete_project(project_id: int) -> bool:
    db = get_db()
    cur = db.execute("DELETE FROM project WHERE id = ?", (project_id,))
    db.commit()
    return cur.rowcount > 0


def _cast(field, value):
    """Coerce validated strings into the right SQLite types."""
    if field in ("latitude", "longitude"):
        return float(value)
    if field == "is_public":
        return 1 if value in (1, "1", True, "true", "on") else 0
    return value


# ---------------------------------------------------------------------------
# Counts (baseline + manual adjustments + mapped records)
# ---------------------------------------------------------------------------

def set_baseline(category: str, completed_base: int, ongoing_base: int) -> None:
    db = get_db()
    db.execute(
        """INSERT INTO counts_baseline (category, completed_base, ongoing_base)
           VALUES (?, ?, ?)
           ON CONFLICT(category) DO UPDATE SET
             completed_base = excluded.completed_base,
             ongoing_base = excluded.ongoing_base""",
        (category, max(0, int(completed_base)), max(0, int(ongoing_base))),
    )
    db.commit()


def add_adjustment(category: str, completed_adj: int, ongoing_adj: int, reason: str) -> None:
    if completed_adj == 0 and ongoing_adj == 0:
        return
    db = get_db()
    db.execute(
        """INSERT INTO count_adjustment (category, completed_adjustment, ongoing_adjustment, reason)
           VALUES (?, ?, ?, ?)""",
        (
            category,
            max(0, int(completed_adj)),
            max(0, int(ongoing_adj)),
            " ".join((reason or "").split())[:300],
        ),
    )
    db.commit()


def list_adjustments() -> list:
    return get_db().execute(
        "SELECT * FROM count_adjustment ORDER BY id DESC LIMIT 100"
    ).fetchall()


def get_counts() -> dict:
    """Merged counts = editable verified baseline + manual adjustments
    + individually mapped project records (each record counted once).

    Returns {category: {completed, ongoing, total}} plus "all" totals."""
    db = get_db()
    counts = {c: {"completed": 0, "ongoing": 0} for c in INITIAL_BASELINE}
    for row in db.execute("SELECT * FROM counts_baseline"):
        counts[row["category"]]["completed"] += row["completed_base"]
        counts[row["category"]]["ongoing"] += row["ongoing_base"]
    for row in db.execute(
        "SELECT category, SUM(completed_adjustment) cs, SUM(ongoing_adjustment) os "
        "FROM count_adjustment GROUP BY category"
    ):
        counts[row["category"]]["completed"] += row["cs"] or 0
        counts[row["category"]]["ongoing"] += row["os"] or 0
    for row in db.execute(
        "SELECT category, status, COUNT(*) c FROM project WHERE is_public = 1 "
        "GROUP BY category, status"
    ):
        counts[row["category"]][row["status"]] += row["c"]
    # totals across categories
    totals = {"completed": 0, "ongoing": 0}
    for value in counts.values():
        totals["completed"] += value["completed"]
        totals["ongoing"] += value["ongoing"]
    totals["total"] = totals["completed"] + totals["ongoing"]
    for value in counts.values():
        value["total"] = value["completed"] + value["ongoing"]
    counts["all"] = totals
    return counts


# ---------------------------------------------------------------------------
# Site settings
# ---------------------------------------------------------------------------

def get_setting(key: str, default: str = "") -> str:
    row = get_db().execute("SELECT * FROM site_settings WHERE id = 1").fetchone()
    return row[key] if row and row[key] else default


def set_default_theme(theme: str) -> None:
    db = get_db()
    db.execute(
        """INSERT INTO site_settings (id, default_theme) VALUES (1, ?)
           ON CONFLICT(id) DO UPDATE SET default_theme = excluded.default_theme,
                                          updated_at = datetime('now')""",
        (theme,),
    )
    db.commit()


def today() -> str:
    return date.today().isoformat()
