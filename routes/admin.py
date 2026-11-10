"""Admin dashboard (/admin) — password-only authentication.

Security model:
  - Single administrator row; Werkzeug scrypt password hash in SQLite.
  - Login limited by RateLimiter (per IP), CSRF-protected, no username.
  - Session cookie: HttpOnly, SameSite=Lax, Secure in production, expires.
  - All admin routes require a verified session (server-side check).
  - Uploaded images: png/jpg/webp only, size-limited, safe random filenames.
"""
import os
import secrets

from flask import (
    Blueprint, render_template, request, redirect, url_for, session,
    current_app, flash, abort, jsonify,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import database as db
from security import validate_csrf
from .themes import DEFAULT_THEME, resolve_admin_default

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

SETTINGS_KEYS = ("default_theme",)


def is_admin() -> bool:
    return bool(session.get("admin_verified"))


def admin_required(view):
    def wrapped(*args, **kwargs):
        if not is_admin():
            flash("Please sign in to continue.", "error")
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        limiter = current_app.extensions.get("login_limiter")
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0]
        allow = (
            limiter.allow(f"login:{ip}", current_app.config["ADMIN_RATE_LIMIT"],
                          current_app.config["ADMIN_RATE_WINDOW"])
            if limiter else True
        )
        if not allow:
            return render_template("admin/login.html"), 429
        if not validate_csrf(request.form.get("csrf_token", "")):
            return render_template("admin/login.html", error="Session expired. Try again."), 400

        row = db.get_admin()
        submitted = request.form.get("password", "")
        if row and submitted and check_password_hash(row["password_hash"], submitted):
            session.clear()
            session["admin_verified"] = True
            session.permanent = True
            current_app.permanent_session_lifetime = current_app.config["ADMIN_SESSION_LIFETIME"]
            current_app.logger.warning(  # no password material ever logged
                "Admin signed in from %s", ip
            )
            nxt = request.args.get("next", url_for("admin.dashboard"))
            if not nxt.startswith("/admin"):
                nxt = url_for("admin.dashboard")
            return redirect(nxt)
        return render_template("admin/login.html", error="Incorrect password."), 401
    return render_template("admin/login.html")


@admin_bp.route("/logout", methods=["POST"])
def logout():
    if not validate_csrf(request.form.get("csrf_token", "")):
        abort(400)
    session.clear()
    return redirect(url_for("admin.login"))


@admin_bp.route("/", methods=["GET"], strict_slashes=False)
@admin_required
def dashboard():
    counts = db.get_counts()
    return render_template(
        "admin/dashboard.html",
        counts=counts,
        enquiry_count=db.count_enquiries(),
        projects=db.list_projects(),
        default_theme=resolve_admin_default(db.get_setting("default_theme", DEFAULT_THEME)),
    )


@admin_bp.route("/change-password", methods=["POST"])
@admin_required
def change_password():
    if not validate_csrf(request.form.get("csrf_token", "")):
        abort(400)
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    row = db.get_admin()
    if not row or not check_password_hash(row["password_hash"], current):
        return jsonify(ok=False, error="Current password is incorrect."), 400
    if len(new) < 8:
        return jsonify(ok=False, error="New password must be at least 8 characters."), 400
    db.update_admin_password(generate_password_hash(new, method="scrypt"))
    current_app.logger.info("Admin password changed from %s",
                            request.headers.get("X-Forwarded-For", request.remote_addr))
    return jsonify(ok=True, message="Password updated.")


# ---------------------------------------------------------------------------
# Project locations CRUD
# ---------------------------------------------------------------------------

_INT_FIELDS = {"latitude", "longitude", "is_public"}
_REQUIRED = ("name", "category", "status", "latitude", "longitude")
STATES = [  # India states/UTs used by the admin dropdown (standard list)
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal", "Andaman & Nicobar", "Chandigarh", "Dadra & Nagar Haveli",
    "Delhi", "Jammu & Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]


def parse_coordinates(value, field):
    try:
        num = float(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number")
    lo, hi = (-90, 90) if field == "latitude" else (-180, 180)
    if not (lo <= num <= hi):
        raise ValueError(f"{field} out of range")
    return round(num, 6)


def valid_project_form(form):
    errors = []
    data = {k: (form.get(k) or "").strip() for k in db.PROJECT_FIELDS if k != "is_public"}
    data["is_public"] = 1 if (form.get("is_public") or "1") == "1" else 0
    if len(data["name"]) < 3:
        errors.append("Project name needs at least 3 characters.")
    if data["category"] not in ("solar", "ups", "generators", "other"):
        errors.append("Invalid category.")
    if data["status"] not in ("completed", "ongoing"):
        errors.append("Invalid status.")
    try:
        data["latitude"] = parse_coordinates(form.get("latitude"), "Latitude")
        data["longitude"] = parse_coordinates(form.get("longitude"), "Longitude")
    except ValueError as exc:
        errors.append(str(exc))
    if len(data["description"]) > 500:
        errors.append("Description too long (max 500).")
    if data["installation_date"]:
        try:
            from datetime import date as _d
            _d.fromisoformat(data["installation_date"])
        except ValueError:
            errors.append("Installation date must be YYYY-MM-DD.")
    return data, errors


def save_image(file_storage):
    """Validated image upload → static/images/projects-map/<random>.<ext>."""
    if not file_storage or not file_storage.filename:
        return ""
    allowed = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
    ext = secure_filename(file_storage.filename).rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        raise ValueError("Image must be png, jpg or webp.")
    file_storage.stream.seek(0, os.SEEK_END)
    if file_storage.stream.tell() > 2 * 1024 * 1024:
        raise ValueError("Image larger than 2 MB.")
    file_storage.stream.seek(0)
    folder = os.path.join(current_app.root_path, "static", "images", "projects-map")
    os.makedirs(folder, exist_ok=True)
    filename = f"{secrets.token_hex(8)}.{ext}"
    file_storage.save(os.path.join(folder, filename))
    return f"images/projects-map/{filename}"


@admin_bp.route("/projects", methods=["GET"])
@admin_required
def projects():
    return render_template("admin/projects.html", projects=db.list_projects(), states=STATES)


@admin_bp.route("/api/projects", methods=["POST", "GET"])
@admin_required
def projects_api():
    if request.method == "POST":
        if not (validate_csrf(request.form.get("csrf_token", ""))
                or validate_csrf(request.headers.get("X-CSRF-Token", ""))):
            abort(400)
        data, errors = valid_project_form(request.form)
        if errors:
            return jsonify(ok=False, errors=errors), 422
        try:
            data["image_path"] = save_image(request.files.get("image"))
        except ValueError as exc:
            return jsonify(ok=False, errors=[str(exc)]), 422
        pid = db.insert_project(data)
        return jsonify(ok=True, id=pid, message="Project added.")
    return jsonify(ok=True, projects=[dict(r) for r in db.list_projects()])


@admin_bp.route("/api/projects/<int:pid>", methods=["POST", "DELETE"])
@admin_required
def project_api(pid):
    if not db.get_project(pid):
        return jsonify(ok=False, error="Not found."), 404
    if request.method == "DELETE":
        if not validate_csrf(request.headers.get("X-CSRF-Token", "")):
            abort(400)
        db.delete_project(pid)
        return jsonify(ok=True, message="Project deleted.")
    if not validate_csrf(request.form.get("csrf_token", "")):
        abort(400)
    data, errors = valid_project_form(request.form)
    if errors:
        return jsonify(ok=False, errors=errors), 422
    try:
        image = save_image(request.files.get("image"))
        if image:
            data["image_path"] = image
    except ValueError as exc:
        return jsonify(ok=False, errors=[str(exc)]), 422
    db.update_project(pid, data)
    return jsonify(ok=True, message="Project updated.")


# ---------------------------------------------------------------------------
# Public read-only feed (matches what visitors may know)
# ---------------------------------------------------------------------------

@admin_bp.route("/api/public/projects", methods=["GET"])
def public_projects():
    payload = []
    for row in db.list_projects(public_only=True):
        payload.append({
            "id": row["id"], "name": row["name"], "category": row["category"],
            "status": row["status"], "state": row["state"], "district": row["district"],
            "locality": row["locality"], "latitude": row["latitude"],
            "longitude": row["longitude"], "description": row["description"],
            "installation_date": row["installation_date"], "capacity": row["capacity"],
        })
    return jsonify(payload)


@admin_bp.route("/api/public/counts", methods=["GET"])
def public_counts():
    return jsonify(db.get_counts())


# ---------------------------------------------------------------------------
# Map management
# ---------------------------------------------------------------------------

@admin_bp.route("/map", methods=["GET"])
@admin_required
def map_manager():
    return render_template("admin/map.html", projects=db.list_projects(), states=STATES)


# ---------------------------------------------------------------------------
# Counts management
# ---------------------------------------------------------------------------

@admin_bp.route("/counts", methods=["POST"])
@admin_required
def counts_update():
    if not validate_csrf(request.form.get("csrf_token", "")):
        abort(400)
    action = request.form.get("action", "")
    category = request.form.get("category", "")
    if category not in db.INITIAL_BASELINE:
        abort(400)
    try:
        _ints = {}
        for f in ("baseline_completed", "baseline_ongoing", "adj_completed", "adj_ongoing"):
            raw = request.form.get(f, "").strip()
            _ints[f] = max(0, int(raw)) if raw != "" else None
        completed, ongoing = _ints["baseline_completed"], _ints["baseline_ongoing"]
        adj_completed, adj_ongoing = _ints["adj_completed"], _ints["adj_ongoing"]
    except ValueError:
        abort(400)

    if action == "baseline":
        if completed is None and ongoing is None:
            abort(400)
        row = db.get_db().execute(
            "SELECT completed_base, ongoing_base FROM counts_baseline WHERE category = ?",
            (category,),
        ).fetchone()
        db.set_baseline(
            category,
            completed if completed is not None else row["completed_base"],
            ongoing if ongoing is not None else row["ongoing_base"],
        )
    elif action == "adjust":
        reason = request.form.get("reason", "").strip()
        if not reason:
            flash("Please state a reason for the historical adjustment.", "error")
            return redirect(url_for("admin.dashboard"))
        db.add_adjustment(category, adj_completed or 0, adj_ongoing or 0, reason)
    else:
        abort(400)
    return redirect(url_for("admin.dashboard"))


# ---------------------------------------------------------------------------
# Settings (default theme)
# ---------------------------------------------------------------------------

@admin_bp.route("/settings", methods=["POST"])
@admin_required
def settings_update():
    if not validate_csrf(request.form.get("csrf_token", "")):
        abort(400)
    theme = request.form.get("default_theme", "")
    from routes.themes import canonical_theme
    canonical = canonical_theme(theme)
    if canonical:
        db.set_default_theme(canonical)
    return redirect(url_for("admin.dashboard"))
