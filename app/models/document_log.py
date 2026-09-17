from app.utils.db import get_db_connection
from datetime import date


class DocumentLog:
    # Prefijos por tipo de documento
    PREFIXES = {
        'constancia_estudio': 'CE',
        'certificacion_funciones': 'CF',
    }

    TYPE_LABELS = {
        'constancia_estudio': 'Constancia de Estudios',
        'certificacion_funciones': 'Certificación de Funciones',
    }

    @staticmethod
    def _next_sequence(doc_type, year):
        """Calcula el siguiente número correlativo para ese tipo y año."""
        conn = get_db_connection()
        if not conn:
            return 1
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(MAX(sequence), 0) + 1
            FROM documents_log
            WHERE doc_type = %s AND year = %s
        """, (doc_type, year))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else 1

    @staticmethod
    def issue(doc_type, student_id=None, teacher_id=None, issued_by=None):
        """
        Emite un nuevo documento, reservando su número correlativo.
        Devuelve el dict con el registro completo o None si falla.
        """
        year = date.today().year
        seq = DocumentLog._next_sequence(doc_type, year)
        prefix = DocumentLog.PREFIXES.get(doc_type, 'DOC')
        number = f"{prefix}-{year}-{seq:04d}"

        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO documents_log
                    (doc_type, doc_number, year, sequence,
                     student_id, teacher_id, issued_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (doc_type, number, year, seq,
                  student_id, teacher_id, issued_by))
            conn.commit()
            new_id = cursor.lastrowid
            return {
                'id': new_id,
                'doc_type': doc_type,
                'doc_number': number,
                'year': year,
                'sequence': seq,
            }
        except Exception as e:
            print(f"[DocumentLog.issue] {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def find_existing(doc_type, student_id=None, teacher_id=None):
        """
        Busca si ya existe un documento emitido para esa persona.
        Devuelve el más reciente o None.
        """
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT dl.*, u.username AS issued_by_username
            FROM documents_log dl
            LEFT JOIN users u ON dl.issued_by = u.id
            WHERE dl.doc_type = %s
        """
        params = [doc_type]
        if student_id:
            sql += " AND dl.student_id = %s"
            params.append(student_id)
        if teacher_id:
            sql += " AND dl.teacher_id = %s"
            params.append(teacher_id)
        sql += " ORDER BY dl.issued_at DESC LIMIT 1"

        cursor.execute(sql, params)
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    @staticmethod
    def get_by_id(log_id):
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT dl.*, u.username AS issued_by_username
            FROM documents_log dl
            LEFT JOIN users u ON dl.issued_by = u.id
            WHERE dl.id = %s
        """, (log_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    @staticmethod
    def mark_printed(log_id):
        """Incrementa el contador de impresiones."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE documents_log
                SET printed_count = printed_count + 1,
                    last_printed_at = NOW()
                WHERE id = %s
            """, (log_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[DocumentLog.mark_printed] {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_student(student_id):
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT dl.*, u.username AS issued_by_username
            FROM documents_log dl
            LEFT JOIN users u ON dl.issued_by = u.id
            WHERE dl.student_id = %s
            ORDER BY dl.issued_at DESC
        """, (student_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def get_by_teacher(teacher_id):
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT dl.*, u.username AS issued_by_username
            FROM documents_log dl
            LEFT JOIN users u ON dl.issued_by = u.id
            WHERE dl.teacher_id = %s
            ORDER BY dl.issued_at DESC
        """, (teacher_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows