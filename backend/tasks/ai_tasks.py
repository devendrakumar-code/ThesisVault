from celery import shared_task
from utils.ai_handler import analyze_thesis_with_gemini

# The name must exactly match the CELERY_TASK_ROUTES in your config.py
# SECURITY FIX: Removed max_retries from Celery level.
# Retry logic is handled entirely within ai_handler.py to prevent
# compounding retries (was 3 Celery × 3 handler = 9 total attempts).
@shared_task(name="tasks.analyze_thesis", bind=True, max_retries=0)
def process_thesis_task(self, submission_id):
    """
    Background worker task to trigger Gemini AI evaluation.
    All retry and error handling is managed by analyze_thesis_with_gemini().
    """
    analyze_thesis_with_gemini(submission_id)
    return True
