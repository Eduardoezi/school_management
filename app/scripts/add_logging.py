# scripts/add_logging.py
"""
Inserta automáticamente:
    - `import logging` antes del primer import top-level
    - `logger = logging.getLogger(__name__)` después del último import

en todos los .py de app/models/.

Uso:
    python scripts/add_logging.py

No hace nada si el archivo ya tiene `getLogger(__name__)`.
Hace backup .bak de cada archivo tocado.
"""
import ast
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TARGET_DIR = RAIZ / 'app' / 'models'
LOGGER_LINE = 'logger = logging.getLogger(__name__)\n'


def _linea_primer_import(tree) -> int | None:
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return node.lineno
    return None


def _linea_ultimo_import(tree) -> int | None:
    last = None
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last = node.end_lineno
    return last


def _ya_importa_logging(tree) -> bool:
    for node in tree.body:
        if isinstance(node, ast.Import):
            if any(a.name == 'logging' for a in node.names):
                return True
    return False


def procesar(path: Path) -> str:
    fuente = path.read_text(encoding='utf-8')

    if 'getLogger(__name__)' in fuente:
        return 'SKIP (ya tiene logger)'

    try:
        tree = ast.parse(fuente, filename=str(path))
    except SyntaxError as e:
        return f'ERROR sintaxis: {e}'

    primer = _linea_primer_import(tree)
    ultimo = _linea_ultimo_import(tree)
    if primer is None or ultimo is None:
        return 'SKIP (sin imports top-level)'

    ya_logging = _ya_importa_logging(tree)

    # Backup antes de tocar
    shutil.copy2(path, path.with_suffix(path.suffix + '.bak'))

    lineas = fuente.splitlines(keepends=True)

    # Insertar de atrás hacia adelante para no descolocar índices
    nuevas = lineas[:]

    # 1) logger tras el último import
    nuevas[ultimo:ultimo] = ['\n', LOGGER_LINE]

    # 2) import logging antes del primer import (si no existe)
    if not ya_logging:
        nuevas[primer - 1:primer - 1] = ['import logging\n']

    path.write_text(''.join(nuevas), encoding='utf-8')
    accion_imp = 'ya estaba' if ya_logging else f'insertado en línea {primer}'
    return f'OK (import: {accion_imp}, logger tras línea {ultimo})'


if __name__ == '__main__':
    if not TARGET_DIR.exists():
        print(f'No existe {TARGET_DIR}')
        raise SystemExit(1)

    for f in sorted(TARGET_DIR.glob('*.py')):
        if f.name == '__init__.py':
            continue
        print(f'{f.name:40s} -> {procesar(f)}')