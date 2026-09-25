import mysql.connector
from app.config import Config

def get_db_connection():
    """Devuelve una conexión a MySQL usando la configuración."""
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            connection_timeout=10,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error de conexión: {err}")
        return None