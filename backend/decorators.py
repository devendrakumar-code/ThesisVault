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

def limit_check(org_attr="active_projects", plan_limit_attr="max_active_projects", message=None, code=403):
    """
    Generic decorator to enforce numeric limits.
    Compares org.{org_attr} against plan.{plan_limit_attr}.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            org, plan = _get_org_and_plan()
            if not org:
                current_app.logger.warning("Limit check failed: user %s has no organization", getattr(current_user, "id", None))
                return json_error("Organization not found", 403)
            if not plan:
                return json_error("Plan configuration missing", 403)

            try:
                current_val = int(getattr(org, org_attr, 0) or 0)
                limit_val = int(getattr(plan, plan_limit_attr, 0) or 0)
            except (TypeError, ValueError):
                current_app.logger.exception("Invalid limit comparison for %s/%s", org_attr, plan_limit_attr)
                return json_error("Server misconfiguration", 500)

            if limit_val <= 0:
                return json_error(message or f"Action restricted on {getattr(plan, 'name', 'your plan')}. Please upgrade.", code)

            if current_val >= limit_val:
                friendly_name = org_attr.replace('_', ' ').title()
                return json_error(message or f"{friendly_name} limit reached for {getattr(plan, 'name', 'your plan')} ({limit_val}). Please upgrade.", code)

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

            # 1. Check Legacy Column-based flag (if exists)
            has_feature = bool(getattr(plan, feature_name, False))
            
            # 2. Check Modern JSON-based features map (Requirement 2 & 3)
            # This allows adding 'advanced_pdf', 'video_interview', etc. via DB only.
            plan_features = getattr(plan, "features", None) or {}
            if feature_name in plan_features:
                has_feature = bool(plan_features[feature_name])

            if not has_feature:
                current_app.logger.info(
                    "Feature '%s' denied for user %s plan %s",
                    feature_name, getattr(current_user, "id", None), getattr(plan, "name", None)
                )
                return json_error(message or f"The '{feature_name}' feature is not included in your {getattr(plan, 'name', 'current')} plan. Please upgrade.", code)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

