# tests/test_infra.py
"""
Tests automáticos para la categoría INF (infraestructura y despliegue),
excepto INF-03 que vive en test_inf03.py.

Convención de nombres:
    test_infNN_<descripcion_corta>

Los tests marcados con "CHECK BLANDO" solo verifican existencia o
presencia superficial. Los "CHECK FUERTE" inspeccionan contenido real.
"""
import re
from pathlib import Path

import pytest


RAIZ = Path(__file__).resolve().parent.parent
APP_DIR = RAIZ / 'app'

# Carpetas que nunca se escanean
IGNORAR_DIRS = {
    '.venv', 'venv', 'env', '__pycache__', '.git',
    'tests', 'test', 'node_modules', 'logs', 'backups',
    '.pytest_cache', '.mypy_cache',
}


def _py_files(base: Path = APP_DIR):
    """Itera archivos .py de la app, sin tests, sin venvs."""
    for p in base.rglob('*.py'):
        if any(part in IGNORAR_DIRS for part in p.parts):
            continue
        yield p


def _grep(patron: str, base: Path = APP_DIR, flags=0):
    """Devuelve [(archivo, nro_linea, linea)] de matches en .py."""
    rx = re.compile(patron, flags)
    for archivo in _py_files(base):
        try:
            lineas = archivo.read_text(encoding='utf-8', errors='ignore').splitlines()
        except OSError:
            continue
        for n, linea in enumerate(lineas, 1):
            if linea.lstrip().startswith('#'):
                continue
            if rx.search(linea):
                yield archivo.relative_to(RAIZ), n, linea.strip()


# ===================================================================
# INF-01 — MYSQL_PORT llega a mysql.connector.connect()
# ===================================================================
def test_inf01_mysql_port_se_usa_en_la_conexion():
    """CHECK FUERTE: db.py debe pasar port=Config.MYSQL_PORT."""
    db_file = RAIZ / 'app' / 'utils' / 'db.py'
    assert db_file.exists(), "[INF-01] no existe app/utils/db.py"

    texto = db_file.read_text(encoding='utf-8')
    assert re.search(r'port\s*=\s*Config\.MYSQL_PORT', texto) \
        or re.search(r'port\s*=\s*MYSQL_PORT', texto), (
        "[INF-01] db.py no pasa MYSQL_PORT a mysql.connector.connect()"
    )


def test_inf01_connection_timeout_y_charset():
    """CHECK FUERTE: conexión con timeouts y charset explícitos."""
    db_file = RAIZ / 'app' / 'utils' / 'db.py'
    if not db_file.exists():
        pytest.skip("db.py no existe (cubierto por test_inf01 anterior)")
    texto = db_file.read_text(encoding='utf-8')
    assert 'connection_timeout' in texto, \
        "[INF-01] falta connection_timeout en la conexión"
    assert 'utf8mb4' in texto, \
        "[INF-01] falta charset/collation utf8mb4 en la conexión"


# ===================================================================
# INF-02 — Producción no usa app.run()
# ===================================================================
def test_inf02_existe_wsgi_py():
    """CHECK BLANDO: existe wsgi.py como entry point WSGI."""
    assert (RAIZ / 'wsgi.py').exists(), "[INF-02] falta wsgi.py"


def test_inf02_existe_serve_py():
    """CHECK BLANDO: existe serve.py con Waitress."""
    serve = RAIZ / 'serve.py'
    assert serve.exists(), "[INF-02] falta serve.py"
    texto = serve.read_text(encoding='utf-8')
    assert 'waitress' in texto.lower(), \
        "[INF-02] serve.py no usa Waitress"


def test_inf02_run_py_advierte_que_es_dev():
    """CHECK FUERTE: run.py debe advertir que no es producción."""
    run = RAIZ / 'run.py'
    assert run.exists(), "[INF-02] no existe run.py"
    texto = run.read_text(encoding='utf-8').lower()
    assert 'no usar en producción' in texto or 'no usar en produccion' in texto, (
        "[INF-02] run.py no advierte que es solo para desarrollo"
    )


# ===================================================================
# INF-04 — SESSION_COOKIE_SECURE depende del entorno
# ===================================================================
def test_inf04_cookie_secure_no_esta_hardcodeada():
    """CHECK FUERTE: SESSION_COOKIE_SECURE no debe ser literal True."""
    config = RAIZ / 'app' / 'config.py'
    if not config.exists():
        pytest.skip("app/config.py no existe")
    texto = config.read_text(encoding='utf-8')
    assert not re.search(r'SESSION_COOKIE_SECURE\s*=\s*True\b', texto), (
        "[INF-04] SESSION_COOKIE_SECURE=True hardcodeado. "
        "Debe depender de IS_PRODUCTION."
    )
    assert 'IS_PRODUCTION' in texto, (
        "[INF-04] config.py no consulta IS_PRODUCTION para la cookie"
    )


# ===================================================================
# INF-05 — Migraciones / versionado de esquema
# ===================================================================
def test_inf05_existe_carpeta_migraciones():
    """CHECK FUERTE: hay carpeta de migraciones + runner + README."""
    mig = RAIZ / 'database' / 'migrations'
    assert mig.exists() and mig.is_dir(), \
        "[INF-05] falta database/migrations/"

    sqls = sorted(mig.glob('*.sql'))
    assert sqls, "[INF-05] database/migrations/ está vacía"

    # Debe haber al menos una 001_*
    assert any(s.name.startswith('001_') for s in sqls), \
        "[INF-05] falta una migración inicial 001_*.sql"

    # Debe existir el runner
    runner = RAIZ / 'database' / 'migrate.py'
    assert runner.exists(), "[INF-05] falta database/migrate.py"

    # Debe existir README
    readme = RAIZ / 'database' / 'README.md'
    assert readme.exists(), "[INF-05] falta database/README.md"


# ===================================================================
# INF-06 — Reproducibilidad de dependencias
# ===================================================================
def test_inf06_requirements_esta_pinneado():
    """CHECK FUERTE: requirements.txt usa ==, no >= ni ~=."""
    req = RAIZ / 'requirements.txt'
    assert req.exists(), "[INF-06] falta requirements.txt"
    lineas = [
        l.strip() for l in req.read_text(encoding='utf-8').splitlines()
        if l.strip() and not l.strip().startswith('#')
    ]
    sueltos = [l for l in lineas if re.search(r'[><~]=', l)]
    assert not sueltos, (
        "[INF-06] requirements.txt tiene versiones no pinneadas:\n  "
        + "\n  ".join(sueltos)
    )


def test_inf06_existe_requirements_dev():
    """CHECK BLANDO: separación dev/prod."""
    assert (RAIZ / 'requirements-dev.txt').exists() or \
           (RAIZ / 'requirements-dev.in').exists(), (
        "[INF-06] falta requirements-dev.txt (separación dev/prod)"
    )


# ===================================================================
# INF-07 — Infraestructura (CI, Docker, health, backups)
# ===================================================================
def test_inf07_health_endpoint_definido():
    """CHECK FUERTE: debe existir un blueprint/ruta /health."""
    for archivo in _py_files():
        texto = archivo.read_text(encoding='utf-8', errors='ignore')
        if re.search(r"route\(\s*['\"]/health['\"]", texto) or \
           re.search(r"health_bp\s*=\s*Blueprint", texto):
            return
    pytest.fail("[INF-07] no se encontró endpoint /health en app/")


def test_inf07_existe_workflow_ci():
    """CHECK BLANDO: .github/workflows/ con al menos un YAML."""
    wf = RAIZ / '.github' / 'workflows'
    assert wf.exists() and any(wf.glob('*.yml')) or any(wf.glob('*.yaml')) \
        if wf.exists() else False, (
        "[INF-07] falta CI en .github/workflows/"
    )


def test_inf07_existe_dockerfile():
    """CHECK BLANDO: Dockerfile en la raíz."""
    assert (RAIZ / 'Dockerfile').exists(), "[INF-07] falta Dockerfile"


def test_inf07_existe_script_backup():
    """CHECK BLANDO: al menos un script de backup."""
    candidatos = list(RAIZ.glob('**/backup*')) + list(RAIZ.glob('**/*backup*'))
    scripts = [c for c in candidatos
               if c.is_file() and c.suffix in ('.sh', '.ps1', '.bat', '.py')]
    assert scripts, (
        "[INF-07] no hay script de backup (.sh/.ps1/.bat/.py)"
    )


# ===================================================================
# INF-08 — Logs con logging, no print()
# ===================================================================
def test_inf08_no_hay_print_en_app():
    """
    CHECK FUERTE basado en AST: detecta llamadas REALES a print(),
    no menciones de 'print' dentro de strings o docstrings.
    """
    import ast

    hallazgos = []
    for archivo in _py_files():
        try:
            fuente = archivo.read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(fuente, filename=str(archivo))
        except SyntaxError:
            continue

        for nodo in ast.walk(tree):
            if not isinstance(nodo, ast.Call):
                continue
            func = nodo.func
            # print(...) como función global
            if isinstance(func, ast.Name) and func.id == 'print':
                hallazgos.append(
                    f"  {archivo.relative_to(RAIZ)}:{nodo.lineno}"
                )

    assert not hallazgos, (
        f"[INF-08] {len(hallazgos)} print() encontrados en app/ "
        f"(usar logging):\n" + "\n".join(hallazgos)
    )