# scripts/encrypt_sensitive_data.py
"""
Cifra los datos médicos y socioeconómicos existentes en la BD
(SEC-09).

Qué hace:
    1. Lee cada fila de student_medical y student_socioeconomic.
    2. Cifra los campos sensibles que están en texto plano.
    3. Detecta los que YA están cifrados y los deja igual (idempotente).
    4. Guarda los cambios.

Uso:
    python scripts/encrypt_sensitive_data.py --dry-run   # ver qué haría
    python scripts/encrypt_sensitive_data.py             # aplicar

Requisitos:
    - DATA_ENCRYPTION_KEY definida en .env
    - Haber hecho backup de la BD antes
"""
import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.utils.db import get_db_connection
from app.utils.crypto import encrypt_sensitive


# Campos sensibles en cada tabla
MEDICAL_FIELDS = [
    'vaccine_others', 'allergies', 'chronic_conditions', 'convulsions',
    'current_medication', 'medical_attention', 'upen_attention',
    'fever_protocol', 'report_medical', 'report_psychological',
    'report_neurological',
]

SOCIO_FIELDS = [
    'other_family_members', 'monthly_income', 'housing_infrastructure',
]


def looks_encrypted(value: str) -> bool:
    """Fernet output empieza con 'gAAAAA' y es base64 ASCII."""
    if not value:
        return False
    return isinstance(value, str) and value.startswith('gAAAAA')


def process_table(table: str, fields: list, dry_run: bool) -> tuple:
    """Cifra los campos dados en todas las filas de la tabla."""
    conn = get_db_connection()
    if not conn:
        raise RuntimeError("No hay conexión a la BD")

    cursor = conn.cursor(dictionary=True)
    cifradas = 0
    saltadas = 0
    errores = 0

    try:
        cursor.execute(f"SELECT student_id, {', '.join(fields)} FROM {table}")
        filas = cursor.fetchall()

        for fila in filas:
            student_id = fila['student_id']
            cambios = {}

            for campo in fields:
                valor = fila.get(campo)
                if valor is None or valor == '':
                    continue
                if looks_encrypted(str(valor)):
                    saltadas += 1
                    continue

                # Convertir Decimal a str para monthly_income
                if not isinstance(valor, str):
                    valor = str(valor)

                cambios[campo] = encrypt_sensitive(valor)

            if not cambios:
                continue

            if dry_run:
                print(f"  [{table}] student_id={student_id} → cifraría "
                      f"{list(cambios.keys())}")
                cifradas += 1
                continue

            # UPDATE
            set_clause = ', '.join(f"{k} = %s" for k in cambios.keys())
            valores = list(cambios.values()) + [student_id]
            cursor.execute(
                f"UPDATE {table} SET {set_clause} WHERE student_id = %s",
                valores,
            )
            cifradas += 1

        if not dry_run:
            conn.commit()

        return cifradas, saltadas, errores

    except Exception as e:
        conn.rollback()
        print(f"ERROR en {table}: {e}")
        errores += 1
        return cifradas, saltadas, errores
    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print("=" * 60)
    print(f"  Cifrado de datos sensibles (SEC-09) "
          f"{'[DRY-RUN]' if args.dry_run else '[APLICANDO]'}")
    print("=" * 60)

    c1, s1, e1 = process_table('student_medical', MEDICAL_FIELDS, args.dry_run)
    print(f"\nstudent_medical: {c1} filas cifradas, "
          f"{s1} valores ya cifrados, {e1} errores")

    c2, s2, e2 = process_table('student_socioeconomic', SOCIO_FIELDS, args.dry_run)
    print(f"student_socioeconomic: {c2} filas cifradas, "
          f"{s2} valores ya cifrados, {e2} errores")

    if args.dry_run:
        print("\n[DRY-RUN] No se modificó nada. Quitá --dry-run para aplicar.")
    print("=" * 60)


if __name__ == '__main__':
    main()