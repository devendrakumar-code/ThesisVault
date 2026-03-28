import os
import uuid
from tasks.ai_tasks import process_thesis_task
from utils.ai_handler import analyze_thesis_with_gemini
from flask import Blueprint, request, jsonify, current_app, send_from_directory, send_file, abort
from flask_security import auth_token_required, current_user, roles_accepted
from werkzeug.utils import secure_filename, safe_join
from extentions import db
from models import Submission, Project, Enrollment, User
from decorators import subscription_required, requires_feature
from schemas import submission_schema, user_schema
from sqlalchemy import func, case
from sqlalchemy.exc import IntegrityError

submissions_bp = Blueprint('submissions', __name__, url_prefix='/api/submissions')

ALLOWED_EXTENSIONS = {'pdf'}
JOINED_UPLOAD_SUBDIR = ''  # optional subdir inside UPLOAD_FOLDER for submissions

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

# --- 1. STUDENT ENDPOINTS ---

@submissions_bp.route('/upload/<int:project_id>', methods=['POST'])
@auth_token_required
@roles_accepted('student')
@subscription_required()
@requires_feature('has_ai_feature')
def upload_submission(project_id):
    """Securely handles PDF uploads and links them to a project enrollment."""
    # Validate project exists and belongs to same org and is active
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

    if 'file' not in request.files:
        return json_response(False, "No file uploaded", None, 400)

    file = request.files['file']
    if file.filename == '':
        return json_response(False, "Empty filename", None, 400)
    if not allowed_file(file.filename):
        return json_response(False, "Invalid file. Only PDFs are allowed.", None, 400)

    # Optional: check MAX_CONTENT_LENGTH (Flask will raise RequestEntityTooLarge automatically if set)
    max_len = current_app.config.get('MAX_CONTENT_LENGTH')
    # Generate a unique filename
    original_basename = secure_filename(os.path.basename(file.filename))
    unique_name = f"{current_user.id}_{project_id}_{uuid.uuid4().hex}_{original_basename}"
    try:
        upload_folder = _ensure_upload_folder()
        file_path = os.path.join(upload_folder, unique_name)
        file.save(file_path)

        new_submission = Submission(
            student_id=current_user.id,
            project_id=project_id,
            file_path=os.path.relpath(file_path, current_app.config.get('UPLOAD_FOLDER')),
            status='pending'
        )
        db.session.add(new_submission)
        db.session.commit()

        # TODO: Trigger Gemini AI Task here (enqueue background job)
        return json_response(True, "Thesis uploaded. AI analysis started.",
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

@submissions_bp.route('/status/<int:submission_id>', methods=['GET'])
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

    return json_response(True, "Status fetched", {
        "status": submission.status,
        "ai_score": submission.ai_score,
        "ai_feedback": submission.ai_feedback
    })

# --- 2. PROFESSOR & ADMIN ENDPOINTS ---

@submissions_bp.route('/project/<int:project_id>', methods=['GET'])
@auth_token_required
@roles_accepted('professor', 'admin')
def get_project_submissions(project_id):
    """List of all work submitted to a specific project."""
    project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first_or_404()
    if current_user.has_role('professor') and project.professor_id != current_user.id:
        return json_response(False, "Unauthorized", None, 403)

    submissions = Submission.query.filter_by(project_id=project_id).order_by(Submission.created_at.desc()).all()
    return json_response(True, "Fetched project submissions", submission_schema.dump(submissions, many=True))

@submissions_bp.route('/stats/<int:project_id>', methods=['GET'])
@auth_token_required
@roles_accepted('professor', 'admin')
def get_project_stats(project_id):
    """Aggregated analytics for the professor's dashboard."""
    project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first_or_404()
    if current_user.has_role('professor') and project.professor_id != current_user.id:
        return json_response(False, "Unauthorized", None, 403)

    # Use SQLAlchemy case for conditional aggregation
    stats = db.session.query(
        func.avg(Submission.ai_score).label('avg_score'),
        func.count(Submission.id).label('total_submissions'),
        func.sum(case([(Submission.status == 'completed', 1)], else_=0)).label('processed')
    ).filter(Submission.project_id == project_id).first()

    return json_response(True, "Stats calculated", {
        "average_score": float(stats.avg_score or 0),
        "total_submissions": int(stats.total_submissions or 0),
        "processed_count": int(stats.processed or 0)
    })

@submissions_bp.route('/review/<int:submission_id>', methods=['PATCH'])
@auth_token_required
@roles_accepted('professor')
def review_submission(submission_id):
    """Professor overrides AI score or adds manual feedback."""
    data = request.get_json(silent=True) or {}
    submission = Submission.query.get_or_404(submission_id)
    project = submission.project

    if project.professor_id != current_user.id:
        return json_response(False, "Unauthorized", None, 403)

    # Validate inputs
    if 'status' in data:
        new_status = (data.get('status') or '').strip().lower()
        # Optionally validate against allowed statuses
        submission.status = new_status

    if 'ai_score' in data:
        try:
            submission.ai_score = float(data.get('ai_score'))
        except (TypeError, ValueError):
            return json_response(False, "Invalid ai_score value", None, 400)

    if 'ai_feedback' in data:
        submission.ai_feedback = data.get('ai_feedback')

    try:
        db.session.commit()
        return json_response(True, "Review updated", submission_schema.dump(submission))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to update review")
        return json_response(False, "Unable to update review", None, 500)

# --- 3. AI & SYSTEM ENDPOINTS ---

@submissions_bp.route('/re-evaluate/<int:submission_id>', methods=['POST'])
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

@submissions_bp.route('/<int:submission_id>', methods=['DELETE'])
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
        if submission.file_path and upload_root:
            abs_path = os.path.abspath(os.path.join(upload_root, submission.file_path))
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

@submissions_bp.route('/<int:submission_id>/download', methods=['GET'])
@auth_token_required
def download_submission(submission_id):
    """Securely streams the PDF file to the browser."""
    submission = Submission.query.get_or_404(submission_id)
    project = submission.project

    # Authorization Check
    is_owner = submission.student_id == current_user.id
    is_prof = current_user.has_role('professor') and project.professor_id == current_user.id
    is_admin = current_user.has_role('admin') and project.organization_id == current_user.organization_id

    if not (is_owner or is_prof or is_admin):
        return json_response(False, "Unauthorized to access this file", None, 403)

    upload_root = current_app.config.get('UPLOAD_FOLDER')
    if not upload_root:
        current_app.logger.error("UPLOAD_FOLDER not configured")
        return json_response(False, "Server misconfiguration", None, 500)

    # Ensure submission.file_path is a relative path (no leading slash)
    rel_path = (submission.file_path or "").lstrip("/\\")
    if not rel_path:
        current_app.logger.warning("Submission %s has empty file_path", submission_id)
        return json_response(False, "File not available", None, 404)

    try:
        # safe_join will raise NotFound if the final path is outside the directory
        abs_path = safe_join(upload_root, rel_path)
    except Exception:
        current_app.logger.exception("Unsafe file path for submission %s: %s", submission_id, rel_path)
        return json_response(False, "Invalid file path", None, 400)

    if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        current_app.logger.warning("File missing for submission %s at %s", submission_id, abs_path)
        return json_response(False, "File not found", None, 404)

    # Use a safe download filename for the client
    download_name = secure_filename(os.path.basename(rel_path)) or f"submission-{submission_id}.pdf"

    try:
        # For production, consider using X-Accel-Redirect or X-Sendfile instead of streaming via Flask
        return send_file(
            abs_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/pdf',
            conditional=True  # allows range requests if supported by server
        )
    except Exception:
        current_app.logger.exception("Failed to send file for submission %s", submission_id)
        # If send_file raises, return a JSON error rather than raw traceback
        return json_response(False, "Failed to deliver file", None, 500)

@submissions_bp.route('/evaluate/<int:submission_id>', methods=['POST'])
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
    if submission.status in ('processing', 'queued', 'pending'):
        return json_response(False, "Analysis already in progress or queued", None, 400)

    # Ensure file exists before queuing
    upload_root = current_app.config.get('UPLOAD_FOLDER')
    file_path = submission.file_path or ""
    abs_path = os.path.abspath(os.path.join(upload_root or "", file_path))
    if not upload_root or not os.path.isfile(abs_path) or not abs_path.startswith(os.path.abspath(upload_root)):
        return json_response(False, "Submission file not available", None, 404)

    # Mark pending state and dispatch to Celery
    try:
        submission.status = 'pending'
        db.session.commit()
        
        # DISPATCH TO CELERY
        process_thesis_task.delay(submission.id)

        return json_response(True, "AI evaluation queued successfully", {"submission_id": submission.id}, 202)

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to mark submission pending %s", submission_id)
        return json_response(False, "Unable to queue evaluation", None, 500)
