from flask import Blueprint, request, jsonify, current_app
from flask_security import auth_token_required, current_user, roles_accepted
from extentions import db
from models import Organization, Plan, User, Project, SubscriptionHistory, ActivityLog
from schemas import OrganizationSchema
from datetime import datetime, timezone, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

def json_response(success, message, data=None, code=200):
    return jsonify({"success": success, "message": message, "data": data}), code

@admin_bp.route('/plans', methods=['GET'])
@auth_token_required
@roles_accepted('admin')
def get_plans():
    """List all available subscription plans."""
    plans = Plan.query.all()
    return json_response(True, "Fetched plans", [
        {
            "id": p.id,
            "name": p.name,
            "max_active_projects": p.max_active_projects,
            "max_students": p.max_students,
            "monthly_ai_limit": p.monthly_ai_limit,
            "validity_days": p.validity_days,
            "features": p.features
        } for p in plans
    ])

@admin_bp.route('/organizations/me/upgrade', methods=['POST'])
@auth_token_required
@roles_accepted('admin')
def upgrade_my_org():
    """
    Demonstration endpoint to upgrade the current user's organization.
    In a real app, this would be triggered by a Stripe webhook.
    """
    data = request.get_json()
    new_plan_name = data.get('plan_name')
    if not new_plan_name:
        return json_response(False, "plan_name is required", None, 400)

    org = current_user.organization
    if not org:
        return json_response(False, "Organization not found", None, 404)

    new_plan = Plan.query.filter_by(name=new_plan_name).first()
    if not new_plan:
        return json_response(False, f"Plan '{new_plan_name}' not found", None, 404)

    old_plan_id = org.plan_id
    
    # 1. Update Organization
    org.plan_id = new_plan.id
    org.subscription_status = 'active'
    # Reset/Extend expiry based on new plan validity
    org.subscription_ends_at = datetime.now(timezone.utc) + timedelta(days=new_plan.validity_days)
    
    # 2. Log History (Requirement 2 & 3: Auditability)
    history = SubscriptionHistory(
        organization_id=org.id,
        old_plan_id=old_plan_id,
        new_plan_id=new_plan.id,
        change_reason=f"Admin Upgrade to {new_plan.name}"
    )
    db.session.add(history)

    # 3. Log Activity
    log = ActivityLog(
        user_id=current_user.id,
        organization_id=org.id,
        action="PLAN_UPGRADE",
        description=f"Upgraded from {org.plan.name if org.plan else 'None'} to {new_plan.name}"
    )
    db.session.add(log)

    try:
        db.session.commit()
        return json_response(True, f"Organization upgraded to {new_plan.name} successfully until {org.subscription_ends_at.strftime('%Y-%m-%d')}")
    except Exception as e:
        db.session.rollback()
        return json_response(False, f"Upgrade failed: {str(e)}", None, 500)

@admin_bp.route('/organizations/me/suspend', methods=['POST'])
@auth_token_required
@roles_accepted('admin')
def suspend_my_org():
    """Demonstration endpoint to suspend the organization (e.g., for non-payment)."""
    org = current_user.organization
    if not org: return json_response(False, "Org not found", None, 404)
    
    org.status = 'suspended'
    db.session.commit()
    return json_response(True, "Organization suspended. All API access (except Auth) will be blocked.")

@admin_bp.route('/organizations/me/resume', methods=['POST'])
@auth_token_required
@roles_accepted('admin')
def resume_my_org():
    """Demonstration endpoint to resume the organization."""
    org = current_user.organization
    if not org: return json_response(False, "Org not found", None, 404)
    
    org.status = 'active'
    db.session.commit()
    return json_response(True, "Organization resumed.")

@admin_bp.route('/organizations/me/history', methods=['GET'])
@auth_token_required
@roles_accepted('admin')
def get_my_org_history():
    """
    Returns the subscription history and activity logs for audit trails (Requirement 2 & 3).
    """
    org = current_user.organization
    if not org: return json_response(False, "Org not found", None, 404)
    
    # 1. Fetch Plan History
    history_records = SubscriptionHistory.query.filter_by(organization_id=org.id).order_by(SubscriptionHistory.created_at.desc()).all()
    history_data = [
        {
            "id": h.id,
            "old_plan": h.old_plan.name if h.old_plan else "Initial Signup",
            "new_plan": h.new_plan.name,
            "reason": h.change_reason,
            "date": h.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for h in history_records
    ]

    # 2. Fetch Activity Logs
    activity_records = ActivityLog.query.filter_by(organization_id=org.id).order_by(ActivityLog.created_at.desc()).limit(50).all()
    activity_data = [
        {
            "id": a.id,
            "action": a.action,
            "description": a.description,
            "user": a.user.name if a.user else "System",
            "date": a.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for a in activity_records
    ]

    return json_response(True, "Fetched organization history", {
        "subscription_history": history_data,
        "activity_logs": activity_data
    })

@admin_bp.route('/organizations/me', methods=['GET'])
@auth_token_required
@roles_accepted('admin')
def get_my_org():
    """
    Consolidated metadata for the Admin Dashboard summary.
    Returns the organization, its plan, and current usage.
    """
    org = current_user.organization
    if not org: return json_response(False, "Org not found", None, 404)
    
    # Reload from DB to ensure freshest counters
    db.session.refresh(org)
    
    schema = OrganizationSchema()
    return json_response(True, "Fetched organization summary", schema.dump(org))

@admin_bp.route('/members', methods=['GET'])
@auth_token_required
@roles_accepted('admin')
def get_members():
    """List members of current organization with optional role filtering."""
    role = request.args.get('role')
    org = current_user.organization
    if not org: return json_response(False, "Org not found", None, 404)
    
    query = User.query.filter_by(organization_id=org.id)
    if role:
        query = query.join(User.roles).filter_by(name=role)
    
    users = query.all()
    return json_response(True, "Fetched members", [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "roles": [r.name for r in u.roles],
            "active": u.active
        } for u in users
    ])

@admin_bp.route('/projects', methods=['GET'])
@auth_token_required
@roles_accepted('admin')
def get_projects():
    """List all projects in the organization."""
    org = current_user.organization
    if not org: return json_response(False, "Org not found", None, 404)
    
    projects = Project.query.filter_by(organization_id=org.id).all()
    return json_response(True, "Fetched projects", [
        {
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "professor": p.user.name if hasattr(p, 'user') else 'N/A', # Backref check
            "created_at": p.created_at.strftime('%Y-%m-%d')
        } for p in projects
    ])

@admin_bp.route('/users/<user_id>/toggle', methods=['POST'])
@auth_token_required
@roles_accepted('admin')
def toggle_user_status(user_id):
    """Activate/Deactivate a user."""
    user = User.query.get(user_id)
    if not user or user.organization_id != current_user.organization_id:
        return json_response(False, "User not found or access denied", None, 404)
    
    user.active = not user.active
    db.session.commit()
    return json_response(True, f"User {'activated' if user.active else 'suspended'} successfully")

@admin_bp.route('/projects/<project_id>/toggle', methods=['POST'])
@auth_token_required
@roles_accepted('admin')
def toggle_project_status(project_id):
    """Suspend/Resume a project."""
    project = Project.query.get(project_id)
    if not project or project.organization_id != current_user.organization_id:
        return json_response(False, "Project not found or access denied", None, 404)
    
    project.status = 'suspended' if project.status == 'active' else 'active'
    db.session.commit()
    return json_response(True, f"Project {project.status} successfully")
