# scripts/smoke_test_sec09.py
"""
Smoke test del cifrado de datos sensibles (SEC-09).

Inserta un estudiante ficticio, guarda datos médicos y socioeconómicos,
lee de vuelta, verifica que coincidan, y limpia.

Uso:
    python scripts/smoke_test_sec09.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.utils.db import get_db_connection
from app.models.medical_info import MedicalInfo
from app.models.socioeconomic_info import SocioeconomicInfo


TEST_STUDENT_ID = 999999  # ID ficticio, no debe existir en la BD


def _ensure_test_student():
    """Crea un estudiante ficticio si no existe (para FK)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM students WHERE id = %s", (TEST_STUDENT_ID,))
        if cursor.fetchone():
            return
        cursor.execute("""
            INSERT INTO students (id, school_id, first_name, last_name,
                                  multiple_birth_order)
            VALUES (%s, %s, %s, %s, %s)
        """, (TEST_STUDENT_ID, f'SMOKE{TEST_STUDENT_ID}', 'Smoke', 'Test', 1))
        conn.commit()
        print(f"  Estudiante de prueba creado (id={TEST_STUDENT_ID})")
    finally:
        cursor.close()
        conn.close()


def _cleanup():
    """Borra todo rastro del test."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM student_medical WHERE student_id = %s", (TEST_STUDENT_ID,))
        cursor.execute("DELETE FROM student_socioeconomic WHERE student_id = %s", (TEST_STUDENT_ID,))
        cursor.execute("DELETE FROM students WHERE id = %s", (TEST_STUDENT_ID,))
        conn.commit()
        print("  Limpieza completada")
    finally:
        cursor.close()
        conn.close()


def main():
    print("=" * 60)
    print("  Smoke test SEC-09 — cifrado de datos sensibles")
    print("=" * 60)

    _ensure_test_student()

    # ------------------ MÉDICO ------------------
    print("\n[1] Guardando datos médicos de prueba...")
    ok = MedicalInfo.save(TEST_STUDENT_ID, {
        'allergies': 'Penicilina, maní',
        'chronic_conditions': 'Asma leve controlada',
        'convulsions': None,
        'current_medication': 'Salbutamol según necesidad',
        'medical_attention': 'Control pediátrico cada 6 meses',
        'upen_attention': None,
        'report_medical': 'Informe de prueba',
        'report_psychological': 'Sin observaciones',
        'report_neurological': None,
        'vaccine_others': 'Refuerzo adicional',
    })
    assert ok, "❌ MedicalInfo.save() falló"

    print("[2] Leyendo y comparando...")
    med = MedicalInfo.get_by_student(TEST_STUDENT_ID)
    assert med is not None, "❌ No se leyó la fila"
    assert med['allergies'] == 'Penicilina, maní', \
        f"❌ allergies mal: {med['allergies']!r}"
    assert med['chronic_conditions'] == 'Asma leve controlada', \
        f"❌ chronic mal: {med['chronic_conditions']!r}"
    assert med['report_psychological'] == 'Sin observaciones', \
        f"❌ report_psych mal: {med['report_psychological']!r}"
    print("  ✅ Datos médicos ida y vuelta OK")

    # ------------------ SOCIOECONÓMICO ------------------
    print("\n[3] Guardando datos socioeconómicos de prueba...")
    ok = SocioeconomicInfo.save(TEST_STUDENT_ID, {
        'lives_with': 'Madre y abuela',
        'other_family_members': 'Dos hermanos menores',
        'monthly_income': '1500.00',
        'working_members': 1,
        'household_members': 4,
        'housing_type': 'Casa propia',
        'rooms_count': 3,
        'housing_condition': 'Buena',
        'housing_infrastructure': 'Agua, luz, gas',
    })
    assert ok, "❌ SocioeconomicInfo.save() falló"

    print("[4] Leyendo y comparando...")
    soc = SocioeconomicInfo.get_by_student(TEST_STUDENT_ID)
    assert soc is not None, "❌ No se leyó la fila"
    assert soc['other_family_members'] == 'Dos hermanos menores', \
        f"❌ other_family_members mal: {soc['other_family_members']!r}"
    assert soc['housing_infrastructure'] == 'Agua, luz, gas', \
        f"❌ housing_infrastructure mal: {soc['housing_infrastructure']!r}"
    assert str(soc['monthly_income']) == '1500.00', \
        f"❌ monthly_income mal: {soc['monthly_income']!r}"
    print("  ✅ Datos socioeconómicos ida y vuelta OK")

    # ------------------ VERIFICAR CIFRADO EN BD ------------------
    print("\n[5] Verificando que en la BD está cifrado...")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT allergies FROM student_medical WHERE student_id = %s",
        (TEST_STUDENT_ID,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    crudo = row[0]
    assert crudo.startswith('gAAAAA'), \
        f"❌ En la BD NO está cifrado: {crudo[:50]!r}"
    print(f"  ✅ En BD: {crudo[:40]}...")

    # ------------------ LIMPIEZA ------------------
    print("\n[6] Limpiando...")
    _cleanup()

    print("\n" + "=" * 60)
    print("  ✅ SMOKE TEST OK — el cifrado funciona end-to-end")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except AssertionError as e:
        print(f"\n{e}")
        print("\nIntentando limpiar...")
        try:
            _cleanup()
        except Exception:
            pass
        sys.exit(1)