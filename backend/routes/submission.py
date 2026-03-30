import os
import uuid
import hmac
import hashlib
import time as time_mod
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from tasks.ai_tasks import process_thesis_task
from utils.ai_handler import analyze_thesis_with_gemini
from flask import Blueprint, request, jsonify, current_app, send_from_directory, send_file, abort
from flask_security import auth_token_required, current_user, roles_accepted
from werkzeug.utils import secure_filename, safe_join
from extentions import db
from models import Submission, Project, Milestone, Enrollment, User
from decorators import subscription_required, requires_feature
from schemas import submission_schema, student_submission_schema, user_schema
from sqlalchemy import func, case
from sqlalchemy.exc import IntegrityError

submissions_bp = Blueprint('submissions', __name__, url_prefix='/api/submissions')

ALLOWED_EXTENSIONS = {'pdf'}
JOINED_UPLOAD_SUBDIR = ''  # optional subdir inside UPLOAD_FOLDER for submissions

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

PDF_MAGIC_BYTES = b'%PDF'

def _validate_pdf_content(file_stream):
    """Validate that the uploaded file starts with PDF magic bytes."""
    header = file_stream.read(4)
    file_stream.seek(0)  # Reset stream for saving
    return header == PDF_MAGIC_BYTES

def json_response(success, message, data=None, code=200):
    return jsonify({"success": success, "message": message, "data": data}), code

def _ensure_upload_folder():
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if not upload_folder:
        raise RuntimeError("Server misconfiguration: UPLOAD_FOLDER not set")
    full_path = os.path.join(upload_folder, JOINED_UPLOAD_SUBDIR) if JOINED_UPLOAD_SUBDIR else upload_folder
    os.makedirs(full_path, exist_ok=True)
    return full_path

def _safe_file_path(filename):
    upload_folder = _ensure_upload_folder()
    # store only relative path in DB
    return os.path.join(upload_folder, filename)

def _is_professor_of_project(user, project):
    return user.has_role('professor') and project.professor_id == user.id

def _delete_file(relative_url):
    """Safely delete an uploaded file from disk."""
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', '')
        full_path = os.path.join(upload_folder, relative_url)
        if os.path.isfile(full_path):
            os.remove(full_path)
    except Exception:
        current_app.logger.warning(f"Could not delete old file: {relative_url}")


def _milestone_timezone():
    return ZoneInfo(current_app.config.get('CELERY_TIMEZONE', 'Asia/Kolkata'))


def _to_local_naive(dt_value):
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        return dt_value
    return dt_value.astimezone(_milestone_timezone()).replace(tzinfo=None)


def _current_milestone_time():
    return datetime.now(_milestone_timezone()).replace(tzinfo=None)


def _effective_submission_deadline(submission, milestone):
    if submission and submission.review_status == 'rejected' and submission.resubmission_deadline:
        override_deadline = _to_local_naive(submission.resubmission_deadline)
        if override_deadline:
            return override_deadline
    return _to_local_naive(milestone.deadline)

# --- 1. STUDENT ENDPOINTS ---

@submissions_bp.route('/upload/<project_id>', methods=['POST'])
@auth_token_required
@roles_accepted('student')
@subscription_required()
@requires_feature('has_ai_feature')
def upload_submission(project_id):
    """Handles PDF uploads with milestone gating and overwrite-on-resubmit."""
    project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first()
    if not project:
        return json_response(False, "Project not found", None, 404)
    if getattr(project, 'status', 'active') != 'active':
        return json_response(False, "Project is not accepting submissions", None, 400)

    enrollment = Enrollment.query.filter_by(
        project_id=project_id, student_id=current_user.id, is_active=True
    ).first()
    if not enrollment:
        return json_response(False, "You are not enrolled in this project", None, 403)

    # ── Milestone validation ──────────────────────────────────────────────────
    milestone_id = request.form.get('milestone_id')
    if not milestone_id:
        return json_response(False, "milestone_id is required", None, 400)

    milestone = Milestone.query.filter_by(id=milestone_id, project_id=project_id).first()
    if not milestone:
        return json_response(False, "Milestone not found in this project", None, 404)

    existing = Submission.query.filter_by(
        student_id=current_user.id, milestone_id=milestone_id
    ).first()

    now = _current_milestone_time()
    milestone_start = _to_local_naive(milestone.starts_at)
    effective_deadline = _effective_submission_deadline(existing, milestone)
    if milestone_start and now < milestone_start:
        return json_response(False, "This milestone has not opened yet", None, 400)
    if existing and existing.review_status and existing.review_status not in {'pending_review', 'rejected'}:
        return json_response(False, "This milestone has already been marked by your professor. New submissions are locked.", None, 400)
    if existing and existing.review_status == 'rejected':
        if not effective_deadline or now > effective_deadline:
            return json_response(False, "Your professor's resubmission window for this milestone has expired.", None, 400)
    elif effective_deadline and now > effective_deadline:
        return json_response(False, "The deadline for this milestone has passed", None, 400)

    # ── File validation ───────────────────────────────────────────────────────
    if 'file' not in request.files:
        return json_response(False, "No file uploaded", None, 400)
    file = request.files['file']
    if file.filename == '':
        return json_response(False, "Empty filename", None, 400)
    if not allowed_file(file.filename):
        return json_response(False, "Invalid file. Only PDFs are allowed.", None, 400)
    if not _validate_pdf_content(file):
        return json_response(False, "Invalid file content. File is not a valid PDF.", None, 400)

    original_basename = secure_filename(os.path.basename(file.filename))
    unique_name = f"{current_user.id}_{project_id}_{uuid.uuid4().hex}_{original_basename}"
    try:
        upload_folder = _ensure_upload_folder()
        file_path = os.path.join(upload_folder, unique_name)
        file.save(file_path)
        relative_url = os.path.relpath(file_path, current_app.config.get('UPLOAD_FOLDER'))

        # ── Overwrite if submission already exists for this student + milestone ──
        if existing:
            _delete_file(existing.file_url)  # remove old PDF from disk
            existing.file_url = relative_url
            existing.status = 'uploaded'
            existing.ai_evaluation = None
            existing.ai_score = None
            existing.ai_feedback = None
            existing.grade = None
            existing.remarks = None
            existing.review_status = 'pending_review'
            existing.rejection_extension_days = None
            existing.resubmission_deadline = None
            db.session.commit()
            return json_response(True, "Submission updated. Waiting for Professor review.",
                                 submission_schema.dump(existing), 200)
        else:
            new_submission = Submission(
                student_id=current_user.id,
                project_id=project_id,
                milestone_id=milestone_id,
                organization_id=current_user.organization_id,
                file_url=relative_url,
                status='uploaded'
            )
            db.session.add(new_submission)
            db.session.commit()
            return json_response(True, "Thesis uploaded successfully. Waiting for Professor review.",
                                 submission_schema.dump(new_submission), 201)
    except IntegrityError:
        db.session.rollback()
        current_app.logger.exception("DB integrity error while saving submission")
        return json_response(False, "Unable to save submission (conflict)", None, 409)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unexpected error during upload")
        return json_response(False, "Upload failed due to server error", None, 500)

@submissions_bp.route('/my', methods=['GET'])
@auth_token_required
@roles_accepted('student')
def get_my_submissions():
    """Returns all submissions for the logged-in student."""
    submissions = Submission.query.filter_by(student_id=current_user.id).order_by(Submission.created_at.desc()).all()
    return json_response(True, "Fetched your submissions", submission_schema.dump(submissions, many=True))

@submissions_bp.route('/status/<submission_id>', methods=['GET'])
@auth_token_required
def get_submission_status(submission_id):
    """Polling endpoint for the frontend to check AI progress."""
    submission = Submission.query.get_or_404(submission_id)

    # Student can see own; professor can see only if they own the project; admins can see all in org
    if submission.student_id == current_user.id:
        pass
    else:
        project = submission.project
        if current_user.has_role('professor'):
            if project.professor_id != current_user.id:
                return json_response(False, "Unauthorized", None, 403)
        elif current_user.has_role('admin'):
            if project.organization_id != current_user.organization_id:
                return json_response(False, "Unauthorized", None, 403)
        else:
            return json_response(False, "Unauthorized", None, 403)

    # Students get the restricted schema (no AI data)
    if submission.student_id == current_user.id:
        return json_response(True, "Status fetched", student_submission_schema.dump(submission))

    return json_response(True, "Status fetched", submission_schema.dump(submission))

# --- 2. PROFESSOR & ADMIN ENDPOINTS ---

@submissions_bp.route('/<submission_id>', methods=['GET'])
@auth_token_required
def get_submission_details(submission_id):
    """Fetch details of a single submission for both students and professors."""
    # Force refresh from DB to catch background worker updates
    db.session.expire_all()
    submission = Submission.query.get_or_404(submission_id)
    project = submission.project

    # Security check: owner, professor of project, or org admin
    if submission.student_id == current_user.id:
        allowed = True
    elif current_user.has_role('professor') and project.professor_id == current_user.id:
        allowed = True
    elif current_user.has_role('admin') and project.organization_id == current_user.organization_id:
        allowed = True
    else:
        allowed = False
    
    if not allowed:
        return json_response(False, "Unauthorized", None, 403)

    return json_response(True, "Fetched submission details", submission_schema.dump(submission))

@submissions_bp.route('/project/<project_id>', methods=['GET'])
@auth_token_required
@roles_accepted('professor', 'admin')
def get_project_submissions(project_id):
    """List of all work submitted to a specific project."""
    project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first_or_404()
    if current_user.has_role('professor') and project.professor_id != current_user.id:
        return json_response(False, "Unauthorized", None, 403)

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    pagination = Submission.query.filter_by(project_id=project_id)\
        .order_by(Submission.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return json_response(True, "Fetched project submissions", {
        "submissions": submission_schema.dump(pagination.items, many=True),
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages
    })

@submissions_bp.route('/all', methods=['GET'])
@auth_token_required
@roles_accepted('professor')
def get_all_submissions():
    """Consolidated list of all work submitted to all professor's projects."""
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    pagination = Submission.query.join(Project).filter(
        Project.professor_id == current_user.id
    ).order_by(Submission.created_at.desc())\
    .paginate(page=page, per_page=per_page, error_out=False)

    return json_response(True, "Fetched all project submissions", {
        "submissions": submission_schema.dump(pagination.items, many=True),
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages
    })

@submissions_bp.route('/stats/<project_id>', methods=['GET'])
@auth_token_required
@roles_accepted('professor', 'admin')
def get_project_stats(project_id):
    """Aggregated analytics for the professor's dashboard."""
    project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first_or_404()
    if current_user.has_role('professor') and project.professor_id != current_user.id:
        return json_response(False, "Unauthorized", None, 403)

    # Use SQLAlchemy case for conditional aggregation
    stats = db.session.query(
        func.avg(cast(Submission.grade, db.Integer)).label('avg_grade'),
        func.count(Submission.id).label('total_submissions'),
        func.sum(case((Submission.review_status != 'pending_review', 1), else_=0)).label('reviewed')
    ).filter(Submission.project_id == project_id).first()

    return json_response(True, "Stats calculated", {
        "average_score": float(stats.avg_grade or 0),
        "total_submissions": int(stats.total_submissions or 0),
        "processed_count": int(stats.reviewed or 0)
    })

@submissions_bp.route('/review/<submission_id>', methods=['PATCH'])
@auth_token_required
@roles_accepted('professor')
def review_submission(submission_id):
    """Professor writes their own grade, remarks, and sets the review status."""
    data = request.get_json(silent=True) or {}
    submission = Submission.query.get_or_404(submission_id)
    project = submission.project

    if project.professor_id != current_user.id:
        return json_response(False, "Unauthorized", None, 403)

    ALLOWED_REVIEW_STATUSES = {'pending_review', 'approved', 'needs_revision', 'rejected'}
    previous_status = submission.review_status or 'pending_review'
    next_status = previous_status

    current_app.logger.info(f"Reviewing submission {submission_id}. Data: {data}")

    if 'review_status' in data:
        next_status = (data.get('review_status') or '').strip().lower()
        if next_status not in ALLOWED_REVIEW_STATUSES:
            return json_response(False, f"Invalid review_status. Allowed: {ALLOWED_REVIEW_STATUSES}", None, 400)
    
    submission.review_status = next_status
    current_app.logger.info(f"Submission {submission_id} status set to: {submission.review_status}")

    if 'grade' in data:
        submission.grade = (data.get('grade') or '').strip() or None

    if 'remarks' in data:
        submission.remarks = data.get('remarks')

    if next_status == 'rejected':
        extension_days = submission.rejection_extension_days
        should_recompute_deadline = previous_status != 'rejected' or submission.resubmission_deadline is None

        if 'rejection_extension_days' in data:
            raw_extension_days = data.get('rejection_extension_days')
            if raw_extension_days in (None, '', False):
                return json_response(False, 'Extension days are required when rejecting a submission', None, 400)
            
            try:
                # Robustly handle various types (incl. strings like "5" or accidentally sent booleans)
                if isinstance(raw_extension_days, bool):
                    # If it's a boolean 'true', it might mean something was selected but value not passed.
                    # We should probably still error out or default to something? Let's error and require a number.
                    return json_response(False, 'Rejection requires a numeric amount of extension days.', None, 400)
                
                extension_days = int(raw_extension_days)
            except (TypeError, ValueError):
                return json_response(False, 'Extension days must be a whole number', None, 400)
            
            should_recompute_deadline = True

        if extension_days is None or extension_days <= 0:
            return json_response(False, 'Professor must provide at least 1 extra day when rejecting a submission', None, 400)

        submission.rejection_extension_days = extension_days

        if should_recompute_deadline:
            baseline = _current_milestone_time()
            milestone_deadline = _to_local_naive(submission.milestone.deadline) if submission.milestone else None
            if milestone_deadline and milestone_deadline > baseline:
                baseline = milestone_deadline
            local_deadline = baseline + timedelta(days=extension_days)
            submission.resubmission_deadline = local_deadline.replace(tzinfo=_milestone_timezone()).astimezone(timezone.utc)
    else:
        submission.rejection_extension_days = None
        submission.resubmission_deadline = None

    try:
        db.session.commit()
        return json_response(True, "Review updated", submission_schema.dump(submission))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to update review")
        return json_response(False, "Unable to update review", None, 500)

# --- 3. AI & SYSTEM ENDPOINTS ---

@submissions_bp.route('/re-evaluate/<submission_id>', methods=['POST'])
@auth_token_required
@roles_accepted('professor')
def re_evaluate(submission_id):
    """Manually trigger Gemini AI to look at the PDF again."""
    submission = Submission.query.get_or_404(submission_id)
    project = submission.project
    if project.professor_id != current_user.id:
        return json_response(False, "Unauthorized", None, 403)

    submission.status = 'pending'
    try:
        db.session.commit()
        # TODO: enqueue background job to re-run AI analysis
        return json_response(True, "Re-evaluation queued.")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to queue re-evaluation")
        return json_response(False, "Unable to queue re-evaluation", None, 500)

@submissions_bp.route('/<submission_id>', methods=['DELETE'])
@auth_token_required
def delete_submission(submission_id):
    """Deletes record and physical PDF file. Professors can delete only for their projects; admins can delete across org."""
    submission = Submission.query.get_or_404(submission_id)
    project = submission.project

    # Authorization: student owner, project professor, or org admin
    if submission.student_id == current_user.id:
        allowed = True
    elif current_user.has_role('professor') and project.professor_id == current_user.id:
        allowed = True
    elif current_user.has_role('admin') and project.organization_id == current_user.organization_id:
        allowed = True
    else:
        allowed = False

    if not allowed:
        return json_response(False, "Unauthorized", None, 403)

    try:
        # Resolve absolute path and ensure it's inside UPLOAD_FOLDER
        upload_root = current_app.config.get('UPLOAD_FOLDER')
        if submission.file_url and upload_root:
            abs_path = os.path.abspath(os.path.join(upload_root, submission.file_url))
            if abs_path.startswith(os.path.abspath(upload_root)) and os.path.exists(abs_path):
                os.remove(abs_path)
        # Optionally: soft-delete instead of hard delete
        db.session.delete(submission)
        db.session.commit()
        return json_response(True, "Submission deleted")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to delete submission")
        return json_response(False, "Unable to delete submission", None, 500)

def _generate_download_signature(submission_id, user_id, expires_at):
    """Generate an HMAC signature for a short-lived download URL."""
    secret = current_app.config['SECRET_KEY']
    message = f"{submission_id}:{user_id}:{expires_at}"
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

def _verify_download_signature(submission_id, user_id, expires_at, signature):
    """Verify an HMAC signature and check expiry."""
    if int(time_mod.time()) > int(expires_at):
        return False
    expected = _generate_download_signature(submission_id, user_id, expires_at)
    return hmac.compare_digest(expected, signature)

@submissions_bp.route('/<submission_id>/download-url', methods=['GET'])
@auth_token_required
def get_download_url(submission_id):
    """Generate a short-lived signed download URL (5 min expiry)."""
    submission = Submission.query.get_or_404(submission_id)
    project = submission.project

    is_owner = submission.student_id == current_user.id
    is_prof = current_user.has_role('professor') and project.professor_id == current_user.id
    is_admin = current_user.has_role('admin') and project.organization_id == current_user.organization_id

    if not (is_owner or is_prof or is_admin):
        return json_response(False, "Unauthorized", None, 403)

    expires_at = int(time_mod.time()) + 300  # 5 minutes
    signature = _generate_download_signature(submission_id, current_user.id, expires_at)

    base_url = request.host_url.rstrip('/')
    download_url = (
        f"{base_url}/api/submissions/{submission_id}/download"
        f"?user_id={current_user.id}&expires={expires_at}&sig={signature}"
    )
    return json_response(True, "Download URL generated", {"url": download_url, "expires_in": 300})

@submissions_bp.route('/<submission_id>/download', methods=['GET'])
def download_submission(submission_id):
    """
    Securely streams the PDF file using short-lived signed URLs.
    No JWT token is passed in the query string.
    """
    # Verify signed URL parameters
    user_id = request.args.get('user_id', '')
    expires_at = request.args.get('expires', '0')
    signature = request.args.get('sig', '')

    if not user_id or not signature:
        return json_response(False, "Authentication required", None, 401)

    if not _verify_download_signature(submission_id, user_id, expires_at, signature):
        return json_response(False, "Download link expired or invalid", None, 403)

    user = User.query.get(user_id)
    if not user:
        return json_response(False, "User not found", None, 403)

    submission = Submission.query.get_or_404(submission_id)
    project = submission.project

    # Authorization Check
    is_owner = submission.student_id == user.id
    is_prof = any(r.name == 'professor' for r in user.roles) and project.professor_id == user.id
    is_admin = any(r.name == 'admin' for r in user.roles) and project.organization_id == user.organization_id

    if not (is_owner or is_prof or is_admin):
        return json_response(False, "Unauthorized to access this file", None, 403)

    upload_root = current_app.config.get('UPLOAD_FOLDER')
    if not upload_root:
        current_app.logger.error("UPLOAD_FOLDER not configured")
        return json_response(False, "Server misconfiguration", None, 500)

    rel_path = (submission.file_url or "").lstrip("/\\")
    if not rel_path:
        return json_response(False, "File not available", None, 404)

    try:
        abs_path = safe_join(upload_root, rel_path)
    except Exception:
        current_app.logger.exception("Unsafe file path for submission %s", submission_id)
        return json_response(False, "Invalid file path", None, 400)

    if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        return json_response(False, "File not found", None, 404)

    download_name = secure_filename(os.path.basename(rel_path)) or f"submission-{submission_id}.pdf"
    inline = request.args.get('inline') == 'true'

    try:
        return send_file(
            abs_path,
            as_attachment=not inline,
            download_name=download_name,
            mimetype='application/pdf',
            conditional=True
        )
    except Exception:
        current_app.logger.exception("Failed to send file for submission %s", submission_id)
        return json_response(False, "Failed to deliver file", None, 500)

@submissions_bp.route('/evaluate/<submission_id>', methods=['POST'])
@auth_token_required
@roles_accepted('professor')
@subscription_required()
@requires_feature('has_ai_feature')
def trigger_ai_evaluation(submission_id):
    """
    Trigger Gemini AI analysis for a submission.
    Flow: Validate, mark pending, dispatch to Celery, return 202.
    """
    submission = Submission.query.get_or_404(submission_id)
    project = submission.project

    # Ownership and org scoping
    if project.professor_id != current_user.id:
        return json_response(False, "Unauthorized: You do not own this project", None, 403)
    if project.organization_id != current_user.organization_id:
        return json_response(False, "Unauthorized: Organization mismatch", None, 403)

    # Prevent double-processing
    # Allow starting from 'uploaded', 'completed', or 'failed'.
    # Only block if it is ALREADY in an active background state.
    if current_app.config.get('USE_CELERY') and submission.status in ('processing', 'queued', 'pending'):
        if request.args.get('force') != 'true':
            return json_response(False, f"Analysis already in progress (Status: {submission.status})", None, 400)

    # Ensure file exists before queuing
    upload_root = current_app.config.get('UPLOAD_FOLDER')
    file_url = submission.file_url or ""
    abs_path = os.path.abspath(os.path.join(upload_root or "", file_url))
    if not upload_root or not os.path.isfile(abs_path) or not abs_path.startswith(os.path.abspath(upload_root)):
        return json_response(False, "Submission file not available", None, 404)

    # Mark pending state and dispatch
    try:
        submission.status = 'pending'
        db.session.commit()
        
        if current_app.config.get('USE_CELERY'):
            # DISPATCH TO CELERY
            process_thesis_task.delay(submission.id)
            return json_response(True, "AI evaluation queued successfully", {"submission_id": submission.id}, 202)
        else:
            # RUN SYNCHRONOUSLY FOR DEVELOPMENT
            analyze_thesis_with_gemini(submission.id)
            # Refresh from DB since analyze_thesis_with_gemini might have committed changes
            db.session.refresh(submission)
            return json_response(True, "AI evaluation completed successfully", submission_schema.dump(submission), 200)

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Failed to mark submission pending %s", submission_id)
        return json_response(False, "Unable to queue evaluation", None, 500)



