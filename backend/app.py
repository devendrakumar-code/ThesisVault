from flask import Flask
from config import LocalDevelopmentConfig
from db_utils import create_db_if_not_exists
from extentions import db, ma, migrate, mail
from flask_security import Security, SQLAlchemyUserDatastore
from celery_app import make_celery

def create_app():
    create_db_if_not_exists()

    app = Flask(__name__)
    
    app.config.from_object(LocalDevelopmentConfig)

    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    from models import User, Role
    
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security = Security(app, user_datastore)

    # --- Register Blueprints ---
    from routes.auth import auth_bp
    from routes.members import members_bp
    from routes.profile import profiles_bp
    from routes.projects import projects_bp
    from routes.submission import submissions_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(profiles_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(submissions_bp)
    # ---------------------------

    with app.app_context():
        import models 
        
        db.create_all()
        print("All Modular Tables and Security Schemas Created.")

        import tasks.email_tasks
        import tasks.ai_tasks
    return app

app = create_app()
celery = make_celery(app)

if (__name__ == "__main__"):
    app.run(debug=True)
