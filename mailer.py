"""Enquiry email flow — sent via Gmail SMTP after a successful enquiry.

Two emails are dispatched for every submitted enquiry:
  1. Company notification — the lead is emailed to GV Powers inline
     (Recipient: COMPANY_NOTIFY_EMAIL, Reply-To: the customer so a reply
     from the company inbox lands straight on the customer.)
  2. Customer thank-you — a branded "we received your enquiry" email.

Configuration comes from environment variables (see .env.example):
    SMTP_HOST          default smtp.gmail.com
    SMTP_PORT          default 465 (SSL)
    SMTP_USER          Gmail address used to send
    SMTP_APP_PASSWORD  Gmail App Password (NOT the account password)
    MAIL_FROM          optional override of the From: address
    COMPANY_NOTIFY_EMAIL  inbox that receives every enquiry lead

If SMTP_USER / SMTP_APP_PASSWORD are not set, emails are skipped gracefully
(the enquiry is still stored; nothing breaks).
"""
import logging
import os
import smtplib
import threading
from datetime import datetime, timezone
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("gvpowers.mailer")

SERVICE_LABELS = {
    "solar": "Solar Energy",
    "ups": "UPS Systems",
    "generators": "Generators",
    "bess": "Battery Energy Storage",
    "amc": "AMC / Service",
    "general": "General Enquiry",
}


def _smtp_settings():
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_APP_PASSWORD", "").strip()
    if not user or not password:
        return None
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.environ.get("SMTP_PORT", "465")),
        "user": user,
        "password": password,
        "from_addr": os.environ.get("MAIL_FROM", user),
        "from_name": os.environ.get("MAIL_FROM_NAME", "GV Powers"),
    }


def _company_recipient():
    return os.environ.get("COMPANY_NOTIFY_EMAIL", "gvpowerssalem@gmail.com").strip()


def is_configured() -> bool:
    return _smtp_settings() is not None


def _logo_path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "static", "images", "branding", "logo-email.png")


def _connect(smtp, port):
    if port == 465:
        server = smtplib.SMTP_SSL(smtp["host"], 465, timeout=20)
    else:
        server = smtplib.SMTP(smtp["host"], port, timeout=20)
        server.starttls()
    return server


def _dispatch_smtp(smtp, msg):
    """Send via the configured SMTP port with one automatic fallback.

    Many hosting providers block the alternate submission port (587) or
    SMTPS (465); if the configured port cannot even be connected to, retry
    once on the other well-known port before giving up. A login or send
    failure on a successfully connected port is NOT retried — that would
    be a credential/message problem, not a network one.
    """
    try:
        server = _connect(smtp, smtp["port"])
    except smtplib.SMTPConnectError as exc:
        fallback = 465 if smtp["port"] != 465 else 587
        logger.warning(
            "SMTP connect failed on %s:%s (%s) — retrying on port %s",
            smtp["host"], smtp["port"], exc, fallback,
        )
        server = _connect(smtp, fallback)
    except (OSError, smtplib.SMTPException) as exc:
        if smtp["port"] in (587, 465):
            fallback = 465 if smtp["port"] != 465 else 587
            logger.warning(
                "SMTP connection failed on %s:%s (%s: %s) — retrying on port %s",
                smtp["host"], smtp["port"], type(exc).__name__, exc, fallback,
            )
            server = _connect(smtp, fallback)
        else:
            raise
    try:
        server.login(smtp["user"], smtp["password"])
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass


def _company_plain(enquiry, service_label, stamp):
    return f"""GV POWERS — New enquiry from the website

Submitted:  {stamp}
Name:       {enquiry.get('name', '')}
Email:      {enquiry.get('email', '')}
Phone:      {enquiry.get('phone', '')}
Service:    {service_label}

Message:
{enquiry.get('message', '')}

This lead was captured on gvpowers.in. Reply directly to this email
or call the customer on the number above.
"""


def _company_html(enquiry, service_label, stamp):
    row = lambda k, v: (
        f'<tr><td style="padding:6px 0;font-size:14px;color:#625F54;">{k}</td>'
        f'<td style="padding:6px 0;font-size:14px;color:#30332B;"><strong>{v}</strong></td></tr>'
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<body style="margin:0;padding:0;background-color:#F5F1EA;font-family:'Segoe UI',Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F5F1EA;padding:32px 12px;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;width:100%;background-color:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 6px 24px rgba(48,51,43,0.10);">
        <tr>
          <td style="padding:24px 40px;background-color:#30332B;">
            <h1 style="margin:0;font-size:20px;color:#F5F1EA;font-family:Georgia,'Times New Roman',serif;">
              New enquiry from gvpowers.in
            </h1>
          </td>
        </tr>
        <tr>
          <td style="padding:28px 40px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                   style="background-color:#F5F1EA;border-radius:10px;padding:18px 22px;">
              {row("Name", enquiry.get('name', ''))}
              {row("Email", f"<a href='mailto:{enquiry.get('email', '')}' style='color:#1B6FE8;text-decoration:none;'>{enquiry.get('email', '')}</a>")}
              {row("Phone", f"<a href='tel:{enquiry.get('phone', '').replace(' ', '')}' style='color:#1B6FE8;text-decoration:none;'>{enquiry.get('phone', '')}</a>")}
              {row("Service", service_label)}
              {row("Submitted", stamp)}
            </table>
            <p style="margin:20px 0 6px 0;font-size:13px;color:#625F54;letter-spacing:.04em;text-transform:uppercase;"><strong>Message</strong></p>
            <p style="margin:0;font-size:15px;line-height:1.7;color:#30332B;background-color:#F5F1EA;border-left:4px solid #A5A79B;border-radius:8px;padding:14px 20px;">
              {enquiry.get('message', '').replace(chr(10), '<br>')}
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:14px 40px 26px 40px;font-size:12px;color:#625F54;">
            Auto-notification from the GV Powers website enquiry form.
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _build_company_message(enquiry, smtp):
    msg = MIMEMultipart("alternative")
    sender = enquiry.get("email", "")
    role = enquiry.get("name", "Customer")
    msg["Subject"] = f"New website enquiry — {SERVICE_LABELS.get(enquiry.get('service'), 'General')} — {role}"
    msg["From"] = f"{smtp['from_name']} <{smtp['from_addr']}>"
    msg["To"] = _company_recipient()
    if sender:
        msg["Reply-To"] = f"{role} <{sender}>"

    stamp = datetime.now(timezone.utc).astimezone().strftime("%d %b %Y, %I:%M %p IST")
    service_label = SERVICE_LABELS.get(enquiry.get("service"), "General Enquiry")
    msg.attach(MIMEText(_company_plain(enquiry, service_label, stamp), "plain", "utf-8"))
    msg.attach(MIMEText(_company_html(enquiry, service_label, stamp), "html", "utf-8"))
    return msg


def send_company_notification_sync(enquiry: dict) -> bool:
    """Email the enquiry lead to the GV Powers inbox synchronously."""
    smtp = _smtp_settings()
    if not smtp:
        logger.info("SMTP not configured — skipping company notification email")
        return False
    try:
        msg = _build_company_message(enquiry, smtp)
        _dispatch_smtp(smtp, msg)
        logger.info("Company notification sent for enquiry from %s", enquiry.get("email"))
        return True
    except Exception:
        logger.exception("Failed to send company notification for %s", enquiry.get("email"))
        return False


def _build_message(to_name, to_email, enquiry, smtp):
    msg = MIMEMultipart("related")
    msg["Subject"] = "Thank you for contacting GV Powers"
    msg["From"] = f"{smtp['from_name']} <{smtp['from_addr']}>"
    msg["To"] = f"{to_name} <{to_email}>"
    msg["Reply-To"] = "gvpowerssalem@gmail.com"

    alt = MIMEMultipart("alternative")
    msg.attach(alt)

    service_label = SERVICE_LABELS.get(enquiry.get("service"), "General Enquiry")
    alt.attach(MIMEText(_plain_text(to_name, enquiry, service_label), "plain", "utf-8"))
    alt.attach(MIMEText(_html_text(to_name, enquiry, service_label), "html", "utf-8"))

    logo_path = _logo_path()
    if os.path.isfile(logo_path):
        with open(logo_path, "rb") as f:
            logo = MIMEImage(f.read())
        logo.add_header("Content-ID", "<gvpowers-logo>")
        logo.add_header("Content-Disposition", "inline", filename="gvpowers-logo.png")
        msg.attach(logo)

    return msg


def _plain_text(name, enquiry, service_label):
    return f"""GV POWERS — Powering A Better Tomorrow

Dear {name},

Thank you for contacting GV Powers! We have received your enquiry and our
engineering team will get back to you shortly.

Your enquiry details:
  Service:  {service_label}
  Message:  {enquiry.get('message', '')}

Need something urgent? Call us:
  +91 98940 79090  |  +91 98940 79095
  (Working hours: 9:00 AM - 9:00 PM)

Email: gvpowerssalem@gmail.com
Catalogue: https://catalog.gvpowers.in
Serving Chennai & Salem, Tamil Nadu.

Warm regards,
Team GV Powers
Established 1997

---
Developed by GV Kamleshvar (kamleshvar.online) · TechOrigin (techorigin.online)
"""


def _html_text(name, enquiry, service_label):
    message = enquiry.get("message", "")
    return f"""<!DOCTYPE html>
<html lang="en">
<body style="margin:0;padding:0;background-color:#F5F1EA;font-family:'Segoe UI',Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F5F1EA;padding:32px 12px;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;width:100%;background-color:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 6px 24px rgba(48,51,43,0.10);">
        <tr>
          <td style="padding:28px 40px 20px 40px;border-bottom:1px solid #F3E6D5;" align="center">
            <img src="cid:gvpowers-logo" alt="GV Powers — Powering A Better Tomorrow"
                 width="320" style="display:block;width:320px;max-width:100%;height:auto;border:0;">
          </td>
        </tr>
        <tr>
          <td style="padding:32px 40px 8px 40px;">
            <h1 style="margin:0 0 16px 0;font-size:26px;color:#30332B;font-family:Georgia,'Times New Roman',serif;">
              Thank you for contacting us, {name}!
            </h1>
            <p style="margin:0 0 18px 0;font-size:15px;line-height:1.7;color:#625F54;">
              We have received your enquiry and our engineering team will get back to you shortly.
              For urgent requirements, call us directly — we answer from 9:00&nbsp;AM to 9:00&nbsp;PM.
            </p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                   style="background-color:#F5F1EA;border-left:4px solid #A5A79B;border-radius:8px;margin-bottom:22px;">
              <tr><td style="padding:16px 20px;">
                <p style="margin:0 0 6px 0;font-size:13px;color:#30332B;">
                  <strong>Service interested in:</strong> {service_label}
                </p>
                <p style="margin:0;font-size:13px;color:#625F54;">
                  <strong>Your message:</strong> {message}
                </p>
              </td></tr>
            </table>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:8px;">
              <tr>
                <td style="padding:8px 0;font-size:14px;color:#30332B;">
                  <strong>&#128222; Call:</strong>&nbsp;
                  <a href="tel:+919894079090" style="color:#1B6FE8;text-decoration:none;">+91 98940 79090</a> &nbsp;·&nbsp;
                  <a href="tel:+919894079095" style="color:#1B6FE8;text-decoration:none;">+91 98940 79095</a>
                </td>
              </tr>
              <tr>
                <td style="padding:8px 0;font-size:14px;color:#30332B;">
                  <strong>&#99903; Email:</strong>&nbsp;
                  <a href="mailto:gvpowerssalem@gmail.com" style="color:#1B6FE8;text-decoration:none;">gvpowerssalem@gmail.com</a>
                </td>
              </tr>
              <tr>
                <td style="padding:8px 0;font-size:14px;color:#30332B;">
                  <strong>&#128231; WhatsApp:</strong>&nbsp;
                  <a href="https://wa.me/919894079090" style="color:#1B6FE8;text-decoration:none;">Message us on WhatsApp</a>
                </td>
              </tr>
              <tr>
                <td style="padding:8px 0;font-size:14px;color:#30332B;">
                  <strong>&#128267; Catalogue:</strong>&nbsp;
                  <a href="https://catalog.gvpowers.in" style="color:#1B6FE8;text-decoration:none;">catalog.gvpowers.in</a>
                </td>
              </tr>
              <tr>
                <td style="padding:8px 0;font-size:14px;color:#30332B;">
                  <strong>&#128205; Locations:</strong> Chennai &amp; Salem, Tamil Nadu &nbsp;·&nbsp; <strong>&#128336; Hours:</strong> 9 AM – 9 PM
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding:20px 40px 30px 40px;">
            <p style="margin:0;font-size:15px;color:#30332B;">Warm regards,<br>
               <strong style="font-family:Georgia,serif;font-size:17px;">Team GV Powers</strong><br>
               <span style="font-size:13px;color:#625F54;">Established 1997 · Powering A Better Tomorrow</span></p>
          </td>
        </tr>
        <tr>
          <td style="padding:16px 40px;background-color:#E8D2B5;text-align:center;">
            <p style="margin:0;font-size:12px;color:#30332B;">
              © 2026 GV Powers. All rights reserved. ·
              Developed by <a href="https://kamleshvar.online" style="color:#1B6FE8;text-decoration:none;">GV Kamleshvar</a>
              · <a href="https://techorigin.online" style="color:#1B6FE8;text-decoration:none;">TechOrigin</a>
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_thank_you_sync(to_name: str, to_email: str, enquiry: dict) -> bool:
    """Send the thank-you email synchronously. Returns True if sent."""
    smtp = _smtp_settings()
    if not smtp:
        logger.info("SMTP not configured — skipping thank-you email to %s", to_email)
        return False

    try:
        msg = _build_message(to_name, to_email, enquiry, smtp)
        _dispatch_smtp(smtp, msg)
        logger.info("Thank-you email sent to %s", to_email)
        return True
    except Exception:
        logger.exception("Failed to send thank-you email to %s", to_email)
        return False


def dispatch_enquiry_emails(app, to_name: str, to_email: str, enquiry: dict) -> None:
    """Send BOTH emails in a background thread; never blocks or breaks the request.

      1. company notification (the lead, to the GV Powers inbox)
      2. customer thank-you
    """
    if app.config.get("TESTING"):
        send_company_notification_sync(enquiry)
        send_thank_you_sync(to_name, to_email, enquiry)
        return

    def _worker():
        with app.app_context():
            send_company_notification_sync(enquiry)
            send_thank_you_sync(to_name, to_email, enquiry)

    threading.Thread(target=_worker, name="enquiry-emails", daemon=True).start()
