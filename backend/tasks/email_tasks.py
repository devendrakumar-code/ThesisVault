# tasks/email_tasks.py
import time
from datetime import datetime, timedelta
from celery import current_app as celery_app
from flask import current_app
from flask_mailman import EmailMessage
from extentions import db
from models import Invite  # Invite model described below

# Task configuration: bind=True to access self.retry and request
@celery_app.task(bind=True, name="tasks.send_onboarding_email_async", max_retries=5, acks_late=True)
def send_onboarding_email_task(self, invite_id):
    """
    Worker task that sends an onboarding email for a persisted Invite.
    Accepts only an integer invite_id to avoid non-serializable payloads.
    Retries with exponential backoff on transient errors.
    """
    try:
        invite = Invite.query.get(invite_id)
        if not invite:
            celery_app.log.warning("Invite not found %s", invite_id)
            return False

        # If already sent, skip
        if invite.status == "sent":
            celery_app.log.info("Invite already sent %s", invite_id)
            return True

        # Build message from invite row
        msg_kwargs = {
            "subject": invite.subject,
            "body": invite.text_body,
            "html": invite.html_body,
            "from_email": current_app.config.get("MAIL_DEFAULT_SENDER"),
            "to": [invite.email]
        }

        msg = EmailMessage(**msg_kwargs)
        msg.send()

        # Mark invite as sent
        invite.status = "sent"
        invite.sent_at = datetime.utcnow()
        db.session.commit()

        celery_app.log.info("Onboarding email sent invite_id=%s email=%s", invite_id, invite.email)
        return True

    except Exception as exc:
        db.session.rollback()
        # Exponential backoff: base 60s, cap at 1 hour
        retries = getattr(self.request, "retries", 0)
        countdown = min(60 * (2 ** retries), 3600)
        celery_app.log.exception("Failed to send invite %s attempt=%s, retrying in %s seconds", invite_id, retries, countdown)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(name="tasks.cleanup_expired_invites")
def cleanup_expired_invites():
    """Scheduled task to mark old invites as expired."""
    now = datetime.utcnow()
    expired_count = Invite.query.filter(
        Invite.status == 'queued',
        Invite.expires_at < now
    ).update({"status": "expired"})
    
    db.session.commit()
    return f"Expired {expired_count} invites."
