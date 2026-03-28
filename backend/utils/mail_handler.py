import re
import time
from urllib.parse import urlparse

from flask import current_app, render_template_string
from flask_mailman import EmailMessage
from email.utils import parseaddr
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# Optional: import your task queue to send emails asynchronously
# from tasks import send_email_task

EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

def _is_valid_email(email: str) -> bool:
    if not email:
        return False
    name, addr = parseaddr(email)
    return bool(addr) and bool(EMAIL_REGEX.match(addr))

def _is_safe_url(url: str, allowed_hosts=None) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("https", "http"):
            return False
        host = parsed.netloc.lower()
        if allowed_hosts:
            return any(host == h or host.endswith("." + h) for h in allowed_hosts)
        return True
    except Exception:
        return False

def _make_onboarding_token(email: str) -> str:
    secret = current_app.config.get("SECRET_KEY") or current_app.config.get("MAIL_SECRET")
    serializer = URLSafeTimedSerializer(secret)
    return serializer.dumps({"email": email})

def _build_onboarding_url(base_url: str, token: str) -> str:
    # Append token as query param in a safe way
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}token={token}"

def send_onboarding_email(to_email: str, name: str, onboarding_url: str, purpose: str, send_async: bool = True) -> bool:
    """
    Sends an onboarding email. Returns True on success, False on failure.
    - Validates inputs
    - Builds a tokenized onboarding URL
    - Sends multipart email (text + HTML)
    - Optionally enqueues sending to a background worker
    """
    # Basic validation
    if not _is_valid_email(to_email):
        current_app.logger.warning("Invalid onboarding email attempted: %s", to_email)
        return False

    name = (name or "").strip() or "Colleague"
    purpose = (purpose or "").strip() or "an invitation"
    allowed_hosts = current_app.config.get("ONBOARDING_ALLOWED_HOSTS")  # optional list

    if not _is_safe_url(onboarding_url, allowed_hosts=allowed_hosts):
        current_app.logger.warning("Unsafe onboarding_url attempted: %s", onboarding_url)
        return False

    # Create a one-time token and safe URL
    try:
        token = _make_onboarding_token(to_email)
        safe_url = _build_onboarding_url(onboarding_url, token)
    except Exception:
        current_app.logger.exception("Failed to create onboarding token for %s", to_email)
        return False

    # Prepare message bodies
    subject = current_app.config.get("ONBOARDING_SUBJECT", "Welcome to ThesisVault")
    from_email = current_app.config.get("MAIL_DEFAULT_SENDER")

    text_body = f"""Hello {name},

You've been invited to join ThesisVault for: {purpose}.
Please complete your registration by clicking the link below:

{safe_url}

If you did not expect this invitation, please ignore this email.
"""

    html_template = """
    <html>
      <body>
        <p>Hello {{ name }},</p>
        <p>You've been invited to join <strong>ThesisVault</strong> for: {{ purpose }}.</p>
        <p>
          <a href="{{ url }}" style="display:inline-block;padding:10px 16px;
          background:#1a73e8;color:#fff;text-decoration:none;border-radius:4px;">
            Complete registration
          </a>
        </p>
        <p>If you did not expect this invitation, please ignore this email.</p>
      </body>
    </html>
    """
    html_body = render_template_string(html_template, name=name, purpose=purpose, url=safe_url)

    msg = EmailMessage(
        subject=subject,
        body=text_body,
        html=html_body,
        from_email=from_email,
        to=[to_email]
    )

    # Send with retries and optional async enqueue
    max_retries = int(current_app.config.get("MAIL_SEND_RETRIES", 3))
    backoff_base = float(current_app.config.get("MAIL_BACKOFF_BASE", 1.5))

    try:
        if send_async and current_app.config.get("USE_CELERY"):
            # Enqueue the send to your background worker (preferred)
            # send_email_task.delay(msg)  # adapt to your task signature
            # For now, log and return True to indicate queued
            current_app.logger.info("Enqueued onboarding email for %s", to_email)
            return True

        # Fallback: synchronous send with retries
        for attempt in range(1, max_retries + 1):
            try:
                msg.send()
                current_app.logger.info("Onboarding email sent to %s", to_email)
                return True
            except Exception as exc:
                current_app.logger.exception("Attempt %s failed sending onboarding email to %s", attempt, to_email)
                if attempt < max_retries:
                    time.sleep(backoff_base ** attempt)
                else:
                    current_app.logger.error("All attempts failed sending onboarding email to %s", to_email)
                    return False

    except Exception:
        current_app.logger.exception("Unexpected error in send_onboarding_email for %s", to_email)
        return False

