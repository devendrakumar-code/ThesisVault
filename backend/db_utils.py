import os
import pymysql
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def create_db_if_not_exists():
    """
    Parses DATABASE_URL to extract connection details and creates the database if it doesn't exist.
    In production, database creation is typically managed by a DBA or CI/CD script.
    """
    if os.environ.get('FLASK_ENV') == 'production':
        logger.info("Skipping database creation check in production environment.")
        return

    db_url = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://root:12345678@localhost/thesis_vault_db'
    )

    try:
        parsed = urlparse(db_url)
        # Handle the scheme part "mysql+pymysql://" correctly
        host = parsed.hostname or "localhost"
        port = parsed.port or 3306
        user = parsed.username or "root"
        password = parsed.password or ""
        db_name = parsed.path.lstrip("/") or "thesis_vault_db"

        connection = pymysql.connect(
            host=host, 
            port=port, 
            user=user, 
            password=password,
            connect_timeout=5
        )
        
        try:
            with connection.cursor() as cursor:
                # Use backticks to safely quote the database name
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
            connection.commit()
            logger.info(f"Database readiness verified for: {db_name}")
        finally:
            connection.close()
    except Exception:
        # We don't want to crash at the very start if the DB server is just warming up
        # or if we're using a different DB engine (like SQLite) where this logic doesn't apply.
        logger.warning("Database pre-check encountered an issue. Proceeding with application startup...")
