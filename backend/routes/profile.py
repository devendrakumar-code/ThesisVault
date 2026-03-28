from flask import Blueprint, request, jsonify, current_app
from flask_security import auth_token_required, current_user
from extentions import db
from models import User, ProfessorProfile, StudentProfile
from schemas import user_schema
from sqlalchemy.exc import SQLAlchemyError

profiles_bp = Blueprint('profiles', __name__, url_prefix='/api/profiles')

MAX_NAME_LENGTH = 200
MAX_DEPT_LENGTH = 120
MAX_MAJOR_LENGTH = 120

def json_response(success, message, data=None, code=200):
    return jsonify({"success": success, "message": message, "data": data}), code

@profiles_bp.route('/me', methods=['GET'])
@auth_token_required
def get_my_profile():
    """Returns the logged-in user's data and their specific profile type."""
    try:
        data = user_schema.dump(current_user)

        # Attach role-specific details safely
        details = {}
        if current_user.has_role('professor'):
            prof = ProfessorProfile.query.filter_by(user_id=current_user.id).first()
            if prof:
                details = {
                    "department": prof.department
                }
        elif current_user.has_role('student'):
            stud = StudentProfile.query.filter_by(user_id=current_user.id).first()
            if stud:
                details = {
                    "major": stud.major,
                    "semester": stud.semester
                }

        data['details'] = details
        return json_response(True, "Profile fetched", data, 200)
    except Exception:
        current_app.logger.exception("Failed to fetch profile for user %s", getattr(current_user, "id", None))
        return json_response(False, "Unable to fetch profile", None, 500)

@profiles_bp.route('/me', methods=['PATCH'])
@auth_token_required
def update_my_profile():
    """Allows users to update their own name or role-specific details."""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict) or not payload:
        return json_response(False, "No data provided", None, 400)

    # Only allow explicit fields
    allowed_user_fields = {'name'}
    allowed_prof_fields = {'department'}
    allowed_student_fields = {'major', 'semester'}

    # Collect changes
    user_changed = False
    prof_changed = False
    stud_changed = False

    # Validate and apply user-level fields
    if 'name' in payload:
        name = (payload.get('name') or '').strip()
        if not name:
            return json_response(False, "Name cannot be empty", None, 400)
        if len(name) > MAX_NAME_LENGTH:
            return json_response(False, f"Name too long (max {MAX_NAME_LENGTH})", None, 400)
        current_user.name = name
        user_changed = True

    # Role-specific updates
    try:
        # Use a transaction so either all changes commit or none
        with db.session.begin_nested():
            if current_user.has_role('professor'):
                prof = ProfessorProfile.query.filter_by(user_id=current_user.id).first()
                # Create profile row if missing
                if not prof:
                    prof = ProfessorProfile(user_id=current_user.id)
                    db.session.add(prof)

                if 'department' in payload:
                    dept = (payload.get('department') or '').strip()
                    if not dept:
                        return json_response(False, "Department cannot be empty", None, 400)
                    if len(dept) > MAX_DEPT_LENGTH:
                        return json_response(False, f"Department too long (max {MAX_DEPT_LENGTH})", None, 400)
                    prof.department = dept
                    prof_changed = True

            elif current_user.has_role('student'):
                stud = StudentProfile.query.filter_by(user_id=current_user.id).first()
                if not stud:
                    stud = StudentProfile(user_id=current_user.id)
                    db.session.add(stud)

                if 'major' in payload:
                    major = (payload.get('major') or '').strip()
                    if not major:
                        return json_response(False, "Major cannot be empty", None, 400)
                    if len(major) > MAX_MAJOR_LENGTH:
                        return json_response(False, f"Major too long (max {MAX_MAJOR_LENGTH})", None, 400)
                    stud.major = major
                    stud_changed = True

                if 'semester' in payload:
                    sem = payload.get('semester')
                    # Accept numeric or string that can be coerced to int
                    try:
                        sem_int = int(sem)
                        if sem_int < 0:
                            return json_response(False, "Semester must be non-negative", None, 400)
                        stud.semester = sem_int
                        stud_changed = True
                    except (TypeError, ValueError):
                        return json_response(False, "Invalid semester value", None, 400)

            # Prevent role changes via this endpoint
            if 'roles' in payload or 'role' in payload:
                return json_response(False, "Role changes are not allowed here", None, 403)

            # Commit nested transaction; outer commit below
            db.session.flush()

        # Commit outer transaction
        db.session.commit()

        # Return updated profile
        data = user_schema.dump(current_user)
        # Attach updated details
        details = {}
        if current_user.has_role('professor'):
            prof = ProfessorProfile.query.filter_by(user_id=current_user.id).first()
            if prof:
                details = {"department": prof.department}
        elif current_user.has_role('student'):
            stud = StudentProfile.query.filter_by(user_id=current_user.id).first()
            if stud:
                details = {"major": stud.major, "semester": stud.semester}
        data['details'] = details

        return json_response(True, "Profile updated", data, 200)

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Database error updating profile for user %s", current_user.id)
        return json_response(False, "Database error while updating profile", None, 500)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unexpected error updating profile for user %s", current_user.id)
        return json_response(False, "Unable to update profile", None, 500)

