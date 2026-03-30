import os
from pathlib import Path

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = Path(BASE_DIR).parent


def _load_env_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return

    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].strip()

        key, separator, value = line.partition('=')
        if not separator or not key.strip():
            continue

        cleaned = value.strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
            cleaned = cleaned[1:-1]

        os.environ.setdefault(key.strip(), cleaned)


for candidate in (PROJECT_ROOT / '.env', Path(BASE_DIR) / '.env'):
    _load_env_file(candidate)


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False


class LocalDevelopmentConfig(BaseConfig):
    # --- Database ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://root:12345678@localhost/thesis_vault_db'
    )

    # --- Core Security ---
    DEBUG = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-change-me-in-production')
    SECURITY_PASSWORD_SALT = os.environ.get('PASSWORD_SALT', 'dev-only-salt-change-me')

    # --- Frontend / CORS ---
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173')
    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173'
    ).split(',')

    # --- Celery / Redis ---
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
    USE_CELERY = True
    CELERY_TIMEZONE = os.environ.get('CELERY_TIMEZONE', 'Asia/Kolkata')
    CELERY_TASK_ROUTES = {
        'tasks.analyze_thesis': {'queue': 'ai'},
        'tasks.send_onboarding_email_async': {'queue': 'default'}
    }

    # --- Flask-Security-Too Core ---
    SECURITY_PASSWORD_HASH = 'argon2'
    SECURITY_TOKEN_AUTHENTICATION_HEADER = 'Authorization'
    SECURITY_TOKEN_AUTHENTICATION_QUERY_PARAMETER = 'token'
    SECURITY_TOKEN_MAX_AGE = int(os.environ.get('TOKEN_MAX_AGE', '3600'))
    SECURITY_REDIRECT_BEHAVIOR = 'spa'
    SECURITY_HTTP_AUTHENTICATION = True
    SECURITY_FLASH_MESSAGES = False
    SECURITY_REGISTERABLE = True
    SECURITY_SEND_REGISTER_EMAIL = False

    # --- File Uploads ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # --- External Services ---
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'sandbox.smtp.mailtrap.io')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '2525'))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@thesisvault.com')

    # --- Other ---
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
    MAX_ENROLLMENTS_PER_PROJECT = int(os.environ.get('MAX_ENROLLMENTS_PER_PROJECT', '500'))


class ProductionConfig(BaseConfig):
    DEBUG = False

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        val = os.environ.get('DATABASE_URL')
        if not val:
            raise RuntimeError('DATABASE_URL must be set in production')
        return val

    @property
    def SECRET_KEY(self):
        val = os.environ.get('SECRET_KEY')
        if not val or val.startswith('dev-only'):
            raise RuntimeError('A secure SECRET_KEY must be set in production')
        return val

    @property
    def SECURITY_PASSWORD_SALT(self):
        val = os.environ.get('PASSWORD_SALT')
        if not val or val.startswith('dev-only'):
            raise RuntimeError('A secure PASSWORD_SALT must be set in production')
        return val

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_URL = os.environ.get('FRONTEND_URL')
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')

    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND')
    USE_CELERY = True

    SECURITY_PASSWORD_HASH = 'argon2'
    SECURITY_TOKEN_MAX_AGE = int(os.environ.get('TOKEN_MAX_AGE', '3600'))

    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')

    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_USE_TLS = True
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'redis://127.0.0.1:6379/1')
    MAX_ENROLLMENTS_PER_PROJECT = int(os.environ.get('MAX_ENROLLMENTS_PER_PROJECT', '500'))


