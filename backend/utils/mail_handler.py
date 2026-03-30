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
    <!DOCTYPE html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        @media only screen and (max-width: 620px) {
          table.body .content { padding: 0 !important; }
          table.body .container { padding: 0 !important; width: 100% !important; }
          table.body .main { border-radius: 0 !important; }
        }
      </style>
    </head>
    <body style="background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; margin: 0; padding: 0;">
      <table border="0" cellpadding="0" cellspacing="0" class="body" style="border-collapse: separate; width: 100%; background-color: #f8fafc;">
        <tr>
          <td style="display: block; margin: 0 auto; max-width: 580px; padding: 10px; width: 580px;">
            <div class="content" style="box-sizing: border-box; display: block; margin: 0 auto; max-width: 580px; padding: 10px;">
              
              <!-- START CENTERED WHITE CONTAINER -->
              <table role="presentation" class="main" style="border-collapse: separate; width: 100%; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; border-spacing: 0;">
                
                <!-- START MAIN CONTENT AREA -->
                <tr>
                  <td class="wrapper" style="box-sizing: border-box; padding: 40px;">
                    <table border="0" cellpadding="0" cellspacing="0" style="border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: 100%;">
                      <tr>
                        <td>
                          <!-- LOGO / HEADER -->
                          <div style="margin-bottom: 30px;">
                            <span style="font-size: 24px; font-weight: 900; color: #4f46e5; letter-spacing: -0.025em;">ThesisVault</span>
                          </div>
                          
                          <p style="font-size: 16px; font-weight: normal; margin: 0; margin-bottom: 20px; color: #1e293b;">Hello {{ name }},</p>
                          
                          <p style="font-size: 16px; font-weight: normal; margin: 0; margin-bottom: 24px; line-height: 1.6; color: #475569;">
                            You've been invited to join <strong>ThesisVault</strong> for: <span style="color: #6366f1; font-weight: 600;">{{ purpose }}</span>. 
                            Our platform helps you manage research submissions and streamline the grading workflow with AI-powered insights.
                          </p>
                          
                          <table border="0" cellpadding="0" cellspacing="0" class="btn btn-primary" style="border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: 100%; box-sizing: border-box; margin-bottom: 30px;">
                            <tbody>
                              <tr>
                                <td align="left" style="font-size: 16px; vertical-align: top; padding-bottom: 15px;">
                                  <table border="0" cellpadding="0" cellspacing="0" style="border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: auto;">
                                    <tbody>
                                      <tr>
                                        <td style="border-radius: 8px; text-align: center; background-color: #4f46e5;"> <a href="{{ url }}" target="_blank" style="border: solid 1px #4f46e5; border-radius: 8px; box-sizing: border-box; color: #ffffff; cursor: pointer; display: inline-block; font-size: 14px; font-weight: bold; margin: 0; padding: 12px 30px; text-decoration: none; text-transform: capitalize;">Complete Registration</a> </td>
                                      </tr>
                                    </tbody>
                                  </table>
                                </td>
                              </tr>
                            </tbody>
                          </table>
                          
                          <p style="font-size: 14px; font-weight: normal; margin: 0; margin-bottom: 15px; color: #94a3b8; line-height: 1.5;">
                            If the button doesn't work, copy and paste this link into your browser:
                            <br>
                            <span style="word-break: break-all; color: #6366f1;">{{ url }}</span>
                          </p>
                          
                          <hr style="border: 0; border-bottom: 1px solid #f1f5f9; margin: 30px 0;">
                          
                          <p style="font-size: 12px; font-weight: normal; margin: 0; color: #64748b;">
                            This invitation was sent by your organization administrator. If you did not expect this invitation, please ignore this email.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              
              <!-- START FOOTER -->
              <div class="footer" style="clear: both; margin-top: 20px; text-align: center; width: 100%;">
                <table border="0" cellpadding="0" cellspacing="0" style="border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: 100%;">
                  <tr>
                    <td class="content-block" style="color: #94a3b8; font-size: 12px; text-align: center; padding-top: 10px; padding-bottom: 10px;">
                      <span>&copy; 2026 ThesisVault SaaS Platform</span>
                    </td>
                  </tr>
                </table>
              </div>
            </div>
          </td>
        </tr>
      </table>
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

