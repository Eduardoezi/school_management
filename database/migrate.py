# database/migrate.py
"""
Runner de migraciones SQL.

Cómo funciona:
    1. Crea la tabla `schema_version` si no existe.
    2. Lee `database/migrations/*.sql` ordenados alfabéticamente.
    3. Compara con lo registrado en `schema_version`.
    4. Aplica solo los pendientes, uno por archivo, en transacción.
    5. Registra cada migración aplicada (nombre + checksum SHA256).

Uso:
    python database/migrate.py            # aplica pendientes
    python database/migrate.py --status   # muestra estado sin tocar nada
    python database/migrate.py --dry-run  # muestra qué haría
"""
import argparse
import hashlib
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import mysql.connector

from app.config import Config


MIGRATIONS_DIR = Path(__file__).resolve().parent / 'migrations'


def _conectar():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        connection_timeout=10,
        charset='utf8mb4',
        collation='utf8mb4_unicode_ci',
    )


def _crear_tabla_version(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version     VARCHAR(255) NOT NULL,
            checksum    CHAR(64)     NOT NULL,
            applied_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (version)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    cur.close()


def _ya_aplicadas(conn) -> dict[str, str]:
    """Devuelve {version: checksum} de las ya aplicadas."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT version, checksum FROM schema_version")
        return {row[0]: row[1] for row in cur.fetchall()}
    finally:
        cur.close()


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _migraciones_del_disco() -> list[Path]:
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(MIGRATIONS_DIR.glob('*.sql'))


def _aplicar(conn, path: Path) -> None:
    """Ejecuta un .sql completo en una sola transacción lógica."""
    sql = path.read_text(encoding='utf-8')
    cur = conn.cursor()
    try:
        # multi=True permite ejecutar varios statements separados por ;
        for _ in cur.execute(sql, multi=True):
            pass
        conn.commit()
    except mysql.connector.Error as e:
        conn.rollback()
        raise RuntimeError(f"Error aplicando {path.name}: {e}") from e
    finally:
        cur.close()


def _registrar(conn, version: str, checksum: str) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO schema_version (version, checksum) VALUES (%s, %s)",
            (version, checksum),
        )
        conn.commit()
    finally:
        cur.close()


def _cmd_status(conn, aplicadas: dict[str, str], pendientes: list[Path]) -> None:
    print('=' * 60)
    print('  Estado de migraciones')
    print('=' * 60)
    for path in _migraciones_del_disco():
        nombre = path.name
        if nombre in aplicadas:
            print(f'  [OK]      {nombre}')
        else:
            print(f'  [PEND]    {nombre}')
    print('=' * 60)
    print(f'  Total: {len(_migraciones_del_disco())} '
          f'| Aplicadas: {len(aplicadas)} '
          f'| Pendientes: {len(pendientes)}')


def _cmd_dry_run(pendientes: list[Path]) -> None:
    print('=' * 60)
    print('  Dry-run: se aplicarían las siguientes migraciones')
    print('=' * 60)
    for path in pendientes:
        print(f'  - {path.name}')
    if not pendientes:
        print('  (nada que hacer)')


def _cmd_aplicar(conn, pendientes: list[Path]) -> None:
    if not pendientes:
        print('Nada que hacer: no hay migraciones pendientes.')
        return

    for path in pendientes:
        print(f'Aplicando {path.name} ... ', end='', flush=True)
        inicio = datetime.now()
        _aplicar(conn, path)
        checksum = _checksum(path)
        _registrar(conn, path.name, checksum)
        delta = (datetime.now() - inicio).total_seconds()
        print(f'OK ({delta:.2f}s)')


def main() -> int:
    parser = argparse.ArgumentParser(description='Runner de migraciones')
    parser.add_argument('--status', action='store_true',
                        help='Muestra el estado sin aplicar nada')
    parser.add_argument('--dry-run', action='store_true',
                        help='Muestra qué se aplicaría sin tocar la BD')
    args = parser.parse_args()

    if not MIGRATIONS_DIR.exists():
        print(f'No existe {MIGRATIONS_DIR}', file=sys.stderr)
        return 1

    conn = _conectar()
    try:
        _crear_tabla_version(conn)
        aplicadas = _ya_aplicadas(conn)

        pendientes = [
            p for p in _migraciones_del_disco()
            if p.name not in aplicadas
        ]

        if args.status:
            _cmd_status(conn, aplicadas, pendientes)
            return 0
        if args.dry_run:
            _cmd_dry_run(pendientes)
            return 0

        _cmd_aplicar(conn, pendientes)
        return 0
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())