from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, request, jsonify, current_app
from flask_security import auth_token_required, current_user, roles_accepted

from extentions import db
from models import Project, Milestone, Submission
from schemas import MilestoneSchema

milestones_bp = Blueprint('milestones', __name__, url_prefix='/api/milestones')
milestone_schema = MilestoneSchema()

MAX_MILESTONES_PER_PROJECT = 10


def json_response(success, message, data=None, code=200):
    return jsonify({'success': success, 'message': message, 'data': data}), code


def _milestone_timezone():
    return ZoneInfo(current_app.config.get('CELERY_TIMEZONE', 'Asia/Kolkata'))


def _to_local_naive(dt_value):
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        return dt_value
    return dt_value.astimezone(_milestone_timezone()).replace(tzinfo=None)


def _current_local_naive():
    return datetime.now(_milestone_timezone()).replace(tzinfo=None)


def _effective_submission_deadline(submission, milestone):
    if submission and submission.review_status == 'rejected' and submission.resubmission_deadline:
        override_deadline = _to_local_naive(submission.resubmission_deadline)
        if override_deadline:
            return override_deadline
    return _to_local_naive(milestone.deadline)


@milestones_bp.route('/project/<project_id>', methods=['GET'])
@auth_token_required
def list_milestones(project_id):
    """Everyone enrolled (professor or student) can list milestones."""
    Project.query.get_or_404(project_id)
    milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.order_num).all()

    now = _current_local_naive()
    result = []
    for milestone in milestones:
        start_at = _to_local_naive(milestone.starts_at)
        serialized = milestone_schema.dump(milestone)
        submission = None
        effective_deadline = _to_local_naive(milestone.deadline)

        if current_user.has_role('student'):
            submission = Submission.query.filter_by(milestone_id=milestone.id, student_id=current_user.id).first()
            effective_deadline = _effective_submission_deadline(submission, milestone)

        if start_at and now < start_at:
            serialized['state'] = 'dormant'
        elif effective_deadline and now <= effective_deadline:
            serialized['state'] = 'active'
        else:
            serialized['state'] = 'locked'

        if current_user.has_role('student'):
            can_resubmit = bool(
                submission
                and submission.review_status == 'rejected'
                and effective_deadline
                and now <= effective_deadline
            )
            serialized['my_submission'] = {
                'id': submission.id,
                'status': submission.status,
                'review_status': submission.review_status,
                'grade': submission.grade,
                'created_at': submission.created_at.isoformat() if submission.created_at else None,
                'rejection_extension_days': submission.rejection_extension_days,
                'resubmission_deadline': submission.resubmission_deadline.isoformat() if submission.resubmission_deadline else None,
                'can_resubmit': can_resubmit,
            } if submission else None
        else:
            serialized['submission_count'] = Submission.query.filter_by(milestone_id=milestone.id).count()

        result.append(serialized)

    return json_response(True, 'Milestones fetched', result)


@milestones_bp.route('/project/<project_id>', methods=['POST'])
@auth_token_required
@roles_accepted('professor')
def create_milestone(project_id):
    project = Project.query.get_or_404(project_id)
    if project.professor_id != current_user.id:
        return json_response(False, 'Unauthorized', None, 403)

    current_count = Milestone.query.filter_by(project_id=project_id).count()
    if current_count >= MAX_MILESTONES_PER_PROJECT:
        return json_response(False, f'Maximum {MAX_MILESTONES_PER_PROJECT} milestones per project', None, 400)

    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return json_response(False, 'Title is required', None, 400)

    try:
        starts_at = datetime.fromisoformat(data['starts_at'].replace('Z', '+00:00'))
        deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
    except (KeyError, ValueError):
        return json_response(False, 'Valid starts_at and deadline (ISO 8601) are required', None, 400)

    if deadline <= starts_at:
        return json_response(False, 'Deadline must be after start date', None, 400)

    last = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.order_num.desc()).first()
    order_num = (last.order_num + 1) if last else 1

    milestone = Milestone(
        project_id=project_id,
        title=title,
        description=(data.get('description') or '').strip() or None,
        order_num=order_num,
        starts_at=starts_at,
        deadline=deadline,
    )
    db.session.add(milestone)
    db.session.commit()
    return json_response(True, 'Milestone created', milestone_schema.dump(milestone), 201)


@milestones_bp.route('/<milestone_id>', methods=['PATCH'])
@auth_token_required
@roles_accepted('professor')
def update_milestone(milestone_id):
    milestone = Milestone.query.get_or_404(milestone_id)
    if milestone.project.professor_id != current_user.id:
        return json_response(False, 'Unauthorized', None, 403)

    data = request.get_json(silent=True) or {}

    if 'title' in data:
        title = (data['title'] or '').strip()
        if not title:
            return json_response(False, 'Title cannot be empty', None, 400)
        milestone.title = title

    if 'description' in data:
        milestone.description = (data['description'] or '').strip() or None

    if 'starts_at' in data:
        try:
            milestone.starts_at = datetime.fromisoformat(data['starts_at'].replace('Z', '+00:00'))
        except ValueError:
            return json_response(False, 'Invalid starts_at format', None, 400)

    if 'deadline' in data:
        try:
            milestone.deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
        except ValueError:
            return json_response(False, 'Invalid deadline format', None, 400)

    if milestone.deadline <= milestone.starts_at:
        return json_response(False, 'Deadline must be after start date', None, 400)

    db.session.commit()
    return json_response(True, 'Milestone updated', milestone_schema.dump(milestone))


@milestones_bp.route('/<milestone_id>', methods=['DELETE'])
@auth_token_required
@roles_accepted('professor')
def delete_milestone(milestone_id):
    milestone = Milestone.query.get_or_404(milestone_id)
    if milestone.project.professor_id != current_user.id:
        return json_response(False, 'Unauthorized', None, 403)

    db.session.delete(milestone)
    db.session.commit()
    return json_response(True, 'Milestone deleted')
