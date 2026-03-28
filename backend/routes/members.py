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
    )
from utils.mail_handler import send_onboarding_email
from utils.invite_helper import create_and_queue_invite
from flask_security.utils import hash_password
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import secrets
import logging
import re

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
            return jsonify({
                "message": "Invite persisted and queued", 
                "invite_id": invite_id
            }), 201
            
        return jsonify({"error": "Failed to process invitation"}), 500

    except Exception:
        logger.exception("Unexpected error creating invite for email=%s", email)
        return jsonify({"error": "Internal server error"}), 500
# -------------------------
# 2) Student Join (public-ish)
# -------------------------
@members_bp.route('/student-join', methods=['POST'])
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

