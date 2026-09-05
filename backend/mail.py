"""
backend/mail.py — Email notification for contact-form submissions.

Uses Python's built-in ``smtplib`` + ``email`` to send via Gmail SMTP.
Runs in a background thread so the API response is never delayed.
Failures are logged but never propagate to the caller.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.config import settings

log = logging.getLogger(__name__)


def _build_html(name: str, email: str, service: str, message: str) -> str:
    """Build a clean HTML email body for the contact notification."""
    return f"""\
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
             background: #0a0a0a; color: #fafafa; padding: 32px;">
  <div style="max-width: 560px; margin: 0 auto; background: #111; border: 1px solid rgba(255,255,255,0.06);
              padding: 36px; border-radius: 4px;">
    <h2 style="margin: 0 0 4px; font-size: 18px; color: #e11d48; text-transform: uppercase;
               letter-spacing: 0.1em;">
      New Contact Submission
    </h2>
    <p style="margin: 0 0 28px; font-size: 12px; color: #71717a;">Crimson Nyx Studios</p>

    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
      <tr>
        <td style="padding: 10px 0; color: #71717a; width: 100px; vertical-align: top;">Name</td>
        <td style="padding: 10px 0; color: #fafafa; font-weight: 600;">{name}</td>
      </tr>
      <tr>
        <td style="padding: 10px 0; color: #71717a; vertical-align: top;">Email</td>
        <td style="padding: 10px 0;">
          <a href="mailto:{email}" style="color: #e11d48; text-decoration: none;">{email}</a>
        </td>
      </tr>
      <tr>
        <td style="padding: 10px 0; color: #71717a; vertical-align: top;">Service</td>
        <td style="padding: 10px 0; color: #fafafa;">{service}</td>
      </tr>
      <tr>
        <td style="padding: 10px 0; color: #71717a; vertical-align: top;">Message</td>
        <td style="padding: 10px 0; color: #a1a1aa; line-height: 1.7;
                   white-space: pre-wrap;">{message}</td>
      </tr>
    </table>

    <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 28px 0 16px;">
    <p style="font-size: 11px; color: #52525b; margin: 0;">
      This email was sent automatically from your website's contact form.
    </p>
  </div>
</body>
</html>"""


def _build_plain(name: str, email: str, service: str, message: str) -> str:
    """Build a plain-text fallback for email clients that don't render HTML."""
    return (
        f"New Contact Submission — Crimson Nyx Studios\n"
        f"{'─' * 44}\n\n"
        f"Name:    {name}\n"
        f"Email:   {email}\n"
        f"Service: {service}\n\n"
        f"Message:\n{message}\n"
    )


def _send(name: str, email: str, service: str, message: str) -> None:
    """Synchronous send — intended to run in a daemon thread."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[CNS] New enquiry from {name}"
    msg["From"] = settings.MAIL_USERNAME
    msg["To"] = settings.MAIL_RECIPIENT
    msg["Reply-To"] = email

    msg.attach(MIMEText(_build_plain(name, email, service, message), "plain"))
    msg.attach(MIMEText(_build_html(name, email, service, message), "html"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT, timeout=15) as server:
        server.starttls(context=ctx)
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        server.sendmail(settings.MAIL_USERNAME, [settings.MAIL_RECIPIENT], msg.as_string())

    log.info("Contact email sent to %s (from: %s)", settings.MAIL_RECIPIENT, email)


def send_contact_email(
    *, name: str, email: str, service: str, message: str
) -> None:
    """Fire-and-forget email notification.  Runs in a background thread.

    If mail is disabled (no MAIL_PASSWORD configured) this is a no-op.
    Any SMTP errors are caught and logged — they never surface to the caller.
    """
    if not settings.MAIL_ENABLED:
        log.debug("Mail disabled — skipping contact notification.")
        return

    def _worker() -> None:
        try:
            _send(name, email, service, message)
        except Exception:
            log.exception("Failed to send contact email for %s", email)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
