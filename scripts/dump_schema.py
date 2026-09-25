# scripts/dump_schema.py
"""
Extrae la estructura completa de la BD (tablas, índices, FKs) y la
guarda en database/schema.sql. NO exporta datos.

Uso:
    python scripts/dump_schema.py
"""
import sys
from pathlib import Path

# ------------------------------------------------------------
# IMPORTANTE: agregar la raíz del proyecto al sys.path ANTES
# de importar app.*. Cuando corrés `python scripts/dump_schema.py`,
# Python pone `scripts/` en sys.path[0], no la raíz. Sin este
# insert, `import app` falla con ModuleNotFoundError.
# ------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# Recién ahora se pueden importar módulos del proyecto
import mysql.connector

from app.config import Config


OUT = RAIZ / 'database' / 'schema.sql'


def main():
    OUT.parent.mkdir(exist_ok=True)

    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
    )
    cur = conn.cursor()

    cur.execute("SHOW TABLES")
    tablas = [r[0] for r in cur.fetchall()]

    with OUT.open('w', encoding='utf-8') as f:
        f.write(f"-- Schema de `{Config.MYSQL_DB}`\n")
        f.write("-- Generado automáticamente por scripts/dump_schema.py\n")
        f.write("-- Solo estructura; sin datos.\n\n")
        f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

        for t in tablas:
            cur.execute(f"SHOW CREATE TABLE `{t}`")
            row = cur.fetchone()
            f.write(f"-- ---------- {t} ----------\n")
            f.write(row[1] + ";\n\n")

        f.write("SET FOREIGN_KEY_CHECKS=1;\n")

    cur.close()
    conn.close()
    print(f"OK: {OUT} ({len(tablas)} tablas)")


if __name__ == '__main__':
    main()