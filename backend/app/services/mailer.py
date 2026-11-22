"""Sends password reset links.

With SMTP_HOST set, links are emailed. Without it (local development), the link is
written to the backend log instead, so a developer can copy it from `docker-compose logs
backend`. Do not run without SMTP where other people can read the logs.
"""

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

APP_URL = os.environ.get("APP_URL", "http://localhost:8080").rstrip("/")


def reset_link(token: str) -> str:
    return f"{APP_URL}/account/reset?token={token}"


def send_password_reset(email: str, token: str) -> None:
    link = reset_link(token)
    host = os.environ.get("SMTP_HOST")
    if not host:
        logger.warning("SMTP is not configured. Password reset link for %s: %s", email, link)
        return
    message = EmailMessage()
    message["Subject"] = "Reset your VitalLens password"
    message["From"] = os.environ.get("SMTP_FROM") or "no-reply@localhost"
    message["To"] = email
    message.set_content(
        "Someone asked to reset the password for this account.\n\n"
        f"Open this link within 30 minutes to choose a new password:\n{link}\n\n"
        "If you did not ask for this, ignore this email; your password has not changed."
    )
    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT") or 587), timeout=10) as smtp:
            smtp.starttls()
            username = os.environ.get("SMTP_USERNAME")
            if username:
                smtp.login(username, os.environ.get("SMTP_PASSWORD", ""))
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        # The request already answered the same way for every email, so just record it.
        logger.exception("Could not send the password reset email")
