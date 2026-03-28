import json
import os
import re
import time
import uuid
from typing import Any, Dict
import google.generativeai as genai
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from extentions import db
from models import Submission

# Configurable retry/backoff
MAX_RETRIES = 3
BACKOFF_BASE = 1.5
ALLOWED_PLAGIARISM = {"low", "medium", "high"}

JSON_OBJ_RE = re.compile(r'\{.*\}', re.DOTALL)

def _extract_first_json(text: str) -> Dict[str, Any]:
    """
    Extract the first JSON object from text. Raises ValueError if none found or invalid JSON.
    """
    if not text:
        raise ValueError("Empty response text")
    match = JSON_OBJ_RE.search(text)
    if not match:
        raise ValueError("No JSON object found in response")
    raw = match.group(1)
    return json.loads(raw)

def _clamp_score(value: Any) -> int:
    try:
        score = int(float(value))
    except Exception:
        return 0
    return max(0, min(100, score))

def analyze_thesis_with_gemini(submission_id: int) -> None:
    """
    Fetch a submission, send the PDF to Gemini, parse the JSON response,
    and update the submission record. Designed to be called from a background worker.
    """
    submission = Submission.query.get(submission_id)
    if not submission:
        current_app.logger.warning("Submission not found: %s", submission_id)
        return

    upload_root = current_app.config.get("UPLOAD_FOLDER")
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not upload_root or not api_key:
        current_app.logger.error("Missing configuration for Gemini or upload folder")
        # Mark as failed to avoid infinite retries by job runner
        try:
            submission.status = "failed"
            db.session.commit()
        except Exception:
            db.session.rollback()
        return

    # Resolve absolute path and ensure it's inside upload root
    abs_path = os.path.abspath(os.path.join(upload_root, submission.file_path or ""))
    if not abs_path.startswith(os.path.abspath(upload_root)) or not os.path.exists(abs_path):
        current_app.logger.error("Submission file missing or outside upload folder: %s", abs_path)
        try:
            submission.status = "failed"
            db.session.commit()
        except Exception:
            db.session.rollback()
        return

    # Configure API client
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-pro")

    # Mark as processing before external call so state is visible
    try:
        submission.status = "processing"
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to mark submission processing")
        # continue; we still attempt analysis but DB state may be inconsistent

    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Upload file to Gemini file API
            sample_file = genai.upload_file(path=abs_path, display_name=f"submission-{submission_id}")

            # Compose prompt with clear instruction to return JSON only
            prompt = (
                "Analyze this academic thesis PDF. Return a single JSON object with keys:\n"
                '"score" (int 0-100), "summary" (string), "strengths" (array of strings), '
                '"weaknesses" (array of strings), "plagiarism_risk" ("Low"/"Medium"/"High").\n'
                "Respond with JSON only, no surrounding markdown or commentary."
            )

            # Call model - keep call synchronous; if the SDK supports streaming or async,
            # prefer background-friendly patterns in your worker.
            response = model.generate_content([sample_file, prompt])

            # Extract JSON robustly
            raw_text = getattr(response, "text", "") or str(response)
            result_data = _extract_first_json(raw_text)

            # Validate and normalize result
            score = _clamp_score(result_data.get("score"))
            summary = result_data.get("summary") or ""
            strengths = result_data.get("strengths") or []
            weaknesses = result_data.get("weaknesses") or []
            plagiarism = (result_data.get("plagiarism_risk") or "").strip().lower()

            if isinstance(strengths, str):
                strengths = [strengths]
            if isinstance(weaknesses, str):
                weaknesses = [weaknesses]
            if plagiarism not in {p.lower() for p in ALLOWED_PLAGIARISM}:
                # Normalize or default
                plagiarism = "low"

            # Persist results atomically
            submission.ai_score = score
            submission.ai_feedback = {
                "summary": summary,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "plagiarism_risk": plagiarism
            }
            submission.status = "completed"
            db.session.commit()
            current_app.logger.info("Gemini analysis completed for submission %s", submission_id)
            return
        except ValueError as ve:
            # Parsing or validation error: do not retry
            current_app.logger.exception("Parsing error for submission %s: %s", submission_id, ve)
            last_exc = ve
            try:
                submission.status = "failed"
                db.session.commit()
            except Exception:
                db.session.rollback()
            return
        except Exception as exc:
            # Transient or unknown error: retry a few times
            current_app.logger.exception("Gemini call failed on attempt %s for submission %s", attempt, submission_id)
            last_exc = exc
            # exponential backoff
            if attempt < MAX_RETRIES:
                sleep_for = BACKOFF_BASE ** attempt
                time.sleep(sleep_for)
                continue
            # final failure: mark failed
            try:
                submission.status = "failed"
                db.session.commit()
            except Exception:
                db.session.rollback()
            current_app.logger.error("Gemini analysis permanently failed for %s after %s attempts", submission_id, MAX_RETRIES)
            return

    # If we exit loop without return, log last exception
    if last_exc:
        current_app.logger.exception("Final error for submission %s: %s", submission_id, last_exc)

