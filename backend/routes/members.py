# members.py
from flask import Blueprint, request, jsonify, current_app
from flask_security import roles_accepted, auth_token_required, current_user
from extentions import db, mail  # mail is optional; replace with your mail helper
from models import (
    User,
    Role,
    ProfessorProfile,
    StudentProfile,
    Project,
    OneTimeToken, 
    Enrollment,
    Invite,
    )
from sqlalchemy.orm import joinedload
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime
from utils.mail_handler import send_onboarding_email
from utils.invite_helper import create_and_queue_invite
from flask_security.utils import hash_password
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import secrets
import logging
import re
from schemas import user_schema

members_bp = Blueprint('members', __name__, url_prefix='/api/members')
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

# -------------------------
# Helpers
# -------------------------
def _normalize_email(email: str) -> str:
    return (email or '').strip().lower()

def _validate_password(password: str) -> bool:
    return bool(password) and len(password) >= 8

def _send_onboarding_email(to_email: str, name: str, onboarding_url: str, purpose: str):
    """
    Interface to the centralized mail handler.
    """
    # Simply delegate to the utility function you created
    success = send_onboarding_email(
        to_email=to_email,
        name=name,
        onboarding_url=onboarding_url,
        purpose=purpose,
        send_async=True  # Respects your USE_CELERY config
    )
    
    if not success:
        # We log the failure here; the utility already logged the specifics
        logger.error("Member onboarding email failed for %s", to_email)

# -------------------------
# 1) Invite Professor (admin-only)
# -------------------------
@members_bp.route('/invite-professor', methods=['POST'])
@auth_token_required
@roles_accepted('admin')
def invite_professor():
    """
    Admin invites a professor to the current admin's organization.
    Persists an Invite record and queues a Celery task to send the email.
    """
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('name') or '').strip()
    email = _normalize_email(data.get('email'))
    
    # department is typically collected when the user actually accepts the invite
    # but you can pass it to the helper if you want it stored in the invite row

    # 1. Validation
    if not name or not email or not EMAIL_RE.match(email):
        return jsonify({"error": "Valid name and email required"}), 400

    # 2. Check for existing user to prevent duplicate accounts/invites
    if User.query.filter(func.lower(User.email) == email).first():
        return jsonify({"error": "User with this email already exists"}), 409

    # 3. Use the persisted helper to create DB row and queue Celery task
    try:
        invite_id = create_and_queue_invite(
            email=email,
            name=name,
            onboarding_base_url=current_app.config.get('FRONTEND_URL'), 
            purpose='professor_onboard',
            created_by_id=current_user.id
        )

        if invite_id:
            logger.info("Admin (id=%s) created invite %s for %s", current_user.id, invite_id, email)
            
            # SECURITY: Never return raw tokens in API responses.
            # For automated testing, query the DB directly or use the Invite model.
            response_data = {"message": "Invitation queued successfully", "invite_id": invite_id}

            # Only expose token in explicit TESTING mode (never in DEBUG alone)
            if current_app.config.get('TESTING'):
                invite = Invite.query.get(invite_id)
                response_data["token"] = invite.token

            return jsonify(response_data), 201
            
        return jsonify({"error": "Failed to process invitation"}), 500

    except Exception:
        logger.exception("Unexpected error creating invite for email=%s", email)
        return jsonify({"error": "Internal server error"}), 500
# -------------------------
# Import limiter from extentions
from extentions import limiter

# 2) Student Join (public-ish)
# -------------------------
@members_bp.route('/student-join', methods=['POST'])
@limiter.limit("5 per hour")
def student_join():
    """
    Students register themselves using a Project's unique join_code.
    New student inherits the project's organization and is optionally activated.
    """
    data = request.get_json(force=True, silent=True) or {}
    join_code = (data.get('join_code') or '').strip()
    email = _normalize_email(data.get('email'))
    password = data.get('password') or ''
    name = (data.get('name') or 'Student').strip()
    major = (data.get('major') or 'Undeclared').strip()
    try:
        semester = int(data.get('semester', 1))
    except (TypeError, ValueError):
        semester = 1

    if not join_code or not email or not password:
        return jsonify({"error": "Missing join code, email, or password"}), 400

    if not EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email format"}), 400

    if not _validate_password(password):
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    # Verify project exists and is active
    project = Project.query.filter_by(join_code=join_code, status='active').first()
    if not project:
        return jsonify({"error": "Invalid or inactive join code"}), 404

    # Enforce enrollment cap
    max_enrollments = current_app.config.get('MAX_ENROLLMENTS_PER_PROJECT', 500)
    current_count = Enrollment.query.filter_by(project_id=project.id, is_active=True).count()
    if current_count >= max_enrollments:
        return jsonify({"error": "This project has reached its enrollment limit"}), 403

    # Ensure student role exists
    student_role = Role.query.filter(func.lower(Role.name) == 'student').first()
    if not student_role:
        logger.error("Student role missing in system")
        return jsonify({"error": "Server misconfiguration"}), 500

    # Prevent duplicate accounts (case-insensitive)
    if User.query.filter(func.lower(User.email) == email).first():
        return jsonify({"error": "An account with this email already exists"}), 409

    try:
        new_user = User(
            name=name,
            email=email,
            password=hash_password(password),
            organization_id=project.organization_id,
            active=True  # consider False + email verification if desired
        )
        new_user.roles.append(student_role)
        db.session.add(new_user)
        db.session.flush()

        new_profile = StudentProfile(
            user_id=new_user.id,
            major=major,
            semester=semester
        )
        db.session.add(new_profile)

        new_enrollment = Enrollment(
            student_id=new_user.id,
            project_id=project.id
        )
        db.session.add(new_enrollment)

        db.session.commit()

        logger.info("Student created (id=%s) and joined project (id=%s)", new_user.id, project.id)
        return jsonify({
            "message": "Account created and joined project successfully",
            "student_id": new_user.id,
            "organization_name": project.organization.name
        }), 201

    except IntegrityError:
        db.session.rollback()
        logger.exception("IntegrityError creating student for email=%s", email)
        return jsonify({"error": "An account with this email already exists"}), 409
    except Exception:
        db.session.rollback()
        logger.exception("Unexpected error in student_join for join_code=%s email=%s", join_code, email)
        return jsonify({"error": "Internal server error"}), 500

@members_bp.route('/join-project', methods=['POST'])
@auth_token_required
@roles_accepted('student')
def join_project_for_existing_student():
    """Allow an authenticated student to join an active project using only the join code."""
    data = request.get_json(force=True, silent=True) or {}
    join_code = (data.get('join_code') or '').strip()

    if not join_code:
        return jsonify({"error": "Join code is required"}), 400

    project = Project.query.filter_by(join_code=join_code, status='active').first()
    if not project:
        return jsonify({"error": "Invalid or inactive join code"}), 404

    if current_user.organization_id != project.organization_id:
        return jsonify({"error": "You can only join projects from your own organization"}), 403

    max_enrollments = current_app.config.get('MAX_ENROLLMENTS_PER_PROJECT', 500)
    current_count = Enrollment.query.filter_by(project_id=project.id, is_active=True).count()
    if current_count >= max_enrollments:
        return jsonify({"error": "This project has reached its enrollment limit"}), 403

    existing_enrollment = Enrollment.query.filter_by(project_id=project.id, student_id=current_user.id).first()
    if existing_enrollment and existing_enrollment.is_active:
        return jsonify({"message": "You are already enrolled in this project"}), 200

    try:
        if existing_enrollment:
            existing_enrollment.is_active = True
        else:
            db.session.add(Enrollment(student_id=current_user.id, project_id=project.id, is_active=True))

        db.session.commit()
        logger.info("Student %s joined project %s via dashboard join code", current_user.id, project.id)
        return jsonify({"message": "Joined project successfully", "project_id": project.id}), 200
    except Exception:
        db.session.rollback()
        logger.exception("Unexpected error joining project for student_id=%s join_code=%s", current_user.id, join_code)
        return jsonify({"error": "Internal server error"}), 500

# -------------------------
# 3) Invite Flow (Public)
# -------------------------
@members_bp.route('/invite-details', methods=['GET'])
def get_invite_details():
    """
    Public endpoint to fetch invite info for the onboarding form.
    """
    token = request.args.get('token')
    if not token:
        return jsonify({"error": "Token is required"}), 400
    
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        # Decode token to verify integrity
        data = serializer.loads(token, max_age=3600*24*7) # 7 day limit
        email = data.get('email')
    except Exception:
        return jsonify({"error": "Invalid or expired invitation link"}), 400
    
    invite = Invite.query.filter_by(token=token, email=email).first()
    if not invite or invite.status == 'accepted':
        return jsonify({"error": "Invitation not found or already used"}), 404
    
    if invite.expires_at.replace(tzinfo=None) < datetime.utcnow():
        return jsonify({"error": "This invitation has expired"}), 400
        
    return jsonify({
        "email": invite.email,
        "name": invite.name,
        "purpose": invite.purpose
    }), 200

@members_bp.route('/accept-invite', methods=['POST'])
def accept_invite():
    """
    Professor submits the onboarding form to create their account.
    """
    data = request.get_json() or {}
    token = data.get('token')
    password = data.get('password')
    name = data.get('name')
    department = data.get('department')
    
    if not all([token, password, name, department]):
        return jsonify({"error": "Missing required fields"}), 400
        
    if not _validate_password(password):
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        token_data = serializer.loads(token, max_age=3600*24*7)
        email = token_data.get('email')
    except Exception:
        return jsonify({"error": "Invalid or expired invitation link"}), 400
        
    invite = Invite.query.filter_by(token=token, email=email).first()
    if not invite or invite.status == 'accepted':
        return jsonify({"error": "Invitation not found or already used"}), 404
        
    # Double check user doesn't exist
    if User.query.filter(func.lower(User.email) == email.lower()).first():
        return jsonify({"error": "An account with this email already exists"}), 409

    # Find the admin who created the invite to bind the professor to the same organization
    inviter = User.query.get(invite.created_by_id)
    if not inviter:
        return jsonify({"error": "The organization admin who invited you no longer exists"}), 500
        
    professor_role = Role.query.filter(func.lower(Role.name) == 'professor').first()
    if not professor_role:
        return jsonify({"error": "Professor role not configured in system"}), 500
    
    try:
        new_user = User(
            name=name,
            email=email,
            password=hash_password(password),
            organization_id=inviter.organization_id,
            active=True
        )
        new_user.roles.append(professor_role)
        db.session.add(new_user)
        db.session.flush()
        
        new_profile = ProfessorProfile(
            user_id=new_user.id,
            department=department
        )
        db.session.add(new_profile)
        
        # Mark invite as accepted
        invite.status = 'accepted'
        db.session.commit()
        
        logger.info("Professor created via invite (id=%s) email=%s", new_user.id, email)
        return jsonify({"message": "Welcome onboard! Your account is ready. Please log in."}), 201
        
    except Exception as e:
        db.session.rollback()
        logger.exception("Error during professor invite acceptance")
        return jsonify({"error": "Failed to complete setup. Please contact support."}), 500

# -------------------------
# 4) Member Management (Admin only)
# -------------------------
@members_bp.route('/', methods=['GET'])
@auth_token_required
@roles_accepted('admin')
def list_members():
    """
    List all members in the admin's organization.
    """
    role_filter = request.args.get('role')
    query = User.query.options(joinedload(User.roles))\
        .filter_by(organization_id=current_user.organization_id)
    
    if role_filter:
        query = query.join(User.roles).filter(func.lower(Role.name) == role_filter.lower())
        
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        "success": True,
        "members": user_schema.dump(pagination.items, many=True),
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages
    }), 200

@members_bp.route('/<member_id>/status', methods=['PATCH'])
@auth_token_required
@roles_accepted('admin')
def toggle_member_status(member_id):
    """
    Toggle a user's active status.
    """
    user = User.query.filter_by(id=member_id, organization_id=current_user.organization_id).first_or_404()
    
    # Prevent self-deactivation (Admin must always have at least one active account)
    if user.id == current_user.id:
        return jsonify({"error": "Security check: You cannot deactivate your own administrative account."}), 400
        
    user.active = not user.active
    try:
        db.session.commit()
        action = "activated" if user.active else "deactivated"
        logger.info("Admin %s %s user %s", current_user.id, action, user.id)
        return jsonify({"message": f"User account successfully {action}."}), 200
    except Exception:
        db.session.rollback()
        logger.exception("Error toggling user status")
        return jsonify({"error": "Unable to update user status at this time."}), 500


