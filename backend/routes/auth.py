from datetime import datetime, timedelta, timezone
import logging

from flask import Blueprint, request, jsonify, current_app
from flask_security import auth_token_required, current_user
from flask_security import roles_required, roles_accepted
from flask_security.utils import hash_password, verify_password
from sqlalchemy import func, case
from sqlalchemy.exc import IntegrityError

from extentions import db
from extentions import limiter
from models import User, Role, Organization, Plan, RevokedToken, SubscriptionHistory, ActivityLog
from schemas import user_schema, organization_schema

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
logger = logging.getLogger(__name__)
SUBSCRIPTION_DURATION_DAYS = 365


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _plan_rank(plan_name: str) -> int:
    order = {
        'free': 0,
        'pro': 1,
        'enterprise': 2,
    }
    return order.get((plan_name or '').lower(), 99)


def _to_utc(value):
    if not value:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _default_subscription_end_at(start_at=None):
    base_time = _to_utc(start_at) if start_at else datetime.now(timezone.utc)
    return base_time + timedelta(days=SUBSCRIPTION_DURATION_DAYS)


def _plan_payload(plan):
    if not plan:
        return {
            'id': None,
            'name': None,
            'display_name': None,
            'max_active_projects': 0,
            'has_ai_feature': False,
            'feature_list': [],
            'rank': 99,
        }

    feature_list = [f'Up to {plan.max_active_projects} active projects']
    feature_list.append('AI review available' if plan.has_ai_feature else 'AI review not included')

    return {
        'id': plan.id,
        'name': plan.name,
        'display_name': plan.name,
        'max_active_projects': plan.max_active_projects,
        'has_ai_feature': plan.has_ai_feature,
        'feature_list': feature_list,
        'rank': _plan_rank(plan.name),
    }


def _subscription_snapshot(org):
    now = datetime.now(timezone.utc)
    current_plan = org.plan
    effective_end_at = _to_utc(org.trial_ends_at if org.subscription_status == 'trialing' and org.trial_ends_at else org.subscription_ends_at)
    if not effective_end_at and org.subscription_status == 'active':
        effective_end_at = _default_subscription_end_at(getattr(org, 'created_at', None))
    grace_end_at = _to_utc(org.grace_period_ends_at)
    days_left = None

    if effective_end_at:
        delta_seconds = (effective_end_at - now).total_seconds()
        if delta_seconds <= 0:
            days_left = 0
        else:
            full_days, remainder = divmod(int(delta_seconds), 86400)
            days_left = full_days + (1 if remainder > 0 else 0)

    return {
        'subscription_status': org.subscription_status,
        'current_plan': _plan_payload(current_plan),
        'active_projects': org.active_projects,
        'subscription_ends_at': effective_end_at.isoformat() if effective_end_at else None,
        'grace_period_ends_at': grace_end_at.isoformat() if grace_end_at else None,
        'days_left': days_left,
        'has_active_subscription': org.is_subscription_valid,
    }


@auth_bp.route('/plans', methods=['GET'])
def get_plans():
    try:
        plans = Plan.query.order_by(
            case(
                (func.lower(Plan.name) == 'free', 0),
                (func.lower(Plan.name) == 'pro', 1),
                (func.lower(Plan.name) == 'enterprise', 2),
                else_=99,
            ),
            Plan.name.asc(),
        ).all()

        return jsonify([_plan_payload(plan) for plan in plans]), 200
    except Exception:
        logger.exception('Failed to fetch plans')
        return jsonify({'error': 'Failed to fetch plans'}), 500


# --- 1. ADMIN / ORGANIZATION REGISTRATION ---
@auth_bp.route('/register-org', methods=['POST'])
@limiter.limit("3 per hour")
def register_organization():
    data = request.get_json(force=True, silent=True) or {}
    org_data = data.get('organization') or {}
    owner_data = data.get('owner') or {}
    plan_name = data.get('plan_name', 'Free')

    org_errors = organization_schema.validate(org_data, partial=('plan_id',))
    user_errors = user_schema.validate(owner_data, partial=('organization_id',))
    if org_errors or user_errors:
        return jsonify({"errors": {**org_errors, **user_errors}}), 400

    if not org_data.get('name') or not owner_data.get('email') or not owner_data.get('password'):
        return jsonify({"error": "Missing required organization or owner fields"}), 400

    email = _normalize_email(owner_data['email'])

    try:
        plan = Plan.query.filter(func.lower(Plan.name) == plan_name.lower()).first()
        admin_role = Role.query.filter(func.lower(Role.name) == 'admin').first()
        if not plan or not admin_role:
            logger.error("Missing seed data: plan=%s admin_role=%s", bool(plan), bool(admin_role))
            return jsonify({"error": "System roles/plans not initialized."}), 500

        if Organization.query.filter(func.lower(Organization.domain) == (org_data.get('domain') or '').lower()).first():
            return jsonify({"error": "Organization domain already exists"}), 409
        if User.query.filter(func.lower(User.email) == email).first():
            return jsonify({"error": "Email already exists"}), 409

        new_org = Organization(
            name=org_data['name'].strip(),
            domain=(org_data.get('domain') or '').strip() or None,
            plan_id=plan.id,
            subscription_status='active',
            subscription_ends_at=_default_subscription_end_at()
        )
        db.session.add(new_org)
        db.session.flush()

        new_user = User(
            name=owner_data.get('name', '').strip() or email.split('@')[0],
            email=email,
            password=hash_password(owner_data['password']),
            organization_id=new_org.id,
            active=True
        )
        new_user.roles.append(admin_role)
        db.session.add(new_user)

        history = SubscriptionHistory(
            organization_id=new_org.id,
            old_plan_id=None,
            new_plan_id=plan.id,
            change_reason='initial_signup'
        )
        db.session.add(history)

        log = ActivityLog(
            user_id=new_user.id,
            organization_id=new_org.id,
            action='ORG_REGISTERED',
            description=f"Organization {new_org.name} registered with plan {plan.name}"
        )
        db.session.add(log)

        db.session.commit()

        return jsonify({
            "message": "Organization and Admin registered successfully",
            "organization_id": new_org.id,
            "admin_id": new_user.id
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        logger.warning("IntegrityError during org registration: %s", str(e))
        return jsonify({"error": "A record with these details already exists"}), 409
    except Exception:
        db.session.rollback()
        logger.exception("Failed to register organization")
        return jsonify({"error": "Unable to complete registration"}), 500


# --- 2. LOGIN ---
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = _normalize_email(data.get('email', ''))
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = User.query.filter(func.lower(User.email) == email).first()
    if not user or not verify_password(password, user.password):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.active:
        return jsonify({"error": "Your account is inactive. Please contact your administrator."}), 403

    auth_token = user.get_auth_token()
    roles = [r.name for r in user.roles]

    return jsonify({
        "token": auth_token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "organization_id": user.organization_id,
            "organization_name": user.organization.name if user.organization else None,
            "roles": roles
        }
    }), 200


# --- 3. LOGOUT ---
@auth_bp.route('/logout', methods=['POST'])
@auth_token_required
def logout():
    token = request.headers.get('Authorization')
    if token:
        revoked = RevokedToken(token=token)
        db.session.add(revoked)
        db.session.commit()
    return jsonify({"message": "Logged out successfully"}), 200


@auth_bp.route('/subscription-summary', methods=['GET'])
@auth_token_required
@roles_required('admin')
def get_subscription_summary():
    org = current_user.organization
    if not org:
        return jsonify({"error": "Organization not found for current user"}), 404

    try:
        return jsonify(_subscription_snapshot(org)), 200
    except Exception:
        logger.exception("Failed to fetch subscription summary")
        return jsonify({"error": "Failed to fetch subscription summary"}), 500


# --- 4. SUBSCRIPTION MANAGEMENT (Plan Upgrades/Downgrades) ---
@auth_bp.route('/change-plan', methods=['POST'])
@auth_token_required
@roles_required('admin')
def change_plan():
    """
    SaaS Entitlement Requirement: Support plan upgrades/downgrades with history tracking.
    Reject downgrades if current usage exceeds target plan limits.
    """
    data = request.get_json(force=True, silent=True) or {}
    new_plan_name = data.get('plan_name')
    reason = data.get('reason', 'User-initiated plan change')

    if not new_plan_name:
        return jsonify({"error": "plan_name is required"}), 400

    org = current_user.organization
    if not org:
        return jsonify({"error": "Organization not found for current user"}), 404

    try:
        old_plan_name = getattr(org.plan, 'name', 'N/A')
        new_plan = Plan.query.filter(func.lower(Plan.name) == new_plan_name.lower()).first()
        if not new_plan:
            return jsonify({"error": "Target plan not found"}), 404

        if new_plan.id == org.plan_id:
            return jsonify({"message": "Already on this plan", "subscription": _subscription_snapshot(org)}), 200

        if new_plan.max_active_projects < org.active_projects:
            return jsonify({
                "error": f"Cannot downgrade. Your current usage ({org.active_projects} projects) exceeds the {new_plan.name} limit ({new_plan.max_active_projects})."
            }), 400

        old_plan_id = org.plan_id
        org.plan_id = new_plan.id
        org.subscription_status = 'active'
        org.subscription_ends_at = _default_subscription_end_at()
        org.trial_ends_at = None
        org.grace_period_ends_at = None

        history = SubscriptionHistory(
            organization_id=org.id,
            old_plan_id=old_plan_id,
            new_plan_id=new_plan.id,
            change_reason=reason
        )
        db.session.add(history)

        log = ActivityLog(
            user_id=current_user.id,
            organization_id=org.id,
            action='PLAN_CHANGED',
            description=f"Changed plan from {old_plan_name} to {new_plan.name}",
            metadata_json={"old_plan": old_plan_name, "new_plan": new_plan.name}
        )
        db.session.add(log)

        db.session.commit()
        db.session.refresh(org)

        return jsonify({
            "message": f"Organization transitioned to {new_plan.name} plan.",
            "new_plan": new_plan.name,
            "subscription": _subscription_snapshot(org)
        }), 200

    except Exception:
        db.session.rollback()
        logger.exception("Failed to change plan")
        return jsonify({"error": "Unable to change plan at this time"}), 500





