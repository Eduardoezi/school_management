# scripts/fix_future_imports.py
"""
Repara archivos donde `import logging` quedó ANTES de
`from __future__ import ...`, lo cual es un SyntaxError.

Mueve la línea `import logging` para que quede justo después
de la línea de __future__.

Uso:
    python scripts/fix_future_imports.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TARGET = RAIZ / 'app'   # recorre app/ completo (models + routes + ...)


def reparar(path: Path) -> str:
    lineas = path.read_text(encoding='utf-8').splitlines(keepends=True)
    if not lineas:
        return 'vacío'

    idx_logging = None
    idx_future = None
    for i, l in enumerate(lineas):
        s = l.strip()
        if idx_logging is None and s == 'import logging':
            idx_logging = i
        if idx_future is None and s.startswith('from __future__ import'):
            idx_future = i

    if idx_logging is None or idx_future is None:
        return 'nada que hacer'
    if idx_logging > idx_future:
        return 'ya está bien'

    # Sacar la línea de logging y reinsertarla justo después de __future__
    linea_logging = lineas.pop(idx_logging)
    if idx_logging < idx_future:
        idx_future -= 1
    lineas.insert(idx_future + 1, linea_logging)

    path.write_text(''.join(lineas), encoding='utf-8')
    return f'FIX (logging movido de línea {idx_logging + 1} a {idx_future + 2})'


if __name__ == '__main__':
    if not TARGET.exists():
        print(f'No existe {TARGET}')
        sys.exit(1)

    tocados = 0
    for f in sorted(TARGET.rglob('*.py')):
        if f.name == '__init__.py':
            continue
        resultado = reparar(f)
        if resultado.startswith('FIX'):
            tocados += 1
            print(f'{f.relative_to(RAIZ)}  ->  {resultado}')

    print(f'\nTotal reparados: {tocados}')