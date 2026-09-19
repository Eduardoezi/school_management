# app/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# ---------- Rutas base ----------
BASE_DIR = Path(__file__).resolve().parent.parent   # raíz del proyecto
ENV_FILE = BASE_DIR / '.env'

load_dotenv(ENV_FILE)


# ---------- Helpers ----------
def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


class Config:
    # ---------- Entorno ----------
    ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = _as_bool(os.getenv('FLASK_DEBUG'), default=False)

    # ---------- Seguridad ----------
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        if ENV == 'production':
            raise RuntimeError(
                "SECRET_KEY no está definida. Configúrala en el .env "
                "antes de arrancar en producción."
            )
        SECRET_KEY = 'dev-secret-key-only-for-local'

    # ---------- Servidor ----------
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = _as_int(os.getenv('PORT'), 5000)

    # ---------- SSL (Let's Encrypt via win-acme) ----------
    SSL_CERT = os.getenv('SSL_CERT') or r'C:\certs\gestionescolar.duckdns.org\gestionescolar.duckdns.org-chain.pem'
    SSL_KEY  = os.getenv('SSL_KEY')  or r'C:\certs\gestionescolar.duckdns.org\gestionescolar.duckdns.org-key.pem'

    # ---------- Base de datos MySQL ----------
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = _as_int(os.getenv('MYSQL_PORT'), 3306)
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB = os.getenv('MYSQL_DB', 'school_db')

    # ---------- Cookies / sesión ----------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = _as_bool(
        os.getenv('SESSION_COOKIE_SECURE'), default=True
    )   # True porque ya sirves por HTTPS

    # ---------- Subida de archivos ----------
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024   # 2 MB
    UPLOAD_FOLDER = str(BASE_DIR / 'app' / 'static' / 'uploads')
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

    # ---------- WebAuthn ----------
    WEBAUTHN_RP_ID = os.getenv('WEBAUTHN_RP_ID', 'gestionescolar.duckdns.org')
    WEBAUTHN_RP_NAME = os.getenv('WEBAUTHN_RP_NAME', 'Sistema Escolar IEE Villa de Cura')
    WEBAUTHN_ORIGIN = os.getenv('WEBAUTHN_ORIGIN', 'https://gestionescolar.duckdns.org:5000')