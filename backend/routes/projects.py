import json
import logging
import os
import random
import string
import uuid
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_security import auth_token_required, current_user, roles_accepted
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from decorators import limit_check, subscription_required
from extentions import db
from models import (
    ActivityLog,
    Enrollment,
    Milestone,
    Organization,
    Project,
    Submission,
    User,
    create_project_safe,
)
from schemas import project_schema, student_submission_schema, submission_schema, user_schema

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')
logger = logging.getLogger(__name__)

ALLOWED_STATUSES = {'active', 'completed', 'archived'}
JOIN_CODE_LENGTH = 8
JOIN_CODE_ATTEMPTS = 5
MAX_MILESTONES_PER_PROJECT = 10
ALLOWED_PROBLEM_STATEMENT_EXTENSIONS = {'pdf'}
PROBLEM_STATEMENT_SUBDIR = 'problem_statements'


def json_error(message, code=400):
    return jsonify({'success': False, 'message': message}), code

def _student_project_access_query():
    return Enrollment.query.join(Project).filter(
        Enrollment.student_id == current_user.id,
        or_(Enrollment.is_active == True, Project.status == 'completed')
    )



def _request_payload():
    if request.content_type and 'multipart/form-data' in request.content_type:
        return request.form.to_dict()
    return request.get_json(silent=True) or {}


def _parse_iso_datetime(value, field_name):
    try:
        return datetime.fromisoformat((value or '').replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError(f'Valid {field_name} (ISO 8601) is required') from exc


def _parse_milestones(raw_value):
    if raw_value in (None, '', []):
        return []

    if isinstance(raw_value, list):
        milestone_items = raw_value
    elif isinstance(raw_value, str):
        try:
            milestone_items = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise ValueError('Milestones must be valid JSON') from exc
    else:
        raise ValueError('Milestones must be a JSON array')

    if not isinstance(milestone_items, list):
        raise ValueError('Milestones must be a JSON array')

    if len(milestone_items) > MAX_MILESTONES_PER_PROJECT:
        raise ValueError(f'Maximum {MAX_MILESTONES_PER_PROJECT} milestones allowed per project')

    validated = []
    for index, item in enumerate(milestone_items, start=1):
        if not isinstance(item, dict):
            raise ValueError('Each milestone must be an object')

        title = (item.get('title') or '').strip()
        if not title:
            raise ValueError(f'Milestone {index} title is required')

        starts_at = _parse_iso_datetime(item.get('starts_at'), f'milestone {index} starts_at')
        deadline = _parse_iso_datetime(item.get('deadline'), f'milestone {index} deadline')
        if deadline <= starts_at:
            raise ValueError(f'Milestone {index} deadline must be after its start date')

        validated.append({
            'title': title,
            'description': (item.get('description') or '').strip() or None,
            'starts_at': starts_at,
            'deadline': deadline,
            'order_num': index,
        })

    return validated


def _problem_statement_upload_root():
    upload_root = current_app.config.get('UPLOAD_FOLDER')
    if not upload_root:
        raise RuntimeError('Server misconfiguration: UPLOAD_FOLDER not set')

    target = os.path.join(upload_root, PROBLEM_STATEMENT_SUBDIR)
    os.makedirs(target, exist_ok=True)
    return upload_root, target


def _save_problem_statement_file(upload_file):
    if not upload_file or not getattr(upload_file, 'filename', ''):
        return None

    filename = secure_filename(upload_file.filename)
    if not filename:
        raise ValueError('Problem statement file name is invalid')

    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if extension not in ALLOWED_PROBLEM_STATEMENT_EXTENSIONS:
        raise ValueError('Problem statement must be uploaded as a PDF')

    upload_root, target_dir = _problem_statement_upload_root()
    stored_name = f'{uuid.uuid4().hex}_{filename}'
    absolute_path = os.path.join(target_dir, stored_name)
    upload_file.save(absolute_path)
    return os.path.relpath(absolute_path, upload_root)


def _delete_relative_upload(relative_path):
    if not relative_path:
        return

    upload_root = current_app.config.get('UPLOAD_FOLDER')
    if not upload_root:
        return

    absolute_path = os.path.abspath(os.path.join(upload_root, relative_path))
    upload_root_abs = os.path.abspath(upload_root)
    if not absolute_path.startswith(upload_root_abs):
        return

    if os.path.isfile(absolute_path):
        os.remove(absolute_path)


@projects_bp.route('/', methods=['POST'])
@auth_token_required
@roles_accepted('professor')
@subscription_required()
@limit_check()
def create_project():
    data = _request_payload()
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip() or None

    if not name:
        return json_error('Project name is required', 400)

    try:
        milestones_payload = _parse_milestones(data.get('milestones'))
    except ValueError as exc:
        return json_error(str(exc), 400)

    stored_problem_statement = None
    try:
        if request.files:
            stored_problem_statement = _save_problem_statement_file(request.files.get('problem_statement_file'))

        org = db.session.query(Organization).filter_by(id=current_user.organization_id).with_for_update().first()
        if not org:
            _delete_relative_upload(stored_problem_statement)
            return json_error('Organization not found', 404)

        plan = org.plan
        if plan and org.active_projects >= plan.max_active_projects:
            db.session.rollback()
            _delete_relative_upload(stored_problem_statement)
            return json_error(f'Project limit reached for {plan.name} ({plan.max_active_projects}). Please upgrade.', 403)

        new_project = create_project_safe(
            db.session,
            name=name,
            description=description,
            problem_statement_file_url=stored_problem_statement,
            organization_id=current_user.organization_id,
            professor_id=current_user.id,
            status='active',
        )

        for milestone_data in milestones_payload:
            db.session.add(Milestone(project_id=new_project.id, **milestone_data))

        log = ActivityLog(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            action='PROJECT_CREATED',
            description=f"Project '{name}' created by {current_user.name}",
            metadata_json={
                'project_id': new_project.id,
                'milestone_count': len(milestones_payload),
                'has_problem_statement_file': bool(stored_problem_statement),
            },
        )
        db.session.add(log)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Project created', 'data': project_schema.dump(new_project)}), 201
    except ValueError as exc:
        db.session.rollback()
        _delete_relative_upload(stored_problem_statement)
        return json_error(str(exc), 400)
    except IntegrityError:
        db.session.rollback()
        _delete_relative_upload(stored_problem_statement)
        return json_error('A project with that name or join code already exists', 409)
    except Exception:
        db.session.rollback()
        _delete_relative_upload(stored_problem_statement)
        logger.exception('Unable to create project for professor_id=%s organization_id=%s', current_user.id, current_user.organization_id)
        return json_error('Unable to create project', 500)


@projects_bp.route('/', methods=['GET'])
@auth_token_required
def get_my_projects():
    if current_user.has_role('professor'):
        projects = Project.query.filter_by(
            organization_id=current_user.organization_id,
            professor_id=current_user.id,
        )
    elif current_user.has_role('student'):
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 25, type=int), 100)
        enrollments = _student_project_access_query().paginate(
            page=page, per_page=per_page, error_out=False
        )
        serialized_projects = []
        for enrollment in enrollments.items:
            project_data = project_schema.dump(enrollment.project)
            latest_reviewed_submission = Submission.query.filter(
                Submission.project_id == enrollment.project.id,
                Submission.student_id == current_user.id,
                Submission.grade.isnot(None)
            ).order_by(Submission.updated_at.desc(), Submission.created_at.desc()).first()
            latest_submission = Submission.query.filter_by(
                project_id=enrollment.project.id,
                student_id=current_user.id,
            ).order_by(Submission.updated_at.desc(), Submission.created_at.desc()).first()
            project_data['student_grade'] = latest_reviewed_submission.grade if latest_reviewed_submission else None
            project_data['student_review_status'] = latest_submission.review_status if latest_submission else None
            serialized_projects.append(project_data)
        return jsonify({
            'data': serialized_projects,
            'page': enrollments.page,
            'total_pages': enrollments.pages,
            'total': enrollments.total,
        }), 200
    else:
        projects = Project.query.filter_by(organization_id=current_user.organization_id)

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)
    paginated = projects.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'data': project_schema.dump(paginated.items, many=True),
        'page': paginated.page,
        'total_pages': paginated.pages,
        'total': paginated.total,
    }), 200


@projects_bp.route('/<project_id>', methods=['GET'])
@auth_token_required
def get_project_details(project_id):
    project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first_or_404()

    if current_user.has_role('student'):
        enrollment = _student_project_access_query().filter(Project.id == project_id).first()
        if not enrollment:
            return json_error('You are not enrolled in this project', 403)

    return jsonify({'success': True, 'data': project_schema.dump(project)}), 200


@projects_bp.route('/<project_id>', methods=['PUT'])
@auth_token_required
@roles_accepted('professor')
def update_project(project_id):
    data = request.get_json(silent=True) or {}
    project = Project.query.filter_by(id=project_id, professor_id=current_user.id).first_or_404()

    if 'name' in data:
        new_name = (data.get('name') or '').strip()
        if not new_name:
            return json_error('Project name cannot be empty', 400)
        project.name = new_name

    if 'description' in data:
        project.description = (data.get('description') or '').strip() or None

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Project updated', 'data': project_schema.dump(project)}), 200
    except IntegrityError:
        db.session.rollback()
        return json_error('Update conflicts with existing data', 409)
    except Exception:
        db.session.rollback()
        return json_error('Unable to update project', 500)


@projects_bp.route('/<project_id>/status', methods=['PATCH'])
@auth_token_required
@roles_accepted('professor', 'admin')
def toggle_project_status(project_id):
    data = request.get_json(silent=True) or {}
    new_status = (data.get('status') or '').strip().lower()
    if new_status not in ALLOWED_STATUSES:
        return json_error(f"Invalid status. Allowed: {', '.join(ALLOWED_STATUSES)}", 400)

    project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first_or_404()

    if current_user.has_role('professor') and project.professor_id != current_user.id:
        return json_error('Unauthorized', 403)

    project.status = new_status

    if new_status == 'archived':
        Enrollment.query.filter_by(project_id=project.id, is_active=True).update({'is_active': False}, synchronize_session=False)

    log = ActivityLog(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action='PROJECT_STATUS_CHANGED',
        description=f"Project '{project.name}' marked as {new_status} by {current_user.name}",
        metadata_json={'project_id': project.id, 'status': new_status},
    )
    db.session.add(log)

    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f"Project marked as {new_status}",
            'data': project_schema.dump(project),
        }), 200
    except Exception:
        db.session.rollback()
        return json_error('Unable to change status', 500)


@projects_bp.route('/<project_id>/regenerate-code', methods=['POST'])
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
                return jsonify({'success': True, 'message': 'New join code generated', 'join_code': new_code}), 200
            except IntegrityError:
                db.session.rollback()
                continue
            except Exception:
                db.session.rollback()
                return json_error('Unable to generate join code', 500)

    return json_error('Code generation failed, please try again', 500)


@projects_bp.route('/<project_id>/students', methods=['GET'])
@auth_token_required
@roles_accepted('professor', 'admin')
def get_project_students(project_id):
    project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first_or_404()

    if current_user.has_role('professor') and project.professor_id != current_user.id:
        return json_error('Unauthorized', 403)

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)
    paginated = Enrollment.query.filter_by(project_id=project.id, is_active=True).paginate(
        page=page, per_page=per_page, error_out=False
    )
    students = [e.student for e in paginated.items]
    return jsonify({
        'success': True,
        'data': user_schema.dump(students, many=True),
        'page': paginated.page,
        'total_pages': paginated.pages,
        'total': paginated.total,
    }), 200


@projects_bp.route('/students/all', methods=['GET'])
@auth_token_required
@roles_accepted('professor')
def get_all_managed_students():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)
    paginated = Enrollment.query.join(Project).filter(
        Project.professor_id == current_user.id,
        Enrollment.is_active == True,
    ).paginate(page=page, per_page=per_page, error_out=False)

    unique_students = {}
    for enrollment in paginated.items:
        project_info = {'id': enrollment.project.id, 'name': enrollment.project.name}
        if enrollment.student_id not in unique_students:
            student_data = user_schema.dump(enrollment.student)
            student_data['projects'] = [enrollment.project.name]
            student_data['managed_projects'] = [project_info]
            unique_students[enrollment.student_id] = student_data
        else:
            if enrollment.project.name not in unique_students[enrollment.student_id]['projects']:
                unique_students[enrollment.student_id]['projects'].append(enrollment.project.name)
            if not any(p['id'] == enrollment.project.id for p in unique_students[enrollment.student_id]['managed_projects']):
                unique_students[enrollment.student_id]['managed_projects'].append(project_info)

    return jsonify({
        'success': True,
        'data': list(unique_students.values()),
        'page': paginated.page,
        'total_pages': paginated.pages,
        'total': paginated.total,
    }), 200


@projects_bp.route('/<project_id>/students/<student_id>', methods=['DELETE'])
@auth_token_required
@roles_accepted('professor', 'admin')
def remove_student_from_project(project_id, student_id):
    project = Project.query.filter_by(id=project_id, organization_id=current_user.organization_id).first_or_404()

    if current_user.has_role('professor') and project.professor_id != current_user.id:
        return json_error('Unauthorized', 403)

    enrollment = Enrollment.query.filter_by(project_id=project.id, student_id=student_id).first()
    if not enrollment:
        return json_error('Enrollment not found', 404)

    enrollment.is_active = False
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Student unenrolled from project'}), 200
    except Exception:
        db.session.rollback()
        return json_error('Unable to unenroll student', 500)


@projects_bp.route('/<project_id>/my-submissions', methods=['GET'])
@auth_token_required
@roles_accepted('student')
def get_my_submissions(project_id):
    enrollment = _student_project_access_query().filter(Project.id == project_id).first()
    if not enrollment:
        return json_error('You are not enrolled in this project', 403)

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)
    pagination = Submission.query.filter_by(project_id=project_id, student_id=current_user.id).order_by(
        Submission.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'data': student_submission_schema.dump(pagination.items, many=True),
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    }), 200

