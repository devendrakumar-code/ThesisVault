from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config.get('CELERY_BROKER_URL'),
        backend=app.config.get('CELERY_RESULT_BACKEND')
    )

    # Minimal safe defaults; override via app.config if needed
    celery.conf.update(
        task_serializer=app.config.get('CELERY_TASK_SERIALIZER', 'json'),
        result_serializer=app.config.get('CELERY_RESULT_SERIALIZER', 'json'),
        accept_content=app.config.get('CELERY_ACCEPT_CONTENT', ['json']),
        enable_utc=app.config.get('CELERY_ENABLE_UTC', True),
        timezone=app.config.get('CELERY_TIMEZONE', 'UTC'),
        task_acks_late=app.config.get('CELERY_TASK_ACKS_LATE', True),
        worker_prefetch_multiplier=app.config.get('CELERY_WORKER_PREFETCH_MULTIPLIER', 1),
        task_default_retry_delay=app.config.get('CELERY_TASK_DEFAULT_RETRY_DELAY', 60),
        task_routes=app.config.get('CELERY_TASK_ROUTES', {}),
        result_expires=app.config.get('CELERY_RESULT_EXPIRES', 3600),  # seconds
        broker_transport_options=app.config.get('CELERY_BROKER_TRANSPORT_OPTIONS', {'max_retries': 3}),
    )

    # --- Beat SCHEDULE ---
    celery.conf.beat_schedule = {
        'daily-invite-cleanup': {
            'task': 'tasks.cleanup_expired_invites',
            'schedule': crontab(hour=0, minute=0), # Every midnight
        },
    }

    # Optional: define queues for heavy vs light tasks
    celery.conf.task_queues = (
        app.config.get('CELERY_TASK_QUEUES') or [
            Queue('default', Exchange('default'), routing_key='default'),
            Queue('ai', Exchange('ai'), routing_key='ai'),
        ]
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

        def on_failure(self, exc, task_id, args, kwargs, einfo):
            # Centralized failure logging
            app.logger.exception("Celery task failed %s args=%s kwargs=%s", task_id, args, kwargs)

    celery.Task = ContextTask
    return celery

