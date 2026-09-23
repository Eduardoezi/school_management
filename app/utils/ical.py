"""
Generador de archivos .ics (iCalendar) para exportar el calendario.

Sigue el RFC 5545 en su forma más simple: eventos de día completo
(VALUE=DATE), sin recurrencia, sin alarmas. Compatible con Google
Calendar, Apple Calendar, Outlook y Thunderbird.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Iterable


def _escape(text: str) -> str:
    """Escapa caracteres especiales según RFC 5545."""
    if not text:
        return ''
    return (
        text.replace('\\', '\\\\')
            .replace(';', '\\;')
            .replace(',', '\\,')
            .replace('\n', '\\n')
            .replace('\r', '')
    )


def _format_date(value: date) -> str:
    """Convierte date a YYYYMMDD (formato iCalendar para días completos)."""
    return value.strftime('%Y%m%d')


def _fold_line(line: str, limit: int = 75) -> str:
    """
    Aplica el plegado (folding) del RFC 5545:
    las líneas mayores a 75 octetos se parten con CRLF + espacio.
    """
    encoded = line.encode('utf-8')
    if len(encoded) <= limit:
        return line

    parts = []
    current = b''
    for byte in encoded:
        current += bytes([byte])
        if len(current) >= limit:
            parts.append(current)
            current = b''
    if current:
        parts.append(current)

    result = parts[0].decode('utf-8', errors='ignore')
    for part in parts[1:]:
        result += '\r\n ' + part.decode('utf-8', errors='ignore')
    return result


def build_ics(events: Iterable[dict], calendar_name: str, host: str) -> bytes:
    """
    Construye el contenido de un archivo .ics.

    Args:
        events: iterable de dicts con:
            id, title, start_date, end_date, description, origin, category
        calendar_name: nombre visible del calendario (ej: "Calendario 2026-2027").
        host: dominio usado para generar UIDs estables.

    Returns:
        bytes del archivo .ics.
    """
    host = host or 'localhost'
    lines: list[str] = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//School Management//Calendario Escolar//ES',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{_escape(calendar_name)}',
        f'X-WR-TIMEZONE:America/Caracas',
    ]

    for event in events:
        uid = f"event-{event.get('id', uuid.uuid4().hex)}@{host}"

        title = event.get('title') or 'Sin título'
        start = event.get('start_date')
        end = event.get('end_date') or start

        # iCalendar exige DTEND exclusivo: si es día completo,
        # el DTEND debe ser el día siguiente al último día del evento.
        from datetime import timedelta
        end_exclusive = end + timedelta(days=1) if isinstance(end, date) else end

        description_parts = []
        if event.get('origin'):
            description_parts.append(f"Origen: {event['origin'].capitalize()}")
        if event.get('category'):
            description_parts.append(f"Categoría: {event['category'].capitalize()}")
        if event.get('description'):
            description_parts.append(event['description'])
        description = '\n'.join(description_parts)

        event_lines = [
            'BEGIN:VEVENT',
            f'UID:{uid}',
            f'DTSTAMP:{_format_date(date.today())}T000000Z',
            f'DTSTART;VALUE=DATE:{_format_date(start)}',
            f'DTEND;VALUE=DATE:{_format_date(end_exclusive)}',
            f'SUMMARY:{_escape(title)}',
        ]

        if description:
            event_lines.append(f'DESCRIPTION:{_escape(description)}')

        if event.get('origin'):
            event_lines.append(f'CATEGORIES:{_escape(event["origin"].capitalize())}')

        event_lines.append('END:VEVENT')

        for line in event_lines:
            lines.append(_fold_line(line))

    lines.append('END:VCALENDAR')

    return ('\r\n'.join(lines) + '\r\n').encode('utf-8')