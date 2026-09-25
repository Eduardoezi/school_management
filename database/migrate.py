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

Notas sobre mysql-connector-python >= 9.2.0:
    - execute() acepta múltiples statements separados por `;` SIN `multi=True`.
    - Es obligatorio consumir TODOS los result sets con `nextset()` antes
      de hacer commit(); si no, MySQL tira "Commands out of sync".
    Ref: https://dev.mysql.com/doc/connector-python/en/connector-python-multi.html
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


# ============================================================
# Conexión
# ============================================================
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


# ============================================================
# Tabla de control
# ============================================================
def _crear_tabla_version(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version     VARCHAR(255) NOT NULL,
                checksum    CHAR(64)     NOT NULL,
                applied_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (version)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        # Drenar por las dudas (CREATE TABLE no devuelve filas, pero
        # algunos conectores dejan un set pendiente igual).
        while cur.nextset() is not None:
            pass
        conn.commit()
    finally:
        cur.close()


def _ya_aplicadas(conn) -> dict:
    """Devuelve {version: checksum} de las ya aplicadas."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT version, checksum FROM schema_version")
        return {row[0]: row[1] for row in cur.fetchall()}
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


# ============================================================
# Migraciones
# ============================================================
def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _migraciones_del_disco() -> list:
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(MIGRATIONS_DIR.glob('*.sql'))


def _drenar_result_sets(cur) -> None:
    """
    Consume todos los result sets pendientes del cursor.

    Necesario en mysql-connector-python >= 9.2.0 tras ejecutar un
    script con múltiples statements. Sin esto, el próximo commit()
    falla con "Commands out of sync".

    - nextset() devuelve None cuando no hay más sets.
    - En sets sin filas (CREATE TABLE, SET, etc.), fetchall() puede
      tirar InterfaceError; lo ignoramos.
    """
    while cur.nextset() is not None:
        try:
            cur.fetchall()
        except mysql.connector.InterfaceError:
            pass


def _aplicar(conn, path: Path) -> None:
    """Ejecuta un .sql completo en una sola transacción lógica."""
    sql = path.read_text(encoding='utf-8')
    cur = conn.cursor()
    try:
        cur.execute(sql)
        _drenar_result_sets(cur)
        conn.commit()
    except mysql.connector.Error as e:
        try:
            conn.rollback()
        except mysql.connector.Error:
            pass
        raise RuntimeError(
            f"Error aplicando {path.name}: {e}"
        ) from e
    finally:
        cur.close()


# ============================================================
# Comandos
# ============================================================
def _cmd_status(aplicadas: dict, pendientes: list) -> None:
    print('=' * 60)
    print('  Estado de migraciones')
    print('=' * 60)
    for path in _migraciones_del_disco():
        nombre = path.name
        marca = '[OK]  ' if nombre in aplicadas else '[PEND]'
        print(f'  {marca}    {nombre}')
    print('=' * 60)
    print(f'  Total: {len(_migraciones_del_disco())} '
          f'| Aplicadas: {len(aplicadas)} '
          f'| Pendientes: {len(pendientes)}')


def _cmd_dry_run(pendientes: list) -> None:
    print('=' * 60)
    print('  Dry-run: se aplicarían las siguientes migraciones')
    print('=' * 60)
    for path in pendientes:
        print(f'  - {path.name}')
    if not pendientes:
        print('  (nada que hacer)')


def _cmd_aplicar(conn, pendientes: list) -> None:
    if not pendientes:
        print('Nada que hacer: no hay migraciones pendientes.')
        return

    for path in pendientes:
        print(f'Aplicando {path.name} ... ', end='', flush=True)
        inicio = datetime.now()
        try:
            _aplicar(conn, path)
            checksum = _checksum(path)
            _registrar(conn, path.name, checksum)
            delta = (datetime.now() - inicio).total_seconds()
            print(f'OK ({delta:.2f}s)')
        except RuntimeError as e:
            print('FALLÓ')
            print(f'  {e}', file=sys.stderr)
            raise


# ============================================================
# Main
# ============================================================
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
            _cmd_status(aplicadas, pendientes)
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