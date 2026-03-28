from functools import wraps
from flask import jsonify, current_app, g
from flask_security import current_user

def json_error(message, code=403):
    return jsonify({"success": False, "message": message}), code

def _get_org_and_plan():
    """
    Helper to fetch and cache organization and plan on flask.g for the current request.
    Returns (org, plan) where either may be None.
    """
    if hasattr(g, "_org_plan_cached"):
        return g._org_plan_cached

    org = getattr(current_user, "organization", None)
    plan = getattr(org, "plan", None) if org is not None else None
    g._org_plan_cached = (org, plan)
    return g._org_plan_cached

def subscription_required(message=None, code=403):
    """
    Decorator to ensure the organization's subscription is active.
    Optional message and HTTP code can be provided.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            org, _ = _get_org_and_plan()
            if not org:
                current_app.logger.warning("Subscription check failed: user %s has no organization", getattr(current_user, "id", None))
                return json_error("Organization not found", 403)
            # Prefer explicit boolean attribute check; treat missing attribute as invalid
            is_valid = getattr(org, "is_subscription_valid", False)
            if not is_valid:
                msg = message or "Your organization's subscription has expired or is inactive."
                current_app.logger.info("Subscription denied for user %s org %s", getattr(current_user, "id", None), getattr(org, "id", None))
                return json_error(msg, code)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def limit_check(message=None, code=403):
    """
    Enforces the 'max_projects' limit from the Plan table.
    Denies access when active_projects >= plan.max_projects.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            org, plan = _get_org_and_plan()
            if not org:
                current_app.logger.warning("Limit check failed: user %s has no organization", getattr(current_user, "id", None))
                return json_error("Organization not found", 403)
            if not plan:
                current_app.logger.warning("Limit check failed: org %s has no plan", getattr(org, "id", None))
                return json_error("Plan configuration missing", 403)

            # Defensive attribute access and coercion
            try:
                active_projects = int(getattr(org, "active_projects", 0) or 0)
                max_projects = int(getattr(plan, "max_active_projects", 0) or 0)
            except (TypeError, ValueError):
                current_app.logger.exception("Invalid project counts for org %s", getattr(org, "id", None))
                return json_error("Server misconfiguration", 500)

            if max_projects <= 0:
                # Treat non-positive max as "no projects allowed" (fail closed)
                current_app.logger.info("Plan %s has non-positive max_projects", getattr(plan, "name", None))
                return json_error(message or f"Project limit reached for {getattr(plan, 'name', 'your plan')}. Please upgrade.", code)

            if active_projects >= max_projects:
                current_app.logger.info(
                    "Project limit reached for user %s org %s: %s/%s",
                    getattr(current_user, "id", None), getattr(org, "id", None), active_projects, max_projects
                )
                return json_error(message or f"Project limit reached for {getattr(plan, 'name', 'your plan')} ({max_projects}). Please upgrade.", code)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requires_feature(feature_name, message=None, code=403):
    """
    Gates specific features like 'has_ai_analysis'.
    If the plan does not have the attribute or it's falsy, access is denied.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            _, plan = _get_org_and_plan()
            if not plan:
                current_app.logger.warning("Feature check failed: user %s org plan missing", getattr(current_user, "id", None))
                return json_error("Plan configuration missing", 403)

            # Use getattr with default False; treat missing attribute as disabled
            has_feature = bool(getattr(plan, feature_name, False))
            if not has_feature:
                current_app.logger.info(
                    "Feature '%s' denied for user %s plan %s",
                    feature_name, getattr(current_user, "id", None), getattr(plan, "name", None)
                )
                return json_error(message or f"The '{feature_name}' feature is not included in your current plan.", code)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

