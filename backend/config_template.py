import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class BaseConfig:
    SQL_ALCHEMY_TRACK_MODIFICATIONS = False

class LocalDevelopmentConfig(BaseConfig):
    # --- Database ---
    # mysql+pymysql://<user>:<password>@<host>/<db_name>
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://YOUR_USER:YOUR_PASSWORD@localhost/thesis_vault_db'
    DEBUG = True
    SECRET_KEY = "YOUR_FLASK_SECRET_KEY" 

    # --- Redis / Celery ---
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    USE_CELERY = True
    CELERY_TIMEZONE = 'Asia/Kolkata' 
    
    CELERY_TASK_ROUTES = {
        'tasks.analyze_thesis': {'queue': 'ai'},
        'tasks.send_onboarding_email_async': {'queue': 'default'}
    }
    
    # --- Flask-Security-Too ---
    SECURITY_PASSWORD_SALT = "YOUR_SALT_STRING" 
    SECURITY_PASSWORD_HASH = "argon2" 
    
    # JWT Settings
    SECURITY_TOKEN_AUTHENTICATION_HEADER = 'Authorization'
    SECURITY_TOKEN_MAX_AGE = 3600 
    
    # SPA / API Optimization
    SECURITY_REDIRECT_BEHAVIOR = "spa"
    SECURITY_HTTP_AUTHENTICATION = True
    SECURITY_FLASH_MESSAGES = False
    
    SECURITY_REGISTERABLE = True 
    SECURITY_SEND_REGISTER_EMAIL = False 
    
    # --- File Management ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # --- SMTP / Mailtrap Settings ---
    MAIL_SERVER = 'YOUR_SMTP_SERVER'
    MAIL_PORT = 2525
    MAIL_USERNAME = 'YOUR_MAIL_USERNAME'
    MAIL_PASSWORD = 'YOUR_MAIL_PASSWORD'
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_DEFAULT_SENDER = 'noreply@thesisvault.com'

    # --- AI Integration ---
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

class ProductionConfig(BaseConfig):
    DEBUG = False
