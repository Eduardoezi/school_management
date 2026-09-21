import unittest
from datetime import date

from app.utils.calendar_import import (
    build_template_csv, parse_calendar_csv, validate_event,
)
from app.utils.ical import build_ics


class CalendarImportTests(unittest.TestCase):
    def test_generated_template_is_valid_for_requested_year(self):
        rows = parse_calendar_csv(build_template_csv("2027-2028"), "2027-2028")
        self.assertEqual(2, len(rows))
        self.assertTrue(all(row["is_valid"] for row in rows))
        self.assertEqual(date(2027, 9, 9), rows[0]["start_date"])

    def test_semicolon_csv_and_spanish_values(self):
        content = (
            "titulo;fecha_inicio;fecha_fin;origen;categoria;suspende_clases;"
            "afecta_asistencia;descripcion;pagina_fuente\n"
            "Vacaciones;2026-12-18;2027-01-10;Ministerio;vacaciones;Sí;Sí;Receso;5\n"
        ).encode("utf-8")
        rows = parse_calendar_csv(content, "2026-2027")
        self.assertTrue(rows[0]["is_valid"])
        self.assertTrue(rows[0]["affects_classes"])
        self.assertEqual("ministerio", rows[0]["origin"])

    def test_event_outside_academic_year_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "debe estar entre"):
            validate_event(
                {
                    "titulo": "Fuera de rango",
                    "fecha_inicio": "2027-09-01",
                    "origen": "Escuela",
                    "categoria": "actividad",
                },
                "2026-2027",
            )


class ICalendarTests(unittest.TestCase):
    def test_all_day_end_is_exclusive_and_text_is_escaped(self):
        content = build_ics(
            [{
                "id": 7,
                "title": "Reunión, familias",
                "start_date": date(2026, 10, 6),
                "end_date": date(2026, 10, 6),
                "origin": "escuela",
                "category": "reunion",
                "description": "Línea 1\nLínea 2",
                "affects_classes": False,
                "affects_attendance": False,
            }],
            "Calendario escolar",
        ).decode("utf-8")
        self.assertIn("DTSTART;VALUE=DATE:20261006\r\n", content)
        self.assertIn("DTEND;VALUE=DATE:20261007\r\n", content)
        self.assertIn("SUMMARY:Reunión\\, familias", content)
        self.assertTrue(content.endswith("END:VCALENDAR\r\n"))


if __name__ == "__main__":
    unittest.main()
