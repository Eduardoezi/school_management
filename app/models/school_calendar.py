"""Persistencia del calendario escolar, importaciones y bitácora."""

from __future__ import annotations

import json
from threading import Lock

from app.utils.db import get_db_connection
import logging

# ============================================================
# Logger del módulo
# ============================================================
logger = logging.getLogger(__name__)


class SchoolCalendar:
    _schema_ready = False
    _schema_lock = Lock()

    @classmethod
    def ensure_schema(cls) -> bool:
        if cls._schema_ready:
            return True
        with cls._schema_lock:
            if cls._schema_ready:
                return True
            conn = get_db_connection()
            if not conn:
                return False
            cursor = conn.cursor()
            statements = [
                """
                CREATE TABLE IF NOT EXISTS school_calendars (
                    id INT NOT NULL AUTO_INCREMENT,
                    academic_year VARCHAR(9) NOT NULL,
                    title VARCHAR(150) NOT NULL,
                    status ENUM('draft','published','archived') NOT NULL DEFAULT 'draft',
                    source_original_name VARCHAR(255) DEFAULT NULL,
                    source_stored_name VARCHAR(255) DEFAULT NULL,
                    source_sha256 CHAR(64) DEFAULT NULL,
                    created_by INT DEFAULT NULL,
                    published_by INT DEFAULT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    published_at DATETIME DEFAULT NULL,
                    PRIMARY KEY (id),
                    KEY idx_school_calendars_year_status (academic_year, status),
                    CONSTRAINT fk_school_calendars_created_by FOREIGN KEY (created_by)
                        REFERENCES users(id) ON DELETE SET NULL,
                    CONSTRAINT fk_school_calendars_published_by FOREIGN KEY (published_by)
                        REFERENCES users(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
                """,
                """
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id INT NOT NULL AUTO_INCREMENT,
                    calendar_id INT NOT NULL,
                    origin ENUM('ministerio','escuela') NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    category VARCHAR(50) NOT NULL DEFAULT 'actividad',
                    description TEXT DEFAULT NULL,
                    affects_classes TINYINT(1) NOT NULL DEFAULT 0,
                    affects_attendance TINYINT(1) NOT NULL DEFAULT 0,
                    source_page SMALLINT UNSIGNED DEFAULT NULL,
                    active TINYINT(1) NOT NULL DEFAULT 1,
                    created_by INT DEFAULT NULL,
                    updated_by INT DEFAULT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    KEY idx_calendar_events_range (calendar_id, start_date, end_date),
                    KEY idx_calendar_events_origin (calendar_id, origin, active),
                    CONSTRAINT fk_calendar_events_calendar FOREIGN KEY (calendar_id)
                        REFERENCES school_calendars(id) ON DELETE CASCADE,
                    CONSTRAINT fk_calendar_events_created_by FOREIGN KEY (created_by)
                        REFERENCES users(id) ON DELETE SET NULL,
                    CONSTRAINT fk_calendar_events_updated_by FOREIGN KEY (updated_by)
                        REFERENCES users(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
                """,
                """
                CREATE TABLE IF NOT EXISTS calendar_imports (
                    id INT NOT NULL AUTO_INCREMENT,
                    calendar_id INT NOT NULL,
                    original_name VARCHAR(255) NOT NULL,
                    file_sha256 CHAR(64) NOT NULL,
                    status ENUM('preview','imported','rejected') NOT NULL DEFAULT 'preview',
                    row_count INT NOT NULL DEFAULT 0,
                    valid_count INT NOT NULL DEFAULT 0,
                    error_count INT NOT NULL DEFAULT 0,
                    imported_by INT DEFAULT NULL,
                    confirmed_by INT DEFAULT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at DATETIME DEFAULT NULL,
                    PRIMARY KEY (id),
                    KEY idx_calendar_imports_calendar (calendar_id, created_at),
                    CONSTRAINT fk_calendar_imports_calendar FOREIGN KEY (calendar_id)
                        REFERENCES school_calendars(id) ON DELETE CASCADE,
                    CONSTRAINT fk_calendar_imports_imported_by FOREIGN KEY (imported_by)
                        REFERENCES users(id) ON DELETE SET NULL,
                    CONSTRAINT fk_calendar_imports_confirmed_by FOREIGN KEY (confirmed_by)
                        REFERENCES users(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
                """,
                """
                CREATE TABLE IF NOT EXISTS calendar_import_rows (
                    id INT NOT NULL AUTO_INCREMENT,
                    import_id INT NOT NULL,
                    source_row INT NOT NULL,
                    raw_data LONGTEXT NOT NULL,
                    origin ENUM('ministerio','escuela') DEFAULT NULL,
                    title VARCHAR(200) DEFAULT NULL,
                    start_date DATE DEFAULT NULL,
                    end_date DATE DEFAULT NULL,
                    category VARCHAR(50) DEFAULT NULL,
                    description TEXT DEFAULT NULL,
                    affects_classes TINYINT(1) NOT NULL DEFAULT 0,
                    affects_attendance TINYINT(1) NOT NULL DEFAULT 0,
                    source_page SMALLINT UNSIGNED DEFAULT NULL,
                    is_valid TINYINT(1) NOT NULL DEFAULT 0,
                    error_message VARCHAR(500) DEFAULT NULL,
                    PRIMARY KEY (id),
                    KEY idx_calendar_import_rows_import (import_id, source_row),
                    CONSTRAINT fk_calendar_import_rows_import FOREIGN KEY (import_id)
                        REFERENCES calendar_imports(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
                """,
                """
                CREATE TABLE IF NOT EXISTS calendar_audit_log (
                    id BIGINT NOT NULL AUTO_INCREMENT,
                    calendar_id INT DEFAULT NULL,
                    event_id INT DEFAULT NULL,
                    action VARCHAR(50) NOT NULL,
                    details LONGTEXT DEFAULT NULL,
                    user_id INT DEFAULT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    KEY idx_calendar_audit_calendar (calendar_id, created_at),
                    CONSTRAINT fk_calendar_audit_calendar FOREIGN KEY (calendar_id)
                        REFERENCES school_calendars(id) ON DELETE SET NULL,
                    CONSTRAINT fk_calendar_audit_user FOREIGN KEY (user_id)
                        REFERENCES users(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
                """,
            ]
            try:
                for statement in statements:
                    cursor.execute(statement)
                conn.commit()
                cls._schema_ready = True
                return True
            except Exception as exc:
                conn.rollback()
                logger.exception("Error en el metodo ensure_schema de la clase SchoolCalendar: %s", exc)
                return False
            finally:
                cursor.close()
                conn.close()

    @classmethod
    def _conn(cls):
        if not cls.ensure_schema():
            return None
        return get_db_connection()

    @staticmethod
    def _audit(cursor, action, user_id, calendar_id=None, event_id=None, details=None):
        cursor.execute(
            """
            INSERT INTO calendar_audit_log
                (calendar_id, event_id, action, details, user_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                calendar_id, event_id, action,
                json.dumps(details or {}, ensure_ascii=False, default=str), user_id,
            ),
        )

    @classmethod
    def create(cls, data: dict, user_id: int):
        conn = cls._conn()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO school_calendars
                    (academic_year, title, source_original_name,
                     source_stored_name, source_sha256, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    data["academic_year"], data["title"],
                    data.get("source_original_name"), data.get("source_stored_name"),
                    data.get("source_sha256"), user_id,
                ),
            )
            calendar_id = cursor.lastrowid
            cls._audit(cursor, "calendar.created", user_id, calendar_id, details=data)
            conn.commit()
            return calendar_id
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en el metodo create de la clase SchoolCalendar: %s", exc)
            return None
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def get(cls, calendar_id: int):
        conn = cls._conn()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT c.*, creator.username AS created_by_username,
                       publisher.username AS published_by_username,
                       (SELECT COUNT(*) FROM calendar_events e
                         WHERE e.calendar_id = c.id AND e.active = 1) AS event_count
                  FROM school_calendars c
                  LEFT JOIN users creator ON creator.id = c.created_by
                  LEFT JOIN users publisher ON publisher.id = c.published_by
                 WHERE c.id = %s
                """,
                (calendar_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def get_all(cls, published_only=False):
        conn = cls._conn()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT c.*,
                       (SELECT COUNT(*) FROM calendar_events e
                         WHERE e.calendar_id = c.id AND e.active = 1) AS event_count
                  FROM school_calendars c
            """
            if published_only:
                sql += " WHERE c.status = 'published'"
            sql += " ORDER BY c.academic_year DESC, c.created_at DESC"
            cursor.execute(sql)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def get_current_published(cls):
        conn = cls._conn()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT c.*,
                       (SELECT COUNT(*) FROM calendar_events e
                         WHERE e.calendar_id = c.id AND e.active = 1) AS event_count
                  FROM school_calendars c
                 WHERE c.status = 'published'
                 ORDER BY c.academic_year DESC, c.published_at DESC
                 LIMIT 1
                """
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def publish(cls, calendar_id: int, user_id: int) -> bool:
        conn = cls._conn()
        if not conn:
            return False
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT academic_year FROM school_calendars WHERE id=%s FOR UPDATE", (calendar_id,))
            calendar_row = cursor.fetchone()
            if not calendar_row:
                return False
            cursor.execute(
                "SELECT COUNT(*) AS total FROM calendar_events WHERE calendar_id=%s AND active=1",
                (calendar_id,),
            )
            if cursor.fetchone()["total"] == 0:
                return False
            cursor.execute(
                """
                UPDATE school_calendars
                   SET status='archived'
                 WHERE academic_year=%s AND status='published' AND id<>%s
                """,
                (calendar_row["academic_year"], calendar_id),
            )
            cursor.execute(
                """
                UPDATE school_calendars
                   SET status='published', published_by=%s, published_at=NOW()
                 WHERE id=%s
                """,
                (user_id, calendar_id),
            )
            cls._audit(cursor, "calendar.published", user_id, calendar_id)
            conn.commit()
            return True
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en el metodo publish de la clase SchoolCalendar: %s", exc)
            return False
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def get_events(cls, calendar_id: int, scope="both", start_date=None, end_date=None):
        conn = cls._conn()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT e.*, creator.username AS created_by_username,
                       updater.username AS updated_by_username
                  FROM calendar_events e
                  LEFT JOIN users creator ON creator.id=e.created_by
                  LEFT JOIN users updater ON updater.id=e.updated_by
                 WHERE e.calendar_id=%s AND e.active=1
            """
            params = [calendar_id]
            if scope in ("ministerio", "escuela"):
                sql += " AND e.origin=%s"
                params.append(scope)
            if start_date is not None and end_date is not None:
                sql += " AND e.start_date <= %s AND e.end_date >= %s"
                params.extend([end_date, start_date])
            sql += " ORDER BY e.start_date, e.end_date, e.title"
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def get_event(cls, event_id: int):
        conn = cls._conn()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM calendar_events WHERE id=%s AND active=1", (event_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def create_event(cls, calendar_id: int, data: dict, user_id: int):
        conn = cls._conn()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO calendar_events
                    (calendar_id, origin, title, start_date, end_date, category,
                     description, affects_classes, affects_attendance, source_page,
                     created_by, updated_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    calendar_id, data["origin"], data["title"], data["start_date"],
                    data["end_date"], data["category"], data.get("description"),
                    data["affects_classes"], data["affects_attendance"],
                    data.get("source_page"), user_id, user_id,
                ),
            )
            event_id = cursor.lastrowid
            cls._audit(cursor, "event.created", user_id, calendar_id, event_id, data)
            conn.commit()
            return event_id
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en el metodo create_event de la clase SchoolCalendar: %s", exc)
            return None
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def update_event(cls, event_id: int, data: dict, user_id: int) -> bool:
        current = cls.get_event(event_id)
        if not current:
            return False
        conn = cls._conn()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE calendar_events
                   SET origin=%s, title=%s, start_date=%s, end_date=%s,
                       category=%s, description=%s, affects_classes=%s,
                       affects_attendance=%s, source_page=%s, updated_by=%s
                 WHERE id=%s AND active=1
                """,
                (
                    data["origin"], data["title"], data["start_date"], data["end_date"],
                    data["category"], data.get("description"), data["affects_classes"],
                    data["affects_attendance"], data.get("source_page"), user_id, event_id,
                ),
            )
            updated = cursor.rowcount > 0
            if not updated:
                conn.rollback()
                return False
            cls._audit(
                cursor, "event.updated", user_id, current["calendar_id"], event_id,
                {"before": current, "after": data},
            )
            conn.commit()
            return True
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en el metodo update_event de la clase SchoolCalendar: %s", exc)
            return False
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def delete_event(cls, event_id: int, user_id: int) -> bool:
        current = cls.get_event(event_id)
        if not current:
            return False
        conn = cls._conn()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE calendar_events SET active=0, updated_by=%s WHERE id=%s AND active=1",
                (user_id, event_id),
            )
            deleted = cursor.rowcount > 0
            if not deleted:
                conn.rollback()
                return False
            cls._audit(cursor, "event.deleted", user_id, current["calendar_id"], event_id, current)
            conn.commit()
            return True
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en el metodo delete_event de la clase SchoolCalendar: %s", exc)
            return False
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def create_import(cls, calendar_id, original_name, file_sha256, rows, user_id):
        conn = cls._conn()
        if not conn:
            return None
        cursor = conn.cursor()
        valid_count = sum(1 for row in rows if row["is_valid"])
        try:
            cursor.execute(
                """
                INSERT INTO calendar_imports
                    (calendar_id, original_name, file_sha256, row_count,
                     valid_count, error_count, imported_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    calendar_id, original_name, file_sha256, len(rows), valid_count,
                    len(rows) - valid_count, user_id,
                ),
            )
            import_id = cursor.lastrowid
            sql = """
                INSERT INTO calendar_import_rows
                    (import_id, source_row, raw_data, origin, title, start_date,
                     end_date, category, description, affects_classes,
                     affects_attendance, source_page, is_valid, error_message)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            for row in rows:
                cursor.execute(sql, (
                    import_id, row["row_number"],
                    json.dumps(row["raw_data"], ensure_ascii=False),
                    row.get("origin"), row.get("title"), row.get("start_date"),
                    row.get("end_date"), row.get("category"), row.get("description"),
                    row.get("affects_classes", False), row.get("affects_attendance", False),
                    row.get("source_page"), row["is_valid"], row.get("error_message"),
                ))
            cls._audit(
                cursor, "import.previewed", user_id, calendar_id,
                details={"import_id": import_id, "rows": len(rows), "valid": valid_count},
            )
            conn.commit()
            return import_id
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en el metodo create_import de la clase SchoolCalendar: %s", exc)
            return None
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def get_import(cls, import_id):
        conn = cls._conn()
        if not conn:
            return None, []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT i.*, c.academic_year, c.title AS calendar_title
                  FROM calendar_imports i
                  JOIN school_calendars c ON c.id=i.calendar_id
                 WHERE i.id=%s
                """,
                (import_id,),
            )
            batch = cursor.fetchone()
            cursor.execute(
                "SELECT * FROM calendar_import_rows WHERE import_id=%s ORDER BY source_row",
                (import_id,),
            )
            return batch, cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def confirm_import(cls, import_id: int, user_id: int) -> bool:
        conn = cls._conn()
        if not conn:
            return False
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM calendar_imports WHERE id=%s FOR UPDATE", (import_id,))
            batch = cursor.fetchone()
            if not batch or batch["status"] != "preview" or batch["error_count"]:
                return False
            cursor.execute(
                "SELECT * FROM calendar_import_rows WHERE import_id=%s AND is_valid=1 ORDER BY source_row",
                (import_id,),
            )
            rows = cursor.fetchall()
            if not rows:
                return False
            insert_sql = """
                INSERT INTO calendar_events
                    (calendar_id, origin, title, start_date, end_date, category,
                     description, affects_classes, affects_attendance, source_page,
                     created_by, updated_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            for row in rows:
                cursor.execute(insert_sql, (
                    batch["calendar_id"], row["origin"], row["title"], row["start_date"],
                    row["end_date"], row["category"], row["description"],
                    row["affects_classes"], row["affects_attendance"], row["source_page"],
                    user_id, user_id,
                ))
            cursor.execute(
                """
                UPDATE calendar_imports
                   SET status='imported', confirmed_by=%s, confirmed_at=NOW()
                 WHERE id=%s
                """,
                (user_id, import_id),
            )
            cls._audit(
                cursor, "import.confirmed", user_id, batch["calendar_id"],
                details={"import_id": import_id, "events": len(rows)},
            )
            conn.commit()
            return True
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en el metodo confirm_import de la clase SchoolCalendar: %s", exc)
            return False
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def get_audit(cls, calendar_id: int, limit=100):
        conn = cls._conn()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT a.*, u.username
                  FROM calendar_audit_log a
                  LEFT JOIN users u ON u.id=a.user_id
                 WHERE a.calendar_id=%s
                 ORDER BY a.created_at DESC, a.id DESC
                 LIMIT %s
                """,
                (calendar_id, limit),
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
