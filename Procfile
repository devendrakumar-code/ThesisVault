web: gunicorn --chdir backend app:app
worker: celery -A backend.celery_app worker --loglevel=info --concurrency=2
beat: celery -A backend.celery_app beat --loglevel=info
