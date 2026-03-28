from flask import Blueprint, request, jsonify
from flask_security import roles_accepted, auth_token_required, current_user
from extentions import db
from models import Project, User, Submission, Enrollment,  create_project_safe
from schemas import project_schema, user_schema, submission_schema
from sqlalchemy.exc import IntegrityError
from decorators import subscription_required, limit_check
import random
import string

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')

ALLOWED_STATUSES = {'active', 'completed', 'archived'}
JOIN_CODE_LENGTH = 8
JOIN_CODE_ATTEMPTS = 5

def json_error(message, code=400):
    return jsonify({"success": False, "message": message}), code

# 1. CREATE PROJECT (Professor Only)
@projects_bp.route('/', methods=['POST'])
@auth_token_required
@roles_accepted('professor')
@subscription_required()
@limit_check()
def create_project():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return json_error("Project name is required", 400)

    try:
        new_project = create_project_safe(
            db.session,
            name=name,
            organization_id=current_user.organization_id,
            professor_id=current_user.id,
            status='active'
        )
        db.session.commit()
        return jsonify({"success": True, "message": "Project created", "data": project_schema.dump(new_project)}), 201
    except IntegrityError:
        db.session.rollback()
        return json_error("A project with that name or join code already exists", 409)
    except Exception:
        db.session.rollback()
        return json_error("Unable to create project", 500)

# 2. GET MY PROJECTS (Context-Aware)
@projects_bp.route('/', methods=['GET'])
@auth_token_required
def get_my_projects():
    if current_user.has_role('professor'):
        projects = Project.query.filter_by(
            organization_id=current_user.organization_id,
            professor_id=current_user.id
        )
    elif current_user.has_role('student'):
        projects = [enrollment.project for enrollment in current_user.project_enrollments if enrollment.is_active]
        return jsonify(project_schema.dump(projects, many=True)), 200
    else:
        projects = Project.query.filter_by(organization_id=current_user.organization_id)

    # Optional: add pagination params ?page=1&per_page=25
    return jsonify(project_schema.dump(projects.all(), many=True)), 200

# 3. GET PROJECT DETAILS
@projects_bp.route('/<int:project_id>', methods=['GET'])
@auth_token_required
def get_project_details(project_id):
    project = Project.query.filter_by(
        id=project_id,
        organization_id=current_user.organization_id
    ).first_or_404()
    return jsonify({"success": True, "data": project_schema.dump(project)}), 200

# 4. UPDATE PROJECT (Professor Only)
@projects_bp.route('/<int:project_id>', methods=['PUT'])
@auth_token_required
@roles_accepted('professor')
def update_project(project_id):
    data = request.get_json(silent=True) or {}
    project = Project.query.filter_by(id=project_id, professor_id=current_user.id).first_or_404()

    if 'name' in data:
        new_name = (data.get('name') or '').strip()
        if not new_name:
            return json_error("Project name cannot be empty", 400)
        project.name = new_name

    try:
        db.session.commit()
        return jsonify({"success": True, "message": "Project updated", "data": project_schema.dump(project)}), 200
    except IntegrityError:
        db.session.rollback()
        return json_error("Update conflicts with existing data", 409)
    except Exception:
        db.session.rollback()
        return json_error("Unable to update project", 500)

# 5. TOGGLE PROJECT STATUS (Active/Completed/Archived)
@projects_bp.route('/<int:project_id>/status', methods=['PATCH'])
@auth_token_required
@roles_accepted('professor', 'admin')
def toggle_project_status(project_id):
    data = request.get_json(silent=True) or {}
    new_status = (data.get('status') or '').strip().lower()
    if new_status not in ALLOWED_STATUSES:
        return json_error(f"Invalid status. Allowed: {', '.join(ALLOWED_STATUSES)}", 400)

    project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first_or_404()

    if current_user.has_role('professor') and project.professor_id != current_user.id:
        return json_error("Unauthorized", 403)

    project.status = new_status
    try:
        db.session.commit()
        return jsonify({"success": True, "message": f"Status changed to {new_status}"}), 200
    except Exception:
        db.session.rollback()
        return json_error("Unable to change status", 500)

# 6. REGENERATE JOIN CODE
@projects_bp.route('/<int:project_id>/regenerate-code', methods=['POST'])
@auth_token_required
@roles_accepted('professor')
def regenerate_join_code(project_id):
    project = Project.query.filter_by(id=project_id, professor_id=current_user.id).first_or_404()

    for _ in range(JOIN_CODE_ATTEMPTS):
        new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=JOIN_CODE_LENGTH))
        if not Project.query.filter_by(join_code=new_code).first():
            project.join_code = new_code
            try:
                db.session.commit()
                return jsonify({"success": True, "message": "New join code generated", "join_code": new_code}), 200
            except IntegrityError:
                db.session.rollback()
                # try again if a race created the same code
                continue
            except Exception:
                db.session.rollback()
                return json_error("Unable to generate join code", 500)

    return json_error("Code generation failed, please try again", 500)

# 7. GET PROJECT STUDENTS (Roster)
@projects_bp.route('/<int:project_id>/students', methods=['GET'])
@auth_token_required
@roles_accepted('professor', 'admin')
def get_project_students(project_id):
    project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first_or_404()

    if current_user.has_role('professor') and project.professor_id != current_user.id:
        return json_error("Unauthorized", 403)

    enrollments = Enrollment.query.filter_by(project_id=project.id, is_active=True).all()
    students = [e.student for e in enrollments]
    return jsonify({"success": True, "data": user_schema.dump(students, many=True)}), 200

# 8. REMOVE STUDENT FROM PROJECT (soft-unenroll)
@projects_bp.route('/<int:project_id>/students/<int:student_id>', methods=['DELETE'])
@auth_token_required
@roles_accepted('professor', 'admin')
def remove_student_from_project(project_id, student_id):
    project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first_or_404()

    if current_user.has_role('professor') and project.professor_id != current_user.id:
        return json_error("Unauthorized", 403)

    enrollment = Enrollment.query.filter_by(project_id=project.id, student_id=student_id).first()
    if not enrollment:
        return json_error("Enrollment not found", 404)

    # Soft-delete for auditability
    enrollment.is_active = False
    try:
        db.session.commit()
        return jsonify({"success": True, "message": "Student unenrolled from project"}), 200
    except Exception:
        db.session.rollback()
        return json_error("Unable to unenroll student", 500)

# 9. GET MY SUBMISSIONS (Student Only)
@projects_bp.route('/<int:project_id>/my-submissions', methods=['GET'])
@auth_token_required
@roles_accepted('student')
def get_my_submissions(project_id):
    submissions = Submission.query.filter_by(
        project_id=project_id,
        student_id=current_user.id
    ).all()
    return jsonify({"success": True, "data": submission_schema.dump(submissions, many=True)}), 200

