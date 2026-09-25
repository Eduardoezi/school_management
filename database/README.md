markdown
# Base de datos — Migraciones

## Estructura
database/
├── README.md ← este archivo
├── schema.sql ← volcado de referencia (para onboardear)
├── migrate.py ← runner de migraciones
└── migrations/
├── 001_schema_inicial.sql
└── 002_*.sql ← agregar acá las futuras

## Cómo aplicar migraciones

python database/migrate.py
Aplica todas las pendientes en orden. Crea la tabla schema_version
automáticamente y registra cada una con su checksum SHA256.

Ver estado sin aplicar nada

python database/migrate.py --status
Ver qué se aplicaría (dry-run)

python database/migrate.py --dry-run

Cómo agregar una migración nueva
Crear database/migrations/NNN_descripcion_corta.sql.

NNN es un número de 3 dígitos consecutivo (003, 004, ...).

Un archivo = un cambio lógico.

Idempotente cuando sea posible (IF NOT EXISTS, chequeos previos).

Probar en local:

python database/migrate.py --dry-run
python database/migrate.py
Commitear el .sql junto con el cambio de código que lo necesita.

Reglas
Nunca editar una migración ya aplicada. Si hay que corregir,
se agrega una nueva que revierta/ajuste.

Nunca borrar un archivo de migrations/ que ya está en producción.

Los .sql usan utf8mb4. No cambiar el charset sin migrar data.

Cómo onboardear a un colaborador

# 1. Clonar el repo
git clone <repo>

# 2. Crear la BD vacía
mysql -u root -p -e "CREATE DATABASE school_db CHARACTER SET utf8mb4"

# 3. Aplicar todas las migraciones
python database/migrate.py

# Listo: la BD tiene el esquema completo.
schema.sql es solo para referencia humana / diff manual.
La fuente de verdad del esquema son las migraciones.