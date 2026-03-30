import json
import os
import re
import time
from typing import Any, Dict

from google import genai
from flask import current_app

from extentions import db
from models import Submission

MAX_RETRIES = 3
BACKOFF_BASE = 1.5
ALLOWED_PLAGIARISM = {'low', 'medium', 'high'}
JSON_OBJ_RE = re.compile(r'\{.*\}', re.DOTALL)
DEFAULT_GEMINI_MODEL = 'gemini-2.5-flash'
FALLBACK_GEMINI_MODELS = ('gemini-2.5-flash-lite',)


def _extract_first_json(text: str) -> Dict[str, Any]:
    if not text:
        raise ValueError('Empty response text')
    match = JSON_OBJ_RE.search(text)
    if not match:
        raise ValueError('No JSON object found in response')
    return json.loads(match.group(0))


def _clamp_score(value: Any) -> int:
    try:
        score = int(float(value))
    except Exception:
        return 0
    return max(0, min(100, score))


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _mark_submission_failed(submission, message: str) -> None:
    try:
        submission.status = 'failed'
        submission.ai_feedback = message
        db.session.commit()
    except Exception:
        db.session.rollback()


def _build_model_candidates(configured_model: str | None) -> list[str]:
    candidates: list[str] = []
    for model_name in (configured_model, DEFAULT_GEMINI_MODEL, *FALLBACK_GEMINI_MODELS):
        cleaned = (model_name or '').strip()
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)
    return candidates


def _is_model_not_found_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return '404' in message and ('model' in message or 'not_found' in message)


def _is_quota_exceeded_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return '429' in message and ('resource_exhausted' in message or 'quota' in message)


def analyze_thesis_with_gemini(submission_id: int) -> None:
    submission = Submission.query.get(submission_id)
    if not submission:
        current_app.logger.warning('Submission not found: %s', submission_id)
        return

    org = submission.project.organization if submission.project else None
    if not org or not org.is_subscription_valid:
        msg = 'Analysis cancelled: Organization subscription is expired or suspended.'
        current_app.logger.warning(msg)
        _mark_submission_failed(submission, msg)
        return

    if org.monthly_ai_count >= org.monthly_ai_limit:
        msg = f'Analysis failed: Monthly AI limit reached ({org.monthly_ai_limit}). Please upgrade.'
        current_app.logger.warning(msg)
        _mark_submission_failed(submission, msg)
        return

    upload_root = current_app.config.get('UPLOAD_FOLDER')
    if not upload_root:
        msg = 'Analysis failed: UPLOAD_FOLDER is not configured.'
        current_app.logger.error(msg)
        _mark_submission_failed(submission, msg)
        return

    api_key = current_app.config.get('GEMINI_API_KEY')
    configured_model = current_app.config.get('GEMINI_MODEL', DEFAULT_GEMINI_MODEL)
    model_candidates = _build_model_candidates(configured_model)
    if not api_key:
        msg = 'Analysis failed: GEMINI_API_KEY is not configured.'
        current_app.logger.error(msg)
        _mark_submission_failed(submission, msg)
        return

    abs_path = os.path.abspath(os.path.join(upload_root, submission.file_url or ''))
    if not abs_path.startswith(os.path.abspath(upload_root)) or not os.path.exists(abs_path):
        msg = f'Submission file missing or outside upload folder: {submission.file_url}'
        current_app.logger.error(msg)
        _mark_submission_failed(submission, msg)
        return

    client = genai.Client(api_key=api_key)

    try:
        submission.status = 'processing'
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Failed to mark submission processing')

    prompt = (
        'You are assisting a professor who is reviewing a student academic submission. '
        'Read the PDF carefully and return exactly one valid JSON object. Do not include markdown fences, extra narration, or any text outside the JSON. '
        'Write concise, evidence-based points in plain academic English. '
        'Use this exact JSON shape: '
        '{'
        '"score": integer from 0 to 100, '
        '"summary": string, '
        '"executive_summary": string, '
        '"document_focus": string, '
        '"methodology_overview": string, '
        '"key_findings": array of 3 to 5 short strings, '
        '"strengths": array of 3 to 5 short strings, '
        '"weaknesses": array of 3 to 5 short strings, '
        '"risks": array of 2 to 4 short strings, '
        '"improvement_actions": array of 3 to 5 specific actions the student should take next, '
        '"professor_questions": array of 3 to 5 short oral-defense or viva questions, '
        '"plagiarism_risk": one of "Low", "Medium", or "High", '
        '"confidence_note": string'
        '}. '
        'Scoring guidance: evaluate clarity of problem definition, structure, methodology, evidence, feasibility, originality, and business or research relevance. '
        'If the PDF is only a proposal or early draft, say so clearly and score it as a proposal, not as a final thesis.'
    )

    last_exc = None
    for model_name in model_candidates:
        for attempt in range(1, MAX_RETRIES + 1):
            sample_file = None
            try:
                sample_file = client.files.upload(file=abs_path)
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[sample_file, prompt],
                    )

                    raw_text = getattr(response, 'text', '') or str(response)
                    result_data = _extract_first_json(raw_text)

                    score = _clamp_score(result_data.get('score'))
                    summary = (result_data.get('summary') or '').strip()
                    executive_summary = (result_data.get('executive_summary') or summary).strip()
                    document_focus = (result_data.get('document_focus') or '').strip()
                    methodology_overview = (result_data.get('methodology_overview') or '').strip()
                    strengths = _normalize_list(result_data.get('strengths'))
                    weaknesses = _normalize_list(result_data.get('weaknesses'))
                    key_findings = _normalize_list(result_data.get('key_findings'))
                    risks = _normalize_list(result_data.get('risks'))
                    improvement_actions = _normalize_list(result_data.get('improvement_actions'))
                    professor_questions = _normalize_list(result_data.get('professor_questions'))
                    confidence_note = (result_data.get('confidence_note') or '').strip()
                    plagiarism = (result_data.get('plagiarism_risk') or '').strip().lower()

                    if plagiarism not in ALLOWED_PLAGIARISM:
                        plagiarism = 'low'

                    submission.ai_score = score
                    submission.ai_evaluation = {
                        'summary': summary,
                        'executive_summary': executive_summary,
                        'document_focus': document_focus,
                        'methodology_overview': methodology_overview,
                        'key_findings': key_findings,
                        'strengths': strengths,
                        'weaknesses': weaknesses,
                        'risks': risks,
                        'improvement_actions': improvement_actions,
                        'professor_questions': professor_questions,
                        'plagiarism_risk': plagiarism,
                        'confidence_note': confidence_note,
                    }
                    submission.status = 'completed'
                    submission.ai_feedback = None
                    org.monthly_ai_count += 1

                    db.session.commit()
                    current_app.logger.info(
                        'Gemini analysis completed for submission %s with model %s. Org usage: %s/%s',
                        submission_id,
                        model_name,
                        org.monthly_ai_count,
                        org.monthly_ai_limit,
                    )
                    return
                finally:
                    if sample_file:
                        try:
                            client.files.delete(name=sample_file.name)
                            current_app.logger.info('Purged temporary file %s from Gemini API', sample_file.name)
                        except Exception as delete_exc:
                            current_app.logger.warning(
                                'Failed to delete temporary Gemini file %s: %s', sample_file.name, delete_exc
                            )
            except ValueError as exc:
                current_app.logger.exception('Parsing error for submission %s: %s', submission_id, exc)
                _mark_submission_failed(submission, f'Parsing Error: {str(exc)}')
                return
            except Exception as exc:
                current_app.logger.exception(
                    'Gemini call failed on attempt %s for submission %s using model %s',
                    attempt,
                    submission_id,
                    model_name,
                )
                last_exc = exc

                if _is_model_not_found_error(exc):
                    current_app.logger.warning(
                        'Gemini model %s is unavailable for submission %s. Trying next configured fallback.',
                        model_name,
                        submission_id,
                    )
                    break

                if _is_quota_exceeded_error(exc):
                    _mark_submission_failed(
                        submission,
                        f'AI review unavailable right now because the Gemini quota is exhausted for model {model_name}.',
                    )
                    return

                if attempt < MAX_RETRIES:
                    time.sleep(BACKOFF_BASE ** attempt)
                    continue

                break

    if last_exc:
        _mark_submission_failed(submission, f'Final API Error: {str(last_exc)}')
        current_app.logger.error(
            'Gemini analysis permanently failed for %s after trying models %s',
            submission_id,
            ', '.join(model_candidates),
        )
