from flask import Blueprint, request, jsonify, current_app
from flask_security import auth_token_required, current_user
from extentions import db
from models import User, ProfessorProfile, StudentProfile
from schemas import user_schema
from sqlalchemy.exc import SQLAlchemyError
import os
import uuid
from werkzeug.utils import secure_filename

profiles_bp = Blueprint('profiles', __name__, url_prefix='/api/profiles')

MAX_NAME_LENGTH = 200
MAX_DEPT_LENGTH = 120
MAX_MAJOR_LENGTH = 120
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

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

@profiles_bp.route('/me', methods=['PATCH', 'POST'])
@auth_token_required
def update_my_profile():
    """Allows users to update their own name or role-specific details."""
    # Handle Multipart/Form-Data (for image uploads) or JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        payload = request.form.to_dict()
    else:
        payload = request.get_json(silent=True) or {}
    
    if not isinstance(payload, dict):
        return json_response(False, "Invalid data format", None, 400)

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

    # Image upload logic
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            # Use configured upload folder; fallback to 'uploads' in root_path
            upload_base = current_app.config.get('UPLOAD_FOLDER') or os.path.join(current_app.root_path, 'uploads')
            upload_folder = os.path.join(upload_base, 'profiles')
            os.makedirs(upload_folder, exist_ok=True)
            
            # Secure filename and add UUID to prevent collisions
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{current_user.id}_{uuid.uuid4().hex}.{ext}")
            file_path = os.path.join(upload_folder, filename)
            
            # Storage path to save in DB (relative to static server root)
            db_storage_path = f"uploads/profiles/{filename}"
            
            # Delete old image if it exists
            if current_user.profile_image:
                old_rel_path = current_user.profile_image.replace('uploads/', '', 1).lstrip('/')
                old_full_path = os.path.join(upload_base, old_rel_path)
                if os.path.exists(old_full_path):
                    try:
                        os.remove(old_full_path)
                    except Exception:
                        current_app.logger.warning("Failed to delete old profile image: %s", old_full_path)

            file.save(file_path)
            current_user.profile_image = db_storage_path
            user_changed = True
            current_app.logger.info("Profile image saved for user %s at %s", current_user.id, file_path)

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
