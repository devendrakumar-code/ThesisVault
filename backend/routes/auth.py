from flask import Blueprint, request, jsonify, current_app
from extentions import db
from models import User, Role, Organization, Plan, RevokedToken
from schemas import user_schema, organization_schema
from flask_security.utils import hash_password, verify_password
from flask_security import auth_token_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import logging

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
logger = logging.getLogger(__name__)

def _normalize_email(email: str) -> str:
    return email.strip().lower()

# --- 1. ADMIN / ORGANIZATION REGISTRATION ---
@auth_bp.route('/register-org', methods=['POST'])
def register_organization():
    data = request.get_json(force=True, silent=True) or {}
    org_data = data.get('organization') or {}
    owner_data = data.get('owner') or {}
    plan_name = data.get('plan_name', 'Free')

    # Validate payload shape using Marshmallow
    org_errors = organization_schema.validate(org_data)
    user_errors = user_schema.validate(owner_data)
    if org_errors or user_errors:
        return jsonify({"errors": {**org_errors, **user_errors}}), 400

    # Basic required fields
    if not org_data.get('name') or not owner_data.get('email') or not owner_data.get('password'):
        return jsonify({"error": "Missing required organization or owner fields"}), 400

    email = _normalize_email(owner_data['email'])

    try:
        plan = Plan.query.filter(func.lower(Plan.name) == plan_name.lower()).first()
        admin_role = Role.query.filter(func.lower(Role.name) == 'admin').first()
        if not plan or not admin_role:
            logger.error("Missing seed data: plan=%s admin_role=%s", bool(plan), bool(admin_role))
            return jsonify({"error": "System roles/plans not initialized."}), 500

        # Prevent duplicate domain/email early (case-insensitive)
        if Organization.query.filter(func.lower(Organization.domain) == (org_data.get('domain') or '').lower()).first():
            return jsonify({"error": "Organization domain already exists"}), 409
        if User.query.filter(func.lower(User.email) == email).first():
            return jsonify({"error": "Email already exists"}), 409

        new_org = Organization(
            name=org_data['name'].strip(),
            domain=(org_data.get('domain') or '').strip() or None,
            plan_id=plan.id
        )
        db.session.add(new_org)
        db.session.flush()

        new_user = User(
            name=owner_data.get('name', '').strip() or None,
            email=email,
            password=hash_password(owner_data['password']),
            organization_id=new_org.id,
            active=True
        )
        new_user.roles.append(admin_role)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "message": "Organization and Admin registered successfully",
            "organization_id": new_org.id,
            "admin_id": new_user.id
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        logger.exception("IntegrityError during register_organization")
        return jsonify({"error": "Email or Domain already exists"}), 409
    except Exception:
        db.session.rollback()
        logger.exception("Unexpected error during register_organization")
        return jsonify({"error": "Internal server error"}), 500

# --- 2. LOGIN (JWT GENERATION) ---
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = _normalize_email(data.get('email', ''))
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter(func.lower(User.email) == email).first()

    # Timing-safe check and active check
    if not user or not verify_password(password, user.password):
        logger.warning("Failed login attempt for email=%s", email)
        return jsonify({"error": "Invalid email or password"}), 401

    if not user.active:
        return jsonify({"error": "Account inactive"}), 403

    # Optionally check organization active/plan limits here

    token = user.get_auth_token()
    # Ensure token is a string
    if isinstance(token, (bytes, bytearray)):
        token = token.decode('utf-8')

    return jsonify({
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "roles": [r.name for r in user.roles],
            "organization_id": user.organization_id
        }
    }), 200

# --- 3. LOGOUT ---
@auth_bp.route('/logout', methods=['POST'])
@auth_token_required
def logout():
    # If you implement token revocation, store token identifier here
    token = getattr(current_user, 'auth_token', None)
    try:
        # Example: RevokedToken model with token string and expiry
        if token:
            revoked = RevokedToken(token=token)
            db.session.add(revoked)
            db.session.commit()
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception:
        db.session.rollback()
        logger.exception("Error revoking token")
        return jsonify({"message": "Logged out (server error revoking token)"}), 200

