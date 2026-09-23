"""
Utilidades para importar y validar el calendario escolar desde CSV.

Formato esperado del CSV (con cabecera, separador coma):

    origen,titulo,fecha_inicio,fecha_fin,categoria,descripcion,afecta_clases,afecta_asistencia,pagina_fuente
    ministerio,Inicio de clases,2026-09-15,2026-09-15,actividad,Primer día,si,no,1
    escuela,Reunión de padres,2026-10-05,2026-10-05,reunion,,no,no,

Los valores de `origen` solo pueden ser `ministerio` o `escuela`.
Los valores de `afecta_clases` y `afecta_asistencia` son `si`/`no` (o vacío = no).
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any


# ============================================================
# Constantes
# ============================================================
CATEGORIES = (
    
    'evaluacion',
    'reunion',
    'feriado',
    'asueto',
    'receso',
    'actividad',
    'efeméride',
    'celebracion',
    'otro',
)

ORIGINS = ('ministerio', 'escuela')

MAX_TITLE_LEN = 200
MAX_DESCRIPTION_LEN = 4000
MAX_SOURCE_PAGE = 999


# ============================================================
# Helpers de fechas
# ============================================================
def academic_year_bounds(academic_year: str) -> tuple[date, date]:
    """
    Devuelve (inicio, fin) del año escolar.

    Formato esperado: 'AAAA-AAAA'. Por convención:
        - Inicio: 1 de septiembre del primer año.
        - Fin:    31 de agosto del segundo año.
    """
    if not academic_year or len(academic_year) != 9 or academic_year[4] != '-':
        raise ValueError('El año escolar debe tener el formato AAAA-AAAA (ej: 2026-2027).')

    try:
        first_year = int(academic_year[:4])
        second_year = int(academic_year[5:])
    except ValueError as exc:
        raise ValueError('El año escolar debe contener números válidos.') from exc

    if second_year != first_year + 1:
        raise ValueError('Los años del período escolar deben ser consecutivos.')

    return date(first_year, 9, 1), date(second_year, 8, 31)


def _parse_date(value: str, field_name: str) -> date:
    """Convierte un string ISO a `date`. Acepta varios formatos comunes."""
    if not value:
        raise ValueError(f'{field_name} es obligatoria.')

    value = value.strip()

    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    raise ValueError(f'{field_name} no tiene un formato de fecha válido.')


def _parse_bool(value: str) -> bool:
    """'si', 'sí', 's', '1', 'true', 'yes' → True. Cualquier otra cosa → False."""
    if not value:
        return False
    return value.strip().lower() in ('si', 'sí', 's', '1', 'true', 'yes', 'on')


# ============================================================
# Validación individual
# ============================================================
def validate_event(raw: dict[str, Any], academic_year: str) -> dict[str, Any]:
    """
    Valida un único evento desde el formulario del director.

    Args:
        raw: dict con las claves tal como vienen del request form.
        academic_year: año escolar del calendario al que pertenece.

    Returns:
        dict con los campos validados y normalizados:
            origin, title, start_date, end_date, category,
            description, affects_classes, affects_attendance, source_page

    Raises:
        ValueError si algún campo es inválido.
    """
    origin = (raw.get('origen') or 'escuela').strip().lower()
    if origin not in ORIGINS:
        raise ValueError('El origen debe ser "ministerio" o "escuela".')

    title = (raw.get('titulo') or '').strip()
    if not title:
        raise ValueError('El título es obligatorio.')
    if len(title) > MAX_TITLE_LEN:
        raise ValueError(f'El título no puede superar {MAX_TITLE_LEN} caracteres.')

    start = _parse_date(raw.get('fecha_inicio', ''), 'La fecha de inicio')
    end = _parse_date(raw.get('fecha_fin', ''), 'La fecha de fin')

    if end < start:
        raise ValueError('La fecha de fin no puede ser anterior a la de inicio.')

    year_start, year_end = academic_year_bounds(academic_year)
    if start < year_start or start > year_end:
        raise ValueError('La fecha de inicio debe estar dentro del año escolar.')
    if end < year_start or end > year_end:
        raise ValueError('La fecha de fin debe estar dentro del año escolar.')

    category = (raw.get('categoria') or 'actividad').strip().lower()
    if category not in CATEGORIES:
        raise ValueError(f'La categoría debe ser una de: {", ".join(CATEGORIES)}.')

    description = (raw.get('descripcion') or '').strip() or None
    if description and len(description) > MAX_DESCRIPTION_LEN:
        raise ValueError(f'La descripción no puede superar {MAX_DESCRIPTION_LEN} caracteres.')

    source_page_raw = raw.get('pagina_fuente')
    source_page = None
    if source_page_raw not in (None, '', '0'):
        try:
            source_page = int(source_page_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError('La página de la fuente debe ser un número entero.') from exc
        if source_page < 1 or source_page > MAX_SOURCE_PAGE:
            raise ValueError(f'La página debe estar entre 1 y {MAX_SOURCE_PAGE}.')

    return {
        'origin':             origin,
        'title':              title,
        'start_date':         start,
        'end_date':           end,
        'category':           category,
        'description':        description,
        'affects_classes':    _parse_bool(raw.get('suspende_clases', '')),
        'affects_attendance': _parse_bool(raw.get('afecta_asistencia', '')),
        'source_page':        source_page,
    }


# ============================================================
# Plantilla CSV para descargar
# ============================================================
TEMPLATE_HEADERS = [
    'origen',
    'titulo',
    'fecha_inicio',
    'fecha_fin',
    'categoria',
    'descripcion',
    'afecta_clases',
    'afecta_asistencia',
    'pagina_fuente',
]


def build_template_csv(academic_year: str) -> bytes:
    """
    Genera un CSV de ejemplo con la cabecera y una fila modelo.
    Listo para que el director lo descargue, lo complete y lo reimporte.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(TEMPLATE_HEADERS)

    year_start, _ = academic_year_bounds(academic_year)
    ejemplo_fecha = year_start.replace(day=15)

    writer.writerow([
        'ministerio',
        'Inicio del año escolar',
        ejemplo_fecha.isoformat(),
        ejemplo_fecha.isoformat(),
        'actividad',
        'Primer día de clases del año escolar',
        'no',
        'no',
        '1',
    ])
    writer.writerow([
        'escuela',
        'Reunión de representantes',
        ejemplo_fecha.isoformat(),
        ejemplo_fecha.isoformat(),
        'reunion',
        'Primera reunión del año con representantes',
        'no',
        'no',
        '',
    ])

    return output.getvalue().encode('utf-8-sig')  # BOM para Excel


# ============================================================
# Parser del CSV completo
# ============================================================
def parse_calendar_csv(content: bytes, academic_year: str) -> list[dict[str, Any]]:
    """
    Parsea el CSV completo y devuelve una lista de dicts, uno por fila.

    Cada dict contiene:
        row_number     → número de fila en el CSV (para reportes)
        raw_data       → dict con los valores crudos
        origin, title, start_date, end_date, category, description,
        affects_classes, affects_attendance, source_page
        is_valid       → bool
        error_message  → str | None

    Si el CSV está completamente vacío o mal formado, lanza ValueError.
    Las filas individuales con problemas se marcan `is_valid=False`
    sin detener el proceso.
    """
    if not content:
        raise ValueError('El archivo está vacío.')

    # Intentar decodificar quitando BOM si existe
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            text = content.decode('latin-1')
        except UnicodeDecodeError as exc:
            raise ValueError('No se pudo leer el archivo. Debe ser texto UTF-8 o Latin-1.') from exc

    reader = csv.DictReader(io.StringIO(text))

    # Normalizar las cabeceras: minúsculas, sin espacios, sin BOM
    if reader.fieldnames is None:
        raise ValueError('El CSV no tiene cabecera.')

    reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

    missing = set(TEMPLATE_HEADERS) - set(reader.fieldnames)
    if missing:
        raise ValueError(
            f'Al CSV le faltan columnas obligatorias: {", ".join(sorted(missing))}.'
        )

    rows: list[dict[str, Any]] = []

    for index, raw_row in enumerate(reader, start=2):  # fila 2 en adelante (fila 1 = cabecera)
        # Saltar filas totalmente vacías
        if not any((v or '').strip() for v in raw_row.values()):
            continue

        row: dict[str, Any] = {
            'row_number': index,
            'raw_data': dict(raw_row),
            'origin': None,
            'title': None,
            'start_date': None,
            'end_date': None,
            'category': None,
            'description': None,
            'affects_classes': False,
            'affects_attendance': False,
            'source_page': None,
            'is_valid': False,
            'error_message': None,
        }

        try:
            # Normalizar: acepta los nombres exactos de la plantilla
            normalized = {
                'origen':             raw_row.get('origen', ''),
                'titulo':             raw_row.get('titulo', ''),
                'fecha_inicio':       raw_row.get('fecha_inicio', ''),
                'fecha_fin':          raw_row.get('fecha_fin', ''),
                'categoria':          raw_row.get('categoria', 'actividad'),
                'descripcion':        raw_row.get('descripcion', ''),
                'suspende_clases':    raw_row.get('afecta_clases', ''),
                'afecta_asistencia':  raw_row.get('afecta_asistencia', ''),
                'pagina_fuente':      raw_row.get('pagina_fuente', ''),
            }
            validated = validate_event(normalized, academic_year)

            row.update(validated)
            row['is_valid'] = True

        except ValueError as exc:
            row['error_message'] = str(exc)

        rows.append(row)

    if not rows:
        raise ValueError('El CSV no contiene filas con datos.')

    return rows