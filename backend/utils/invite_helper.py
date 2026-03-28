from uuid import uuid4
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer
from flask import current_app, render_template_string
from models import Invite
from extentions import db
from tasks.email_tasks import send_onboarding_email_task

def create_and_queue_invite(email, name, onboarding_base_url, purpose, created_by_id, ttl_days=7, send_async=True):
    """
    Create an Invite DB row, generate token, build bodies, and queue the Celery task.
    Returns invite_id on success, None on failure.
    """
    # Validate email and url before calling this helper
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    token = serializer.dumps({"email": email, "nonce": uuid4().hex})

    safe_url = f"{onboarding_base_url.rstrip('/')}/accept-invite?token={token}"

    subject = current_app.config.get("ONBOARDING_SUBJECT", "Welcome to ThesisVault")
    text_body = f"Hello {name},\n\nYou've been invited to join ThesisVault for: {purpose}.\n{safe_url}"
    html_body = render_template_string("<p>Hello {{name}}</p><p>Click <a href='{{url}}'>here</a></p>", name=name, url=safe_url)

    invite = Invite(
        email=email,
        token=token,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        purpose=purpose,
        created_by_id=created_by_id,
        expires_at=datetime.utcnow() + timedelta(days=ttl_days),
        status="queued"
    )
    db.session.add(invite)
    db.session.commit()

    # Queue the worker with the invite id only
    if send_async and current_app.config.get("USE_CELERY"):
        send_onboarding_email_task.delay(invite.id)
    else:
        # Optionally call the task synchronously for small installs
        send_onboarding_email_task.apply(args=(invite.id,))

    return invite.id

