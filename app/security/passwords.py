# app/security/passwords.py
"""
Validación centralizada de contraseñas.

Reglas (balanceadas para educación):
    - Mínimo 12 caracteres (OWASP ASVS 2.1.1).
    - Máximo 128 caracteres (permitir passphrases).
    - Al menos 1 mayúscula, 1 minúscula, 1 número.
    - Caracteres especiales opcionales.
    - Se rechazan contraseñas conocidas como filtradas (HIBP).
    - Se rechazan contraseñas de listas locales comunes.

Uso:
    from app.security.passwords import validate_password
    ok, errores = validate_password("MiClave123")
    if not ok:
        for e in errores:
            flash(e, 'danger')
"""
import hashlib
import logging
import re
import urllib.request

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN (ajustable)
# ============================================================
MIN_LENGTH = 12
MAX_LENGTH = 128
REQUIRE_UPPER = True
REQUIRE_LOWER = True
REQUIRE_DIGIT = True
REQUIRE_SPECIAL = False   # especiales opcionales

# Tiempo máximo de espera al consultar HIBP (segundos).
# Si la API tarda más, se considera "no filtrada" para no bloquear
# el registro por un problema de red externo.
HIBP_TIMEOUT = 2.0

# Lista mínima local de contraseñas comunes (defensa en profundidad
# por si HIBP no responde). En producción se puede cargar un archivo
# más grande, pero estas 30 cubren lo que la gente realmente usa.
COMMON_PASSWORDS = {
    'password', 'password1', 'password123', '12345678', '123456789',
    '1234567890', 'qwerty', 'qwerty123', 'abc123', 'admin', 'admin123',
    'letmein', 'welcome', 'welcome1', 'monkey', 'dragon', 'master',
    'iloveyou', 'sunshine', 'princess', 'football', 'baseball',
    'escuela', 'colegio', 'docente', 'maestro', 'venezuela',
    'colegio123', 'escuela123', 'sistema123', 'escuela2025',
}


# ============================================================
# API PÚBLICA
# ============================================================
def validate_password(password: str) -> tuple[bool, list[str]]:
    """
    Valida una contraseña contra todas las reglas.

    Returns:
        (True, []) si es válida.
        (False, [mensajes de error]) si no lo es.

    Nunca modifica la contraseña; solo la evalúa.
    """
    if not isinstance(password, str):
        return False, ['La contraseña debe ser texto.']

    errores: list[str] = []

    # Longitud
    if len(password) < MIN_LENGTH:
        errores.append(
            f'La contraseña debe tener al menos {MIN_LENGTH} caracteres.'
        )
    if len(password) > MAX_LENGTH:
        errores.append(
            f'La contraseña no puede tener más de {MAX_LENGTH} caracteres.'
        )

    # Composición
    if REQUIRE_UPPER and not re.search(r'[A-ZÁÉÍÓÚÑ]', password):
        errores.append('Debe incluir al menos una letra mayúscula.')

    if REQUIRE_LOWER and not re.search(r'[a-záéíóúñ]', password):
        errores.append('Debe incluir al menos una letra minúscula.')

    if REQUIRE_DIGIT and not re.search(r'\d', password):
        errores.append('Debe incluir al menos un número.')

    if REQUIRE_SPECIAL and not re.search(r'[^A-Za-z0-9]', password):
        errores.append('Debe incluir al menos un carácter especial.')

    # Espacios: NIST los permite. No los bloqueamos.

    # Lista local de comunes
    if password.lower() in COMMON_PASSWORDS:
        errores.append(
            'Esta contraseña es demasiado común. Elegí otra.'
        )

    # Si ya hay errores de forma, no golpeamos HIBP (ahorro de red)
    if errores:
        return False, errores

    # Verificación contra HIBP
    if is_password_pwned(password):
        errores.append(
            'Esta contraseña apareció en filtraciones de datos conocidas. '
            'Elegí una diferente.'
        )

    return (len(errores) == 0), errores


def is_password_pwned(password: str, timeout: float = HIBP_TIMEOUT) -> bool:
    """
    Consulta la API de HIBP con k-Anonymity.

    Solo se envían los primeros 5 caracteres del SHA-1. El password
    completo NUNCA sale del servidor.

    Si la API falla o tarda, se devuelve False para no bloquear
    al usuario por un problema externo. El log queda con la advertencia.

    Ref: https://haveibeenpwned.com/API/v3#PwnedPasswords
    """
    try:
        sha1 = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]
        url = f'https://api.pwnedpasswords.com/range/{prefix}'

        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'SchoolManagement-PasswordCheck'},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode('utf-8')

        for line in data.splitlines():
            h, _, _count = line.partition(':')
            if h.strip() == suffix:
                return True

    except Exception as exc:
        # No rompemos el flujo por un fallo de red externo.
        logger.warning('[HIBP] No se pudo verificar contraseña: %s', exc)

    return False