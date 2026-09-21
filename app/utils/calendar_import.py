"""Validación y normalización de cargas del calendario escolar."""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import date


CATEGORIES = (
    "academico",
    "administrativo",
    "asueto",
    "actividad",
    "efemeride",
    "evaluacion",
    "reunion",
    "vacaciones",
)

TEMPLATE_HEADERS = (
    "titulo",
    "fecha_inicio",
    "fecha_fin",
    "origen",
    "categoria",
    "suspende_clases",
    "afecta_asistencia",
    "descripcion",
    "pagina_fuente",
)


def _key(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


HEADER_ALIASES = {
    "title": "titulo",
    "start_date": "fecha_inicio",
    "end_date": "fecha_fin",
    "origin": "origen",
    "scope": "origen",
    "category": "categoria",
    "affects_classes": "suspende_clases",
    "affects_attendance": "afecta_asistencia",
    "description": "descripcion",
    "source_page": "pagina_fuente",
}


def academic_year_bounds(academic_year: str) -> tuple[date, date]:
    match = re.fullmatch(r"(\d{4})-(\d{4})", str(academic_year or "").strip())
    if not match or int(match.group(2)) != int(match.group(1)) + 1:
        raise ValueError("El año escolar debe tener el formato 2026-2027.")
    start_year, end_year = map(int, match.groups())
    return date(start_year, 9, 1), date(end_year, 8, 31)


def _parse_date(value, field_name: str) -> date:
    raw = str(value or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{field_name} debe usar el formato AAAA-MM-DD.") from exc


def _parse_bool(value, field_name: str) -> bool:
    raw = _key(value)
    if raw in {"", "no", "n", "0", "false"}:
        return False
    if raw in {"si", "s", "1", "true", "x"}:
        return True
    raise ValueError(f"{field_name} debe indicar Sí o No.")


def _parse_origin(value) -> str:
    raw = _key(value)
    if raw in {"ministerio", "ministerial", "escolar", "oficial"}:
        return "ministerio"
    if raw in {"escuela", "institucional", "plantel"}:
        return "escuela"
    raise ValueError("origen debe ser Ministerio o Escuela.")


def validate_event(data: dict, academic_year: str) -> dict:
    """Valida un evento proveniente de formulario o CSV."""
    title = str(data.get("titulo") or data.get("title") or "").strip()
    if not title:
        raise ValueError("El título es obligatorio.")
    if len(title) > 200:
        raise ValueError("El título no puede superar 200 caracteres.")

    start_date = _parse_date(
        data.get("fecha_inicio") or data.get("start_date"), "fecha_inicio"
    )
    end_raw = data.get("fecha_fin") or data.get("end_date") or start_date.isoformat()
    end_date = _parse_date(end_raw, "fecha_fin")
    if end_date < start_date:
        raise ValueError("fecha_fin no puede ser anterior a fecha_inicio.")

    year_start, year_end = academic_year_bounds(academic_year)
    if start_date < year_start or end_date > year_end:
        raise ValueError(
            f"El evento debe estar entre {year_start.isoformat()} y {year_end.isoformat()}."
        )

    category = _key(data.get("categoria") or data.get("category") or "actividad")
    if category not in CATEGORIES:
        raise ValueError("Categoría no reconocida.")

    source_page = data.get("pagina_fuente") or data.get("source_page") or None
    if source_page not in (None, ""):
        try:
            source_page = int(source_page)
        except (TypeError, ValueError) as exc:
            raise ValueError("pagina_fuente debe ser un número.") from exc
        if not 1 <= source_page <= 999:
            raise ValueError("pagina_fuente debe estar entre 1 y 999.")
    else:
        source_page = None

    description = str(data.get("descripcion") or data.get("description") or "").strip()
    if len(description) > 4000:
        raise ValueError("La descripción no puede superar 4000 caracteres.")

    return {
        "title": title,
        "start_date": start_date,
        "end_date": end_date,
        "origin": _parse_origin(data.get("origen") or data.get("origin") or "escuela"),
        "category": category,
        "affects_classes": _parse_bool(
            data.get("suspende_clases", data.get("affects_classes", "no")),
            "suspende_clases",
        ),
        "affects_attendance": _parse_bool(
            data.get("afecta_asistencia", data.get("affects_attendance", "no")),
            "afecta_asistencia",
        ),
        "description": description,
        "source_page": source_page,
    }


def parse_calendar_csv(content: bytes, academic_year: str) -> list[dict]:
    """Convierte un CSV en filas normalizadas listas para vista previa."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp1252")

    if not text.strip():
        raise ValueError("El archivo CSV está vacío.")

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("El archivo no contiene encabezados.")

    normalized_headers = {}
    for original in reader.fieldnames:
        normalized = _key(original)
        normalized_headers[original] = HEADER_ALIASES.get(normalized, normalized)

    present = set(normalized_headers.values())
    missing = {"titulo", "fecha_inicio"} - present
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(sorted(missing))}.")

    rows = []
    seen = set()
    for row_number, raw_row in enumerate(reader, start=2):
        normalized_raw = {
            normalized_headers[key]: (value or "").strip()
            for key, value in raw_row.items()
            if key is not None
        }
        if not any(normalized_raw.values()):
            continue

        item = {
            "row_number": row_number,
            "raw_data": normalized_raw,
            "is_valid": False,
            "error_message": "",
        }
        try:
            event = validate_event(normalized_raw, academic_year)
            duplicate_key = (
                event["origin"], event["title"].casefold(),
                event["start_date"], event["end_date"],
            )
            if duplicate_key in seen:
                raise ValueError("Evento duplicado dentro del archivo.")
            seen.add(duplicate_key)
            item.update(event)
            item["is_valid"] = True
        except ValueError as exc:
            item["error_message"] = str(exc)
        rows.append(item)

    if not rows:
        raise ValueError("El archivo no contiene eventos.")
    if len(rows) > 1000:
        raise ValueError("El archivo supera el máximo de 1000 eventos.")
    return rows


def build_template_csv(academic_year: str) -> bytes:
    year_start, _ = academic_year_bounds(academic_year)
    start_year = year_start.year
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(TEMPLATE_HEADERS)
    writer.writerow([
        "Inicio del año escolar", f"{start_year}-09-09", f"{start_year}-09-09",
        "Ministerio", "academico", "No", "No",
        "Ejemplo: sustituya estas filas por el calendario correspondiente.", "2",
    ])
    writer.writerow([
        "Reunión general de representantes", f"{start_year}-10-06", f"{start_year}-10-06",
        "Escuela", "reunion", "No", "No",
        "Ejemplo de actividad propia de la institución.", "",
    ])
    return ("\ufeff" + output.getvalue()).encode("utf-8")
