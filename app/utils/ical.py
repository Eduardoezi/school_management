"""Generación de calendarios compatibles con RFC 5545."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _escape(value) -> str:
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def _fold(line: str) -> list[str]:
    """Pliega líneas por bytes sin cortar caracteres UTF-8."""
    chunks = []
    prefix = ""
    remaining = line
    limit = 75
    while len((prefix + remaining).encode("utf-8")) > limit:
        take = ""
        for char in remaining:
            if len((prefix + take + char).encode("utf-8")) > limit:
                break
            take += char
        chunks.append(prefix + take)
        remaining = remaining[len(take):]
        prefix = " "
    chunks.append(prefix + remaining)
    return chunks


def build_ics(events: list[dict], calendar_name: str, host: str = "school.local") -> bytes:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Sistema de Gestion Escolar//Calendario//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(calendar_name)}",
    ]
    for event in events:
        start = event["start_date"]
        end = event["end_date"] + timedelta(days=1)
        description = event.get("description") or ""
        if event.get("affects_classes"):
            description = f"Suspende clases. {description}".strip()
        if event.get("affects_attendance"):
            description = f"Afecta asistencia. {description}".strip()
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:calendar-event-{event['id']}@{host}",
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
            f"SUMMARY:{_escape(event['title'])}",
            f"DESCRIPTION:{_escape(description)}",
            f"CATEGORIES:{_escape(event.get('category', 'actividad'))}",
            f"X-SCHOOL-ORIGIN:{event.get('origin', 'escuela').upper()}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")

    folded = []
    for line in lines:
        folded.extend(_fold(line))
    return ("\r\n".join(folded) + "\r\n").encode("utf-8")
