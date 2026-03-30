from datetime import datetime, timedelta, timezone
from flask import Flask, send_from_directory
from sqlalchemy import inspect, text

from config import LocalDevelopmentConfig, ProductionConfig
from db_utils import create_db_if_not_exists
from extentions import db, limiter, ma, mail, migrate
from flask_security import Security, SQLAlchemyUserDatastore
from celery_app import make_celery
from flask_cors import CORS
import os


def _ensure_runtime_schema(app):
    inspector = inspect(db.engine)
    if inspector.has_table('projects'):
        project_columns = {column['name'] for column in inspector.get_columns('projects')}
        if 'problem_statement_file_url' not in project_columns:
            with db.engine.begin() as connection:
                connection.execute(text('ALTER TABLE projects ADD COLUMN problem_statement_file_url VARCHAR(512) NULL'))
            app.logger.info('Added projects.problem_statement_file_url column at startup.')

    if inspector.has_table('submissions'):
        submission_columns = {column['name'] for column in inspector.get_columns('submissions')}
        with db.engine.begin() as connection:
            if 'rejection_extension_days' not in submission_columns:
                connection.execute(text('ALTER TABLE submissions ADD COLUMN rejection_extension_days INT NULL'))
                app.logger.info('Added submissions.rejection_extension_days column at startup.')
            if 'resubmission_deadline' not in submission_columns:
                connection.execute(text('ALTER TABLE submissions ADD COLUMN resubmission_deadline DATETIME NULL'))
                app.logger.info('Added submissions.resubmission_deadline column at startup.')

    if inspector.has_table('users'):
        user_columns = {column['name'] for column in inspector.get_columns('users')}
        if 'profile_image' not in user_columns:
            with db.engine.begin() as connection:
                connection.execute(text('ALTER TABLE users ADD COLUMN profile_image VARCHAR(255) NULL'))
            app.logger.info('Added users.profile_image column at startup.')

    if inspector.has_table('organizations'):
        org_columns = {column['name'] for column in inspector.get_columns('organizations')}
        with db.engine.begin() as connection:
            if 'active_students' not in org_columns:
                connection.execute(text('ALTER TABLE organizations ADD COLUMN active_students INT DEFAULT 0 NOT NULL'))
            if 'subscription_status' not in org_columns:
                connection.execute(text('ALTER TABLE organizations ADD COLUMN subscription_status VARCHAR(20) DEFAULT "active"'))
            if 'subscription_ends_at' not in org_columns:
                connection.execute(text('ALTER TABLE organizations ADD COLUMN subscription_ends_at DATETIME NULL'))
            if 'trial_ends_at' not in org_columns:
                connection.execute(text('ALTER TABLE organizations ADD COLUMN trial_ends_at DATETIME NULL'))
            if 'grace_period_ends_at' not in org_columns:
                connection.execute(text('ALTER TABLE organizations ADD COLUMN grace_period_ends_at DATETIME NULL'))
            if 'monthly_ai_count' not in org_columns:
                connection.execute(text('ALTER TABLE organizations ADD COLUMN monthly_ai_count INT DEFAULT 0 NOT NULL'))
            if 'last_usage_reset' not in org_columns:
                connection.execute(text('ALTER TABLE organizations ADD COLUMN last_usage_reset DATETIME DEFAULT CURRENT_TIMESTAMP'))
            if 'is_maintenance' not in org_columns:
                connection.execute(text('ALTER TABLE organizations ADD COLUMN is_maintenance BOOLEAN DEFAULT 0 NOT NULL'))
        app.logger.info('Checked/Added missing organizations columns at startup.')

    if inspector.has_table('plans'):
        plan_columns = {column['name'] for column in inspector.get_columns('plans')}
        with db.engine.begin() as connection:
            if 'max_students' not in plan_columns:
                connection.execute(text('ALTER TABLE plans ADD COLUMN max_students INT DEFAULT 100 NOT NULL'))
            if 'monthly_ai_limit' not in plan_columns:
                connection.execute(text('ALTER TABLE plans ADD COLUMN monthly_ai_limit INT DEFAULT 50 NOT NULL'))
            if 'validity_days' not in plan_columns:
                connection.execute(text('ALTER TABLE plans ADD COLUMN validity_days INT DEFAULT 30 NOT NULL'))
            if 'features' not in plan_columns:
                connection.execute(text('ALTER TABLE plans ADD COLUMN features JSON NULL'))
            app.logger.info('Added missing plans columns at startup.')

    # Requirement 4: Data-Driven Consistency
    # Sync project_id for submissions if missing or mismatched with milestone
    try:
        from models import Submission, Milestone, Organization, Plan
        with app.app_context():
            # 1. Submission Sync
            db.session.execute(text("""
                UPDATE submissions 
                INNER JOIN milestones ON submissions.milestone_id = milestones.id
                SET submissions.project_id = milestones.project_id
                WHERE submissions.project_id IS NULL OR submissions.project_id != milestones.project_id
            """))
            
            # 2. Plan Metadata Enrichment (Ensures UI meters don't fail)
            db.session.execute(text("""
                UPDATE plans 
                SET features = '{"ai_analysis": true, "premium_support": false}'
                WHERE features IS NULL OR features = ''
            """))

            # 3. Organization Plan Safety (Ensures 'Pro' as default for orphans)
            pro_plan = Plan.query.filter_by(name='Pro').first()
            if pro_plan:
                db.session.execute(text(f"UPDATE organizations SET plan_id = '{pro_plan.id}' WHERE plan_id IS NULL OR plan_id = ''"))
            
            # 4. Standardize Lifecycle Status & Dates (Ensures Display Meters work)
            now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            ends_at_str = (datetime.now(timezone.utc) + timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')
            
            db.session.execute(text(f"UPDATE organizations SET subscription_status = 'active' WHERE subscription_status IS NULL OR subscription_status = ''"))
            db.session.execute(text(f"UPDATE organizations SET subscription_ends_at = '{ends_at_str}' WHERE subscription_ends_at IS NULL"))
            
            db.session.commit()
            app.logger.info('Runtime data sync & refinement complete.')
    except Exception as e:
        db.session.rollback()
        app.logger.warning('Skipped runtime data sync: %s', str(e))


def create_app():
    create_db_if_not_exists()

    app = Flask(__name__)

    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(LocalDevelopmentConfig)

    cors_origins = app.config.get('CORS_ORIGINS', ['http://localhost:5173'])
    CORS(app, resources={r'/api/*': {'origins': cors_origins}}, supports_credentials=True)

    try:
        from flask_talisman import Talisman

        if app.debug:
            app.logger.info('Flask-Talisman skipped in debug mode to allow local cross-origin development.')
        else:
            Talisman(
                app,
                force_https=True,
                content_security_policy={
                    'default-src': "'self'",
                    'style-src': ["'self'", "'unsafe-inline'"],
                    'img-src': ["'self'", 'data:', 'https:'],
                    'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
                    'frame-ancestors': ["'self'", 'http://localhost:5173', 'http://127.0.0.1:5173'],
                },
                frame_options=None,
            )
            app.logger.info('Flask-Talisman security headers enabled.')
    except ImportError:
        app.logger.warning('flask-talisman not installed. Security headers (CSP/HSTS) are NOT active.')

    limiter.init_app(app)

    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    from models import Role, User

    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    Security(app, user_datastore)

    from routes.auth import auth_bp
    from routes.members import members_bp
    from routes.profile import profiles_bp
    from routes.projects import projects_bp
    from routes.submission import submissions_bp
    from routes.milestones import milestones_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(profiles_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(submissions_bp)
    app.register_blueprint(milestones_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        import models

        db.create_all()
        _ensure_runtime_schema(app)
        app.logger.info('All Modular Tables and Security Schemas Created.')

        from flask_security.utils import hash_password
        test_hash = hash_password('__startup_check__')
        if not test_hash.startswith('$argon2'):
            app.logger.critical('FATAL: Argon2 password hashing is NOT active! Install argon2-cffi.')
            raise RuntimeError('Argon2 hashing not active. Install: pip install argon2-cffi')

        if not app.debug and app.config.get('SECRET_KEY', '').startswith('dev-only'):
            app.logger.critical('FATAL: Production mode with dev SECRET_KEY! Set SECRET_KEY env var.')
            raise RuntimeError('Production requires a strong SECRET_KEY')

        import tasks.ai_tasks
        import tasks.email_tasks

    from flask import jsonify, request
    from flask_security import current_user
    from models import RevokedToken

    @app.before_request
    def check_auth_integrity():
        if not request.path.startswith('/api/') or 'auth' in request.path:
            return

        token = request.headers.get('Authorization')
        if not token:
            token = request.args.get('token')

        if token:
            if token.startswith('Bearer '):
                token = token[7:]

            if RevokedToken.query.filter_by(token=token).first():
                app.logger.warning('Revoked token access attempt by user_id=%s', getattr(current_user, 'id', 'anonymous'))
                return jsonify({'success': False, 'message': 'Token has been revoked. Please log in again.'}), 401

        if current_user.is_authenticated and current_user.organization_id:
            org = current_user.organization
            if org and org.is_maintenance:
                return jsonify({
                    'success': False,
                    'error': 'Organization Maintenance',
                    'message': 'Your organization is currently undergoing maintenance. Please try again later.',
                }), 503

    @app.route('/uploads/<path:filename>')
    def serve_uploads(filename):
        return send_from_directory(os.path.join(app.root_path, 'uploads'), filename)

    @app.errorhandler(500)
    @app.errorhandler(Exception)
    def handle_exception(e):
        if not app.debug:
            app.logger.exception('Final exception caught by global handler: %s', str(e))
            return jsonify({'success': False, 'message': 'Internal Server Error'}), 500
        raise e

    return app


app = create_app()
celery = make_celery(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
