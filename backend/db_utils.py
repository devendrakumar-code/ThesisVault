import pymysql
from config import LocalDevelopmentConfig

def create_db_if_not_exists():
    # format: mysql+pymysql://user:password@host:port/db_name
    host = "localhost"
    user = "root"
    password = "12345678" 
    db_name = "thesis_vault_db"

    # 2. Connect to MySQL server (WITHOUT specifying a DB name yet)
    connection = pymysql.connect(host=host, user=user, password=password)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        connection.commit()
        print(f"✅ Database '{db_name}' is ready.")
    finally:
        connection.close()
