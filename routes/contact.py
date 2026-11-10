"""Contact page and secure enquiry submission endpoint."""
import re

from flask import Blueprint, render_template, request, redirect, url_for, current_app

from database import insert_enquiry
from mailer import dispatch_enquiry_emails
from security import generate_csrf_token, validate_csrf, RateLimiter
from site_data import SERVICE_CHOICES, COMPANY

contact_bp = Blueprint("contact", __name__)

rate_limiter = RateLimiter()

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[+]?[0-9][0-9\s\-()]{6,19}$")

SERVICES = dict(SERVICE_CHOICES)


def _clean(value: str, limit: int) -> str:
    """Strip and collapse whitespace; hard-limit length."""
    cleaned = " ".join((value or "").split())
    return cleaned[:limit]


@contact_bp.route("/contact/send", methods=["POST"])
def send():
    form = request.form

    # --- Spam protection: honeypot field must stay empty -------------------
    if form.get("website", "").strip():
        current_app.logger.warning("Honeypot triggered from %s", request.remote_addr)
        return redirect(url_for("main.contact", sent="1", _anchor="enquiry"))

    # --- Rate limiting ------------------------------------------------------
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if not rate_limiter.allow(f"enquiry:{ip}",
                             current_app.config["ENQUIRY_RATE_LIMIT"],
                             current_app.config["ENQUIRY_RATE_WINDOW"]):
        current_app.logger.warning("Rate limit exceeded for %s", ip)
        return render_template("contact.html", error="Too many submissions. Please try again later.",
                               form_values={}), 429

    # --- CSRF ---------------------------------------------------------------
    if not validate_csrf(form.get("csrf_token", "")):
        current_app.logger.warning("CSRF failure from %s", ip)
        return render_template("contact.html", error="Your session expired. Please try again.",
                               form_values={}), 400

    # --- Server-side validation --------------------------------------------
    values = {
        "name": _clean(form.get("name", ""), 120),
        "email": _clean(form.get("email", ""), 254).lower(),
        "phone": _clean(form.get("phone", ""), 25),
        "service": _clean(form.get("service", ""), 40),
        "message": _clean(form.get("message", ""), 2000),
    }
    errors = []
    if len(values["name"]) < 2:
        errors.append("Please enter your full name.")
    if not EMAIL_RE.match(values["email"]):
        errors.append("Please enter a valid email address.")
    if not PHONE_RE.match(values["phone"]):
        errors.append("Please enter a valid phone number.")
    if values["service"] not in SERVICES:
        errors.append("Please choose a service.")
    if len(values["message"]) < 10:
        errors.append("Please describe your requirement (at least 10 characters).")

    if errors:
        return render_template("contact.html", errors=errors, form_values=values), 422

    # --- Persist -------------------------------------------------------------
    enquiry_id = insert_enquiry({
        **values,
        "ip_address": ip,
        "user_agent": request.headers.get("User-Agent", "")[:200],
    })
    current_app.logger.info("Enquiry #%s stored from %s", enquiry_id, values["email"])

    # --- Emails to company and customer (background thread, never blocks) ----
    dispatch_enquiry_emails(
        current_app._get_current_object(),
        values["name"],
        values["email"],
        values,
    )

    return redirect(url_for("main.contact", sent="1", _anchor="enquiry"))
