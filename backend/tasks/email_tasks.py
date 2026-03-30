# tasks/email_tasks.py
from datetime import datetime
from smtplib import SMTPSenderRefused
import logging

from celery import shared_task
from flask import current_app
from flask_mailman import EmailMultiAlternatives

from extentions import db
from models import Invite

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='tasks.send_onboarding_email_async', max_retries=5, acks_late=True)
def send_onboarding_email_task(self, invite_id):
    """
    Worker task that sends an onboarding email for a persisted Invite.
    Accepts only an integer invite_id to avoid non-serializable payloads.
    Retries with exponential backoff on transient errors.
    """
    try:
        invite = Invite.query.get(invite_id)
        if not invite:
            logger.warning('Invite not found %s', invite_id)
            return False

        if invite.status == 'sent':
            logger.info('Invite already sent %s', invite_id)
            return True

        mail_username = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')
        if not mail_username or not mail_password:
            invite.status = 'failed'
            db.session.commit()
            logger.error('Mail credentials are not configured. Set MAIL_USERNAME and MAIL_PASSWORD in the environment or .env file before sending invites.')
            return False

        msg = EmailMultiAlternatives(
            subject=invite.subject,
            body=invite.text_body,
            from_email=current_app.config.get('MAIL_DEFAULT_SENDER'),
            to=[invite.email],
        )
        msg.attach_alternative(invite.html_body, 'text/html')
        msg.send()

        invite.status = 'sent'
        invite.sent_at = datetime.utcnow()
        db.session.commit()

        logger.info('Onboarding email sent invite_id=%s email=%s', invite_id, invite.email)
        return True

    except SMTPSenderRefused as exc:
        db.session.rollback()
        if getattr(exc, 'smtp_code', None) == 530:
            invite = Invite.query.get(invite_id)
            if invite and invite.status != 'sent':
                invite.status = 'failed'
                db.session.commit()
            logger.exception('SMTP authentication failed while sending invite %s. Check Mailtrap username, password, and default sender configuration.', invite_id)
            return False
        retries = getattr(self.request, 'retries', 0)
        countdown = min(60 * (2 ** retries), 3600)
        logger.exception('Failed to send invite %s attempt=%s, retrying in %s seconds', invite_id, retries, countdown)
        raise self.retry(exc=exc, countdown=countdown)
    except Exception as exc:
        db.session.rollback()
        retries = getattr(self.request, 'retries', 0)
        countdown = min(60 * (2 ** retries), 3600)
        logger.exception('Failed to send invite %s attempt=%s, retrying in %s seconds', invite_id, retries, countdown)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(name='tasks.cleanup_expired_invites')
def cleanup_expired_invites():
    """Scheduled task to mark old invites as expired."""
    now = datetime.utcnow()
    expired_count = Invite.query.filter(
        Invite.status == 'queued',
        Invite.expires_at < now,
    ).update({'status': 'expired'})

    db.session.commit()
    return f'Expired {expired_count} invites.'
