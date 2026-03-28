from celery import current_app as celery_app
from utils.ai_handler import analyze_thesis_with_gemini

# The name must exactly match the CELERY_TASK_ROUTES in your config.py
@celery_app.task(name="tasks.analyze_thesis", bind=True, max_retries=3)
def process_thesis_task(self, submission_id):
    """
    Background worker task to trigger Gemini AI evaluation.
    """
    try:
        analyze_thesis_with_gemini(submission_id)
        return True
    except Exception as exc:
        celery_app.log.exception(f"AI Task failed for submission {submission_id}")
        # Exponential backoff for network drops or Gemini rate limits
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
