# tests/test_inf03.py
"""
Tests automáticos para el hallazgo INF-03:
"Configuración HTTPS frágil y específica de una máquina".

A) No debe haber rutas absolutas, dominios ni puertos hardcodeados
   en el código fuente.
B) La app debe fallar al arrancar si faltan variables obligatorias.
C) config.py debe leer efectivamente de las variables de entorno.
D) webauthn_auth.py no debe derivar el RP ID del Host del request
   en producción.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


RAIZ = Path(__file__).resolve().parent.parent

# Carpetas que NO se escanean (tests propios, venvs, caches, etc.)
IGNORAR_DIRS = {
    '.venv', 'venv', 'env', '__pycache__', '.git',
    'tests', 'test', 'node_modules', 'logs', 'backups',
    '.pytest_cache', '.mypy_cache', 'htmlcov',
}

EXTENSIONES = {'.py'}


def _iter_archivos_codigo():
    """Recorre el repo y devuelve solo archivos .py de aplicación."""
    for path in RAIZ.rglob('*'):
        if path.is_dir():
            continue
        if any(part in IGNORAR_DIRS for part in path.parts):
            continue
        if path.suffix not in EXTENSIONES:
            continue
        # Cinturón extra: no escanear archivos de test ni conftest
        if path.name.startswith('test_') or path.name == 'conftest.py':
            continue
        yield path


# ===================================================================
# TEST A — Sin valores hardcodeados
# ===================================================================
PATRONES_PROHIBIDOS = [
    (r"C:\\\\certs",
     "Ruta absoluta de Windows a certificados (C:\\certs\\...)"),

    (r"gestionescolar\.duckdns\.org",
     "Dominio de producción hardcodeado (gestionescolar.duckdns.org)"),

    (r"gestionescolar\.local",
     "Host mDNS hardcodeado (gestionescolar.local)"),

    (r"\bport\s*=\s*5000\b",
     "Puerto 5000 hardcodeado"),

    (r"['\"]0\.0\.0\.0['\"]\s*,?\s*5000",
     "Bind fijo 0.0.0.0:5000"),
]


@pytest.mark.parametrize("patron,descripcion", PATRONES_PROHIBIDOS,
                         ids=[d for _, d in PATRONES_PROHIBIDOS])
def test_no_hardcoded_en_codigo(patron, descripcion):
    rx = re.compile(patron)
    hallazgos = []

    for archivo in _iter_archivos_codigo():
        try:
            contenido = archivo.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue

        for nro_linea, linea in enumerate(contenido.splitlines(), start=1):
            stripped = linea.lstrip()
            if stripped.startswith('#'):
                continue
            if rx.search(linea):
                hallazgos.append(
                    f"  {archivo.relative_to(RAIZ)}:{nro_linea}  ->  {linea.strip()}"
                )

    assert not hallazgos, (
        f"\n[FAIL] INF-03: {descripcion}\n"
        f"   Encontrado en:\n" + "\n".join(hallazgos)
    )


# ===================================================================
# TEST B — Fail-fast en producción
# ===================================================================
def test_app_falla_sin_webauthn_rp_id():
    """
    Forzamos WEBAUTHN_RP_ID y WEBAUTHN_ORIGIN a string vacío (no ausentes)
    porque config.py hace load_dotenv(.env), y si estuvieran ausentes las
    recargaría del archivo real. Un valor vacío SÍ satisface a _required().
    """
    env = os.environ.copy()
    env['FLASK_ENV'] = 'production'
    env['SECRET_KEY'] = 'x' * 64
    env['BANK_ENCRYPTION_KEY'] = 'x' * 44
    env['MYSQL_USER'] = 'user'
    env['MYSQL_PASSWORD'] = 'pass'

    # Vaciado, no ausencia → load_dotenv no las reintroduce
    env['WEBAUTHN_RP_ID'] = ''
    env['WEBAUTHN_ORIGIN'] = ''

    codigo = (
        "import sys; sys.path.insert(0, '.');"
        "import app.config"
    )
    r = subprocess.run(
        [sys.executable, '-c', codigo],
        cwd=str(RAIZ), env=env,
        capture_output=True, text=True, timeout=30,
    )

    assert r.returncode != 0, (
        "[FAIL] INF-03: la app NO falla al arrancar con WEBAUTHN_RP_ID "
        "vacío en producción.\nSTDOUT:\n" + r.stdout +
        "\nSTDERR:\n" + r.stderr
    )
    assert 'WEBAUTHN' in r.stderr.upper(), (
        f"[FAIL] El error no menciona WEBAUTHN_RP_ID.\nSTDERR:\n{r.stderr}"
    )


# ===================================================================
# TEST C — config.py lee de os.getenv
# ===================================================================
def test_config_usa_getenv(monkeypatch):
    dominio_test = 'midominio-de-prueba.example.org'
    origin_test = f'https://{dominio_test}'

    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', 'x' * 64)
    monkeypatch.setenv('BANK_ENCRYPTION_KEY', 'x' * 44)
    monkeypatch.setenv('MYSQL_USER', 'user')
    monkeypatch.setenv('MYSQL_PASSWORD', 'pass')
    monkeypatch.setenv('WEBAUTHN_RP_ID', dominio_test)
    monkeypatch.setenv('WEBAUTHN_ORIGIN', origin_test)

    import importlib
    import app.config as cfg
    importlib.reload(cfg)

    assert cfg.Config.WEBAUTHN_RP_ID == dominio_test, (
        "[FAIL] WEBAUTHN_RP_ID no se está leyendo del entorno"
    )
    assert cfg.Config.WEBAUTHN_ORIGIN == origin_test, (
        "[FAIL] WEBAUTHN_ORIGIN no se está leyendo del entorno"
    )


# ===================================================================
# TEST D — webauthn_auth.py no deriva RP ID del request en prod
# ===================================================================
def test_webauthn_no_deriva_rp_id_del_request():
    archivo = RAIZ / 'app' / 'routes' / 'webauthn_auth.py'
    assert archivo.exists(), f"No existe {archivo}"

    texto = archivo.read_text(encoding='utf-8')

    assert "current_app.config.get('WEBAUTHN_RP_ID')" in texto, (
        "[FAIL] webauthn_auth._rp_id() no consulta WEBAUTHN_RP_ID "
        "desde la configuración."
    )
    assert "current_app.config.get('WEBAUTHN_ORIGIN')" in texto, (
        "[FAIL] webauthn_auth._origin() no consulta WEBAUTHN_ORIGIN "
        "desde la configuración."
    )
    assert "def _check_host" in texto, (
        "[FAIL] Falta el guard _check_host() que rechaza Host no autorizado."
    )