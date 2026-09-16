import os
from dotenv import load_dotenv

# Carga el .env desde la raíz (un directorio arriba de 'app')
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')  # fallback si no está en .env
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB = os.getenv('MYSQL_DB', 'school_db')

    # ---------- Subida de archivos ----------
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024   # 2 MB máximo por archivo
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(__file__), 'static', 'uploads'
    )
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}