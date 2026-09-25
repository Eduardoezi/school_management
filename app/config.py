# app/config.py
"""
Configuración del sistema escolar.

Reglas:
    - Todos los valores sensibles vienen del .env.
    - Los defaults existen SOLO para desarrollo.
    - En producción (FLASK_ENV=production), las variables críticas
      son OBLIGATORIAS y la app falla al arrancar si faltan.
    - La validación de coherencia (por ejemplo, WEBAUTHN_ORIGIN debe
      ser HTTPS en producción) también corre al arrancar.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# Rutas base
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / '.env'

load_dotenv(ENV_FILE)


# ============================================================
# Helpers de parseo
# ============================================================
def _as_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _as_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _required(name: str, value) -> str:
    """
    Devuelve el valor o lanza RuntimeError con mensaje claro.
    Se usa para variables que NO pueden faltar en producción.
    """
    if value is None or str(value).strip() == '':
        raise RuntimeError(
            f"Falta la variable de entorno obligatoria: {name}. "
            f"Configúrala en {ENV_FILE}"
        )
    return str(value).strip()


class Config:

    # ============================================================
    # ENTORNO
    # ============================================================
    ENV = os.getenv('FLASK_ENV', 'production').strip().lower()
    IS_PRODUCTION = (ENV == 'production')
    DEBUG = _as_bool(os.getenv('FLASK_DEBUG'), default=False)

    # ============================================================
    # SEGURIDAD
    # ============================================================
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        if IS_PRODUCTION:
            raise RuntimeError(
                "SECRET_KEY no está definida. Configúrala en el .env. "
                "Genera una con: "
                'python -c "import secrets; print(secrets.token_hex(32))"'
            )
        SECRET_KEY = 'dev-secret-key-only-for-local'

    # Clave Fernet para cifrar cuentas bancarias.
    # Obligatoria en producción (si no, no puedes descifrar nada).
    BANK_ENCRYPTION_KEY = os.getenv('BANK_ENCRYPTION_KEY')
    if IS_PRODUCTION and not BANK_ENCRYPTION_KEY:
        raise RuntimeError(
            "BANK_ENCRYPTION_KEY no está definida. Configúrala en el .env. "
            "Genera una con: "
            'python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )

    # ============================================================
    # SERVIDOR
    # ============================================================
    HOST = os.getenv('HOST', '127.0.0.1')
    PORT = _as_int(os.getenv('PORT'), 8000)

    # Si hay reverse proxy adelante (Apache/Nginx)
    BEHIND_PROXY = _as_bool(os.getenv('BEHIND_PROXY'), default=False)

    # ============================================================
    # SSL (solo desarrollo con HTTPS local, o Apache como referencia)
    # En producción con Apache+Waitress, estas variables NO las usa
    # Flask; solo las lee Apache desde su vhost.
    # ============================================================
    SSL_CERT = os.getenv('SSL_CERT') or None
    SSL_KEY = os.getenv('SSL_KEY') or None

    # ============================================================
    # BASE DE DATOS MySQL
    # ============================================================
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = _as_int(os.getenv('MYSQL_PORT'), 3306)
    MYSQL_USER = os.getenv('MYSQL_USER')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
    MYSQL_DB = os.getenv('MYSQL_DB', 'school_db')

    if IS_PRODUCTION:
        _required('MYSQL_USER', MYSQL_USER)
        _required('MYSQL_PASSWORD', MYSQL_PASSWORD)
        if MYSQL_USER == 'root' and ENV == 'production':
            print(
                '⚠️  ADVERTENCIA: MYSQL_USER=root en producción. '
                'Crea un usuario dedicado para la app.'
            )

    # ============================================================
    # COOKIES / SESIÓN
    # ============================================================
    # HttpOnly: JS no puede leer la cookie (mitiga XSS).
    SESSION_COOKIE_HTTPONLY = True

    # SameSite=Lax: la cookie no se envía en peticiones cross-site
    # (mitiga CSRF). 'Strict' rompe algunos flujos de login externo.
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Secure: la cookie solo viaja por HTTPS.
    #   - Producción: true (por defecto)
    #   - Desarrollo: false (por defecto, porque usas HTTP)
    #   - Override: SESSION_COOKIE_SECURE=true|false en .env
    SESSION_COOKIE_SECURE = _as_bool(
        os.getenv('SESSION_COOKIE_SECURE'),
        default=IS_PRODUCTION,
    )

    # Tiempo de vida de la cookie de sesión. En Educación Especial
    # suele ser suficiente con 8 horas (una jornada laboral).
    # Si necesitas "recordarme", se maneja con remember_cookie aparte.
    SESSION_COOKIE_NAME = 'school_session'

    # Path y Domain: dejar por defecto es más seguro y evita fugas
    # a subdominios no relacionados.
    SESSION_COOKIE_PATH = '/'
    # SESSION_COOKIE_DOMAIN = None   # sin subdominios por ahora

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_DURATION = 30 * 24 * 3600   # 30 días en segundos

    # ============================================================
    # SUBIDA DE ARCHIVOS
    # ============================================================
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB
    UPLOAD_FOLDER = str(BASE_DIR / 'app' / 'static' / 'uploads')
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

    CALENDAR_UPLOAD_FOLDER = str(
        BASE_DIR / 'app' / 'static' / 'uploads' / 'calendars'
    )

    # ============================================================
    # WEB AUTHN
    # ============================================================
    WEBAUTHN_RP_ID = os.getenv('WEBAUTHN_RP_ID')
    WEBAUTHN_RP_NAME = os.getenv(
        'WEBAUTHN_RP_NAME',
        'Sistema Escolar'
    )
    WEBAUTHN_ORIGIN = os.getenv('WEBAUTHN_ORIGIN')

    if IS_PRODUCTION:
        _required('WEBAUTHN_RP_ID', WEBAUTHN_RP_ID)
        _required('WEBAUTHN_ORIGIN', WEBAUTHN_ORIGIN)

    # ============================================================
    # VALIDACIÓN DE COHERENCIA
    # Estas validaciones evitan configuraciones contradictorias.
    # ============================================================
    if IS_PRODUCTION:
        # 1) WebAuthn exige HTTPS en producción
        if WEBAUTHN_ORIGIN and not WEBAUTHN_ORIGIN.startswith('https://'):
            raise RuntimeError(
                f"WEBAUTHN_ORIGIN debe empezar con 'https://' en producción. "
                f"Valor actual: {WEBAUTHN_ORIGIN!r}"
            )

        # 2) El RP ID no puede ser una IP ni localhost en producción
        if WEBAUTHN_RP_ID and (
            WEBAUTHN_RP_ID in ('localhost', '127.0.0.1')
            or WEBAUTHN_RP_ID.replace('.', '').isdigit()
        ):
            raise RuntimeError(
                f"WEBAUTHN_RP_ID debe ser un dominio válido, no una IP ni "
                f"'localhost', en producción. Valor actual: {WEBAUTHN_RP_ID!r}"
            )

        # 3) Si las cookies son Secure, debe haber HTTPS
        if SESSION_COOKIE_SECURE and not WEBAUTHN_ORIGIN.startswith('https://'):
            raise RuntimeError(
                "SESSION_COOKIE_SECURE=true requiere HTTPS. "
                "Revisa WEBAUTHN_ORIGIN."
            )

        # 4) ProxyFix coherente con el modo de despliegue
        if BEHIND_PROXY and HOST not in ('127.0.0.1', 'localhost'):
            print(
                f'⚠️  ADVERTENCIA: BEHIND_PROXY=true pero HOST={HOST}. '
                f'Si hay proxy, Waitress debería escuchar solo en '
                f'127.0.0.1 para no exponerse directamente.'
            )

    # ============================================================
    # RESOLUCIÓN DE RUTAS RELATIVAS
    # Si SSL_CERT/SSL_KEY son relativos, convertirlos a absolutos
    # respecto a BASE_DIR.
    # ============================================================
    if SSL_CERT and not os.path.isabs(SSL_CERT):
        SSL_CERT = str(BASE_DIR / SSL_CERT)
    if SSL_KEY and not os.path.isabs(SSL_KEY):
        SSL_KEY = str(BASE_DIR / SSL_KEY)

    # ============================================================
    # LOG DE ARRANQUE (sin exponer secretos)
    # ============================================================
    if DEBUG:
        print('─' * 60)
        print(f'  Config cargada — ENV={ENV}')
        print(f'  HOST={HOST}  PORT={PORT}  DEBUG={DEBUG}')
        print(f'  BEHIND_PROXY={BEHIND_PROXY}')
        print(f'  WEBAUTHN_RP_ID={WEBAUTHN_RP_ID}')
        print(f'  WEBAUTHN_ORIGIN={WEBAUTHN_ORIGIN}')
        print(f'  SESSION_COOKIE_SECURE={SESSION_COOKIE_SECURE}')
        print(f'  SSL_CERT definido: {bool(SSL_CERT)}')
        print(f'  SSL_KEY  definido: {bool(SSL_KEY)}')
        print(f'  SECRET_KEY definida: {bool(SECRET_KEY)}')
        print('─' * 60)