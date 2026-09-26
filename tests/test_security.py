# tests/test_security.py
"""
Tests automáticos para la categoría SEC (seguridad y autenticación).

Todos son estáticos (regex/AST) para correr rápido sin DB ni HTTP.
Los que están en rojo HOY son tickets concretos del backlog.

Estado esperado al crear el archivo (25-09-2026):
    ✅ SEC-05, SEC-06, SEC-07
    ❌ SEC-01, SEC-02, SEC-03, SEC-04, SEC-08, SEC-09
"""
import ast
import re
from pathlib import Path

import pytest


RAIZ = Path(__file__).resolve().parent.parent
APP = RAIZ / 'app'

IGNORAR_DIRS = {'__pycache__', '.venv', 'venv', 'tests', 'test'}


def _py_files(base: Path = APP):
    """Itera archivos .py del proyecto, sin tests ni venvs."""
    for p in base.rglob('*.py'):
        if any(part in IGNORAR_DIRS for part in p.parts):
            continue
        yield p


def _leer(p: Path) -> str:
    return p.read_text(encoding='utf-8', errors='ignore')


# ===================================================================
# SEC-01 — Registro público sin rate limiting
# ===================================================================
def test_sec01_rate_limit_en_register():
    """
    El endpoint /register debe tener protección contra spam:
    flask-limiter, CAPTCHA, invitación, activación por directivo, etc.

    El simple chequeo 'existe la cédula en teachers' NO es suficiente:
    permite enumerar cédulas y automatizar intentos.
    """
    auth = APP / 'routes' / 'auth.py'
    if not auth.exists():
        pytest.skip("auth.py no existe")

    texto = _leer(auth)

    # Cualquier señal de rate limiting / captcha / invitación
    señales = [
        'limiter.limit',
        '@ratelimit',
        'flask_limiter',
        'Flask-Limiter',
        'recaptcha',
        'hcaptcha',
        'turnstile',
        'invitation_token',
        'invite_token',
    ]
    tiene = any(s.lower() in texto.lower() for s in señales)

    assert tiene, (
        "[SEC-01] /auth/register no tiene rate limiting ni CAPTCHA "
        "ni invitación. Agregar flask-limiter (pip install Flask-Limiter) "
        "y decorar la ruta con @limiter.limit('5 per minute')."
    )


# ===================================================================
# SEC-02 — Política de contraseñas
# ===================================================================
def test_sec02_longitud_minima_password():
    """
    La longitud mínima debe ser >= 10 caracteres en CUALQUIER chequeo
    de contraseña (registro, cambio, reset).

    Buscamos patrones `len(x) < N` con N < 10.
    """
    rx = re.compile(r'len\s*\(\s*\w+\s*\)\s*<\s*(\d+)')
    hallazgos = []

    for archivo in _py_files():
        texto = _leer(archivo)
        lineas = texto.splitlines()
        for m in rx.finditer(texto):
            n = int(m.group(1))
            if n < 10:
                # número de línea
                ln = texto[:m.start()].count('\n') + 1
                contexto = lineas[ln - 1].strip() if ln - 1 < len(lineas) else ''
                # Solo nos interesan chequeos sobre contraseñas
                if 'pass' in contexto.lower():
                    hallazgos.append(
                        f"  {archivo.relative_to(RAIZ)}:{ln}  "
                        f"(mínimo actual: {n}, mínimo requerido: 10)\n"
                        f"    {contexto}"
                    )

    assert not hallazgos, (
        "[SEC-02] Longitud de contraseña por debajo del mínimo:\n"
        + "\n".join(hallazgos) +
        "\n\nSubir a 10-12 caracteres. Ver también OWASP ASVS 2.1.1."
    )


def test_sec02_validador_password_centralizado():
    """
    Debe existir UNA función reutilizable de validación de contraseña,
    no chequeos inline dispersos por varias rutas.
    """
    candidatos = [
        'def validate_password',
        'def check_password_strength',
        'def validate_new_password',
        'def _validate_password',
    ]
    for archivo in _py_files():
        texto = _leer(archivo)
        if any(c in texto for c in candidatos):
            return

    pytest.fail(
        "[SEC-02] No existe una función centralizada de validación "
        "de contraseñas. Los chequeos `len(password) < 6` están inline "
        "en auth.py y hay que centralizarlos en "
        "app/security/passwords.py con reglas reutilizables."
    )


# ===================================================================
# SEC-03 — Logout por GET
# ===================================================================
def test_sec03_logout_es_post():
    """El endpoint /logout debe aceptar SOLO POST (evita CSRF por <img>)."""
    auth = APP / 'routes' / 'auth.py'
    if not auth.exists():
        pytest.skip("auth.py no existe")

    texto = _leer(auth)
    m = re.search(
        r"@\w+\.route\(\s*['\"]/logout['\"](?P<args>[^)]*)\)",
        texto,
    )
    assert m, "[SEC-03] No se encontró la ruta /logout en auth.py"

    args = m.group('args')
    if "methods" not in args or "POST" not in args.upper():
        pytest.fail(
            "[SEC-03] /logout no declara methods=['POST']. "
            "Actualmente acepta GET, lo cual permite CSRF trivial: "
            "<img src='/auth/logout'> en cualquier página externa cierra "
            "la sesión del usuario.\n"
            f"  Encontrado: @auth_bp.route('/logout'{args})"
        )


# ===================================================================
# SEC-04 — Uploads fuera de static/
# ===================================================================
def test_sec04_upload_folder_fuera_de_static():
    """
    Los archivos subidos NO deben vivir bajo app/static/, porque
    Flask los sirve públicamente sin autenticación.

    OJO: UPLOAD_FOLDER está indentado dentro de la clase Config,
    por eso el regex permite espacios al inicio.
    """
    config = APP / 'config.py'
    if not config.exists():
        pytest.skip("config.py no existe")

    texto = _leer(config)
    # Permitir indentación antes del nombre
    m = re.search(r'^\s*UPLOAD_FOLDER\s*=\s*(.+)$', texto, re.MULTILINE)
    assert m, "[SEC-04] No se encontró UPLOAD_FOLDER en config.py"

    expr = m.group(1).strip()
    assert 'static' not in expr, (
        f"[SEC-04] UPLOAD_FOLDER apunta a static/:\n"
        f"    {expr}\n"
        "Mover a `private_uploads/` (fuera de static/) y servir los "
        "archivos por un endpoint autenticado con send_file()."
    )


def test_sec04_calendar_upload_folder_fuera_de_static():
    """
    Lo mismo para CALENDAR_UPLOAD_FOLDER.

    El regex captura solo el bloque de la asignación (paréntesis
    balanceados aproximados con [^)]+) para no tragarse el resto
    del archivo.
    """
    config = APP / 'config.py'
    if not config.exists():
        pytest.skip("config.py no existe")

    texto = _leer(config)
    # Captura solo hasta el cierre del `str(...)` — sin lookahead
    m = re.search(
        r'^\s*CALENDAR_UPLOAD_FOLDER\s*=\s*str\((?P<expr>[^)]+)\)',
        texto, re.MULTILINE | re.DOTALL,
    )
    if not m:
        # Puede estar definido sin str(); lo buscamos más suelto
        m = re.search(
            r'^\s*CALENDAR_UPLOAD_FOLDER\s*=\s*(?P<expr>.+)$',
            texto, re.MULTILINE,
        )
    assert m, "[SEC-04] No se encontró CALENDAR_UPLOAD_FOLDER"

    expr = m.group('expr').strip()
    assert 'static' not in expr, (
        f"[SEC-04] CALENDAR_UPLOAD_FOLDER apunta a static/:\n  {expr}"
    )


# ===================================================================
# SEC-05 — Autorización centralizada
# ===================================================================
def test_sec05_una_sola_definicion_de_role_required():
    """
    No debe haber varios módulos definiendo su propia versión de
    `role_required`. Una sola fuente de verdad.
    """
    definiciones = []
    for archivo in _py_files():
        texto = _leer(archivo)
        if re.search(r'def\s+role_required\s*\(', texto):
            definiciones.append(str(archivo.relative_to(RAIZ)))

    assert len(definiciones) <= 1, (
        f"[SEC-05] `role_required` está definido en {len(definiciones)} "
        f"archivos:\n  " + "\n  ".join(definiciones) +
        "\nDebe haber UNA sola fuente de verdad."
    )


def test_sec05_una_sola_definicion_de_require():
    """Igual para `require` (permisos RBAC+ABAC)."""
    definiciones = []
    for archivo in _py_files():
        texto = _leer(archivo)
        if re.search(r'def\s+require\s*\(', texto):
            definiciones.append(str(archivo.relative_to(RAIZ)))

    assert len(definiciones) <= 1, (
        f"[SEC-05] `require` definido en {len(definiciones)} archivos:\n  "
        + "\n  ".join(definiciones)
    )


# ===================================================================
# SEC-06 — Cifrado de datos bancarios
# ===================================================================
def test_sec06_staff_detail_cifra_cuenta():
    """StaffDetail.save debe cifrar el número de cuenta antes de guardar."""
    sd = APP / 'models' / 'staff_detail.py'
    if not sd.exists():
        pytest.skip("staff_detail.py no existe")

    texto = _leer(sd)
    assert 'encrypt_str' in texto, (
        "[SEC-06] StaffDetail no usa encrypt_str() para el número de cuenta."
    )
    assert 'bank_account_number_encrypted' in texto, (
        "[SEC-06] StaffDetail no persiste en bank_account_number_encrypted."
    )
    assert 'bank_account_last6' in texto, (
        "[SEC-06] Falta bank_account_last6 (últimos 6 dígitos visibles)."
    )


def test_sec06_crypto_usa_fernet():
    """crypto.py debe usar Fernet (AES-128-CBC + HMAC-SHA256)."""
    crypto = APP / 'utils' / 'crypto.py'
    if not crypto.exists():
        pytest.skip("crypto.py no existe")

    texto = _leer(crypto)
    assert 'Fernet' in texto, "[SEC-06] crypto.py no usa Fernet."
    assert 'BANK_ENCRYPTION_KEY' in texto, (
        "[SEC-06] crypto.py no lee BANK_ENCRYPTION_KEY del entorno."
    )


def test_sec06_no_loggea_numero_de_cuenta():
    """
    El número de cuenta NUNCA debe aparecer en logs, prints ni
    mensajes de error.
    """
    patrones = [
        r'logger\.\w+\([^)]*account_number',
        r'print\s*\([^)]*account_number',
    ]
    for archivo in _py_files():
        texto = _leer(archivo)
        for pat in patrones:
            if re.search(pat, texto, re.IGNORECASE):
                pytest.fail(
                    f"[SEC-06] {archivo.relative_to(RAIZ)} loguea "
                    "el número de cuenta. Nunca debe aparecer en logs."
                )


# ===================================================================
# SEC-07 — WebAuthn usa config (ver INF-03)
# ===================================================================
def test_sec07_webauthn_usa_config():
    """Smoke: WebAuthn debe leer RP_ID desde config, no del request."""
    wa = APP / 'routes' / 'webauthn_auth.py'
    if not wa.exists():
        pytest.skip("webauthn_auth.py no existe")

    texto = _leer(wa)
    assert "current_app.config.get('WEBAUTHN_RP_ID')" in texto, (
        "[SEC-07] webauthn_auth no lee WEBAUTHN_RP_ID desde config. "
        "Ver test_inf03 para el detalle completo."
    )
    assert "current_app.config.get('WEBAUTHN_ORIGIN')" in texto, (
        "[SEC-07] webauthn_auth no lee WEBAUTHN_ORIGIN desde config."
    )


# ===================================================================
# SEC-08 — get_online_users duplica por sesiones
# ===================================================================
def test_sec08_online_users_no_duplica():
    """
    get_online_users() debe usar DISTINCT o GROUP BY.
    Un usuario con N sesiones activas aparece N veces sin eso.
    """
    user = APP / 'models' / 'user.py'
    if not user.exists():
        pytest.skip("user.py no existe")

    texto = _leer(user)
    m = re.search(
        r'def\s+get_online_users.*?(?=\n\s+@staticmethod|\n\s+def\s|\Z)',
        texto, re.DOTALL,
    )
    assert m, "[SEC-08] No se encontró get_online_users en user.py"

    cuerpo = m.group(0).upper()
    tiene_distinct = 'DISTINCT' in cuerpo
    tiene_group = 'GROUP BY' in cuerpo

    assert tiene_distinct or tiene_group, (
        "[SEC-08] get_online_users() no usa DISTINCT ni GROUP BY. "
        "El LEFT JOIN a user_sessions produce una fila por sesión activa.\n"
        "Opción simple:\n"
        "    SELECT DISTINCT u.id, u.username, ...\n"
        "Opción completa (con conteo):\n"
        "    SELECT u.*, COUNT(s.id) AS active_sessions\n"
        "    ... GROUP BY u.id"
    )


# ===================================================================
# SEC-09 — Datos sensibles de menores sin cifrar
# ===================================================================
def test_sec09_datos_medicos_cifrados():
    """
    Los campos médicos de menores (vacunas, alergias, condiciones
    crónicas, informes psicológicos y neurológicos) son datos sensibles
    según la LOPNNA. Deben cifrarse en reposo igual que el número
    de cuenta bancaria de los adultos.

    Estado actual: texto plano. Test en rojo hasta que se implemente.
    """
    archivo = APP / 'models' / 'medical_info.py'
    if not archivo.exists():
        pytest.skip("medical_info.py no existe")

    texto = _leer(archivo)
    usa_cifrado = any(s in texto for s in [
        'encrypt_str', 'decrypt_str', 'Fernet', '_encrypted'
    ])

    assert usa_cifrado, (
        "[SEC-09] medical_info.py guarda datos médicos en texto plano. "
        "Cifrar con Fernet (mismo enfoque que SEC-06) los campos:\n"
        "  - allergies\n"
        "  - chronic_conditions\n"
        "  - convulsions\n"
        "  - current_medication\n"
        "  - medical_attention / upen_attention\n"
        "  - report_medical / report_psychological / report_neurological"
    )


def test_sec09_datos_socioeconomicos_cifrados():
    """
    El estudio socioeconómico (ingresos familiares, condiciones de
    vivienda) es información sensible del núcleo familiar.
    """
    archivo = APP / 'models' / 'socioeconomic_info.py'
    if not archivo.exists():
        pytest.skip("socioeconomic_info.py no existe")

    texto = _leer(archivo)
    usa_cifrado = any(s in texto for s in [
        'encrypt_str', 'decrypt_str', 'Fernet', '_encrypted'
    ])

    assert usa_cifrado, (
        "[SEC-09] socioeconomic_info.py guarda datos socioeconómicos en "
        "texto plano. Cifrar al menos:\n"
        "  - monthly_income\n"
        "  - housing_type / housing_condition / housing_infrastructure\n"
        "  - other_family_members"
    )


def test_sec09_documento_clasificacion_datos():
    """
    Debe existir un documento que clasifique los datos personales:
    qué campos son sensibles, cómo se protegen, quién puede verlos.

    Es un requisito de la LOPNNA y de buenas prácticas (GDPR art. 30,
    OWASP ASVS 1.8).
    """
    posibles = [
        RAIZ / 'docs' / 'DATA_CLASSIFICATION.md',
        RAIZ / 'docs' / 'DATOS_PERSONALES.md',
        RAIZ / 'docs' / 'PRIVACY.md',
        RAIZ / 'SECURITY.md',
        RAIZ / 'PRIVACY.md',
    ]
    if any(d.exists() for d in posibles):
        return

    pytest.fail(
        "[SEC-09] No existe documento de clasificación de datos. "
        "Crear `docs/DATA_CLASSIFICATION.md` con:\n"
        "  - Tabla de campos sensibles (médicos, socioeconómicos, "
        "    bancarios, cédulas, direcciones)\n"
        "  - Nivel de protección de cada uno (público / interno / "
        "    confidencial / restringido)\n"
        "  - Roles autorizados a verlos\n"
        "  - Método de cifrado en reposo (si aplica)\n"
        "  - Retención y borrado"
    )


# ===================================================================
# SEC-10 (bonus) — Reset password NO revela si el usuario existe
# ===================================================================
def test_sec10_login_no_revela_usuarios():
    """
    Los mensajes de login deben ser genéricos:
    'Usuario o contraseña incorrectos' (no 'usuario no existe').
    Enumerar usuarios es el primer paso para ataques dirigidos.
    """
    auth = APP / 'routes' / 'auth.py'
    if not auth.exists():
        pytest.skip("auth.py no existe")

    texto = _leer(auth)
    # Frases que revelan si el usuario existe
    malos = [
        'usuario no existe',
        'usuario no encontrado',
        'la contraseña es incorrecta',
        'contraseña incorrecta para',
    ]
    hallazgos = [m for m in malos if m in texto.lower()]

    assert not hallazgos, (
        f"[SEC-10] Mensajes que revelan existencia de usuarios: {hallazgos}\n"
        "Usar siempre: 'Usuario o contraseña incorrectos.'"
    )