"""
Sends an email to the owner whenever a login attempt fails.

PassForge itself does not run its own mail server — it sends through
whatever SMTP account you configure in config.json (copy config.example.json
and fill it in). Gmail, Outlook, Fastmail, a company SMTP relay, or a
transactional service like SendGrid/Mailgun's SMTP endpoint all work the
same way here.

If config.json is missing or incomplete, PassForge does not crash: it logs
the failed attempt locally (see core/db.py's login_attempts table) and
simply skips the email, so the tool is fully usable before you set up
email alerts.
"""

import json
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


@dataclass
class SmtpConfig:
    host: str
    port: int
    username: str
    app_password: str
    use_tls: bool = True


def load_smtp_config() -> Optional[SmtpConfig]:
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text())
        smtp = data.get("smtp", {})
        if not all(smtp.get(k) for k in ("host", "port", "username", "app_password")):
            return None
        return SmtpConfig(
            host=smtp["host"],
            port=int(smtp["port"]),
            username=smtp["username"],
            app_password=smtp["app_password"],
            use_tls=bool(smtp.get("use_tls", True)),
        )
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def send_unauthorized_access_alert(owner_email: str) -> tuple[bool, str]:
    """
    Returns (sent, message). Never raises — callers should not let an email
    failure block the login screen from reporting the wrong-password result.
    """
    config = load_smtp_config()
    if config is None:
        return False, "Email alerts are not configured (see config.example.json)."

    msg = EmailMessage()
    msg["Subject"] = "PassForge security alert: 5 failed login attempts"
    msg["From"] = config.username
    msg["To"] = owner_email
    msg.set_content(
        "Someone just entered your PassForge master password incorrectly 5 times "
        "in a row.\n\nIf this was you, no action is needed — just try again "
        "carefully, or restart the app if you've lost count.\n\nIf you don't "
        "recognize this attempt, make sure your device is secure and "
        "consider changing your master password once you're back in (this "
        "requires knowing the current one, since PassForge never stores it)."
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(config.host, config.port, timeout=10) as server:
            if config.use_tls:
                server.starttls(context=context)
            server.login(config.username, config.app_password)
            server.send_message(msg)
        return True, "Alert email sent."
    except Exception as exc:  # noqa: BLE001 — surfaced to caller, not raised
        return False, f"Could not send alert email: {exc}"
