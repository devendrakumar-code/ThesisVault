from flask import Flask
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

        Talisman(
            app,
            force_https=not app.debug,
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

    app.register_blueprint(auth_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(profiles_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(submissions_bp)
    app.register_blueprint(milestones_bp)

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
