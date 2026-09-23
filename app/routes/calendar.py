"""Calendario anual ministerial e institucional."""

from __future__ import annotations

import calendar as calendar_lib
import hashlib
import io
import uuid
from datetime import date, timedelta
from pathlib import Path

from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template,
    request, send_file, url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.models.school_calendar import SchoolCalendar
from app.utils.calendar_import import (
    CATEGORIES, academic_year_bounds, build_template_csv,
    parse_calendar_csv, validate_event,
)
from app.utils.decorators import role_required
from app.utils.ical import build_ics


calendar_bp = Blueprint("calendar", __name__, url_prefix="/calendar")

MONTH_NAMES = (
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)

SCOPE_LABELS = {
    "both": "Calendario combinado",
    "ministerio": "Calendario escolar oficial",
    "escuela": "Calendario de la escuela",
}


def _parse_iso_date(value, default):
    try:
        return date.fromisoformat(value) if value else default
    except ValueError:
        return default


def _shift_month(value: date, amount: int) -> date:
    month_index = value.year * 12 + value.month - 1 + amount
    year, month_zero = divmod(month_index, 12)
    return date(year, month_zero + 1, 1)


def _visible_calendar(calendar_id=None):
    is_director = current_user.role == "directivo"
    selected = SchoolCalendar.get(calendar_id) if calendar_id else None
    if selected and (is_director or selected["status"] == "published"):
        return selected
    published = SchoolCalendar.get_current_published()
    if published:
        return published
    if is_director:
        calendars = SchoolCalendar.get_all()
        return calendars[0] if calendars else None
    return None


def _calendar_grid(calendar_record, view_name, selected_date, scope):
    year_start, year_end = academic_year_bounds(calendar_record["academic_year"])
    if selected_date < year_start or selected_date > year_end:
        selected_date = year_start

    cal = calendar_lib.Calendar(firstweekday=calendar_lib.MONDAY)
    if view_name == "week":
        range_start = selected_date - timedelta(days=selected_date.weekday())
        range_end = range_start + timedelta(days=6)
        weeks = [[range_start + timedelta(days=offset) for offset in range(7)]]
        months = []
    elif view_name == "year":
        range_start, range_end = year_start, year_end
        weeks = []
        months = []
        cursor = year_start
        for _ in range(12):
            month_weeks = cal.monthdatescalendar(cursor.year, cursor.month)
            months.append({
                "year": cursor.year,
                "month": cursor.month,
                "label": f"{MONTH_NAMES[cursor.month]} {cursor.year}",
                "weeks": month_weeks,
            })
            cursor = _shift_month(cursor, 1)
    else:
        view_name = "month"
        weeks = cal.monthdatescalendar(selected_date.year, selected_date.month)
        range_start, range_end = weeks[0][0], weeks[-1][-1]
        months = []

    events = SchoolCalendar.get_events(
        calendar_record["id"], scope, range_start, range_end
    )
    events_by_day = {}
    cursor = range_start
    while cursor <= range_end:
        events_by_day[cursor] = [
            event for event in events
            if event["start_date"] <= cursor <= event["end_date"]
        ]
        cursor += timedelta(days=1)

    return {
        "view_name": view_name,
        "selected_date": selected_date,
        "range_start": range_start,
        "range_end": range_end,
        "weeks": weeks,
        "months": months,
        "events": events,
        "events_by_day": events_by_day,
        "prev_date": (
            selected_date - timedelta(days=7) if view_name == "week"
            else _shift_month(selected_date, -1) if view_name == "month"
            else year_start
        ),
        "next_date": (
            selected_date + timedelta(days=7) if view_name == "week"
            else _shift_month(selected_date, 1) if view_name == "month"
            else year_end
        ),
    }


@calendar_bp.route("/")
@login_required
def index():
    scope = request.args.get("scope", "both")
    if scope not in SCOPE_LABELS:
        scope = "both"
    view_name = request.args.get("view", "month")
    if view_name not in {"week", "month", "year"}:
        view_name = "month"

    calendar_id = request.args.get("calendar_id", type=int)
    selected_calendar = _visible_calendar(calendar_id)
    calendars = SchoolCalendar.get_all(
        published_only=current_user.role != "directivo"
    )
    grid = None
    if selected_calendar:
        year_start, year_end = academic_year_bounds(selected_calendar["academic_year"])
        default_date = date.today()
        if not year_start <= default_date <= year_end:
            default_date = year_start
        selected_date = _parse_iso_date(request.args.get("date"), default_date)
        grid = _calendar_grid(selected_calendar, view_name, selected_date, scope)

    return render_template(
        "calendar/index.html",
        calendar=selected_calendar,
        calendars=calendars,
        scope=scope,
        scope_labels=SCOPE_LABELS,
        grid=grid,
        month_names=MONTH_NAMES,
    )


@calendar_bp.route("/new", methods=["GET", "POST"])
@role_required("directivo")
def create_calendar():
    if request.method == "POST":
        academic_year = request.form.get("academic_year", "").strip()
        title = request.form.get("title", "").strip()
        try:
            academic_year_bounds(academic_year)
            if not title or len(title) > 150:
                raise ValueError("El título es obligatorio y admite hasta 150 caracteres.")
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("calendar/calendar_form.html")

        source = request.files.get("source_pdf")
        source_data = {}
        source_path = None
        if source and source.filename:
            original_name = secure_filename(source.filename)
            if not original_name.lower().endswith(".pdf"):
                flash("La fuente ministerial debe ser un archivo PDF.", "danger")
                return render_template("calendar/calendar_form.html")
            content = source.read()
            if not content.startswith(b"%PDF-"):
                flash("El archivo no contiene un PDF válido.", "danger")
                return render_template("calendar/calendar_form.html")
            stored_name = f"{uuid.uuid4().hex}.pdf"
            upload_dir = Path(current_app.config["CALENDAR_UPLOAD_FOLDER"])
            upload_dir.mkdir(parents=True, exist_ok=True)
            source_path = upload_dir / stored_name
            source_path.write_bytes(content)
            source_data = {
                "source_original_name": original_name,
                "source_stored_name": stored_name,
                "source_sha256": hashlib.sha256(content).hexdigest(),
            }

        calendar_id = SchoolCalendar.create(
            {"academic_year": academic_year, "title": title, **source_data},
            current_user.id,
        )
        if not calendar_id:
            if source_path and source_path.exists():
                source_path.unlink()
            flash("No fue posible crear el calendario.", "danger")
            return render_template("calendar/calendar_form.html")

        flash("Calendario creado como borrador.", "success")
        return redirect(url_for("calendar.manage", calendar_id=calendar_id))

    return render_template("calendar/calendar_form.html")


@calendar_bp.route("/<int:calendar_id>/manage")
@role_required("directivo")
def manage(calendar_id):
    calendar_record = SchoolCalendar.get(calendar_id)
    if not calendar_record:
        abort(404)
    events = SchoolCalendar.get_events(calendar_id)
    audit = SchoolCalendar.get_audit(calendar_id)
    return render_template(
        "calendar/manage.html", calendar=calendar_record, events=events, audit=audit
    )


@calendar_bp.route("/<int:calendar_id>/source")
@login_required
def source_pdf(calendar_id):
    calendar_record = _visible_calendar(calendar_id)
    if not calendar_record or calendar_record["id"] != calendar_id:
        abort(404)
    stored_name = calendar_record.get("source_stored_name")
    if not stored_name or Path(stored_name).name != stored_name:
        abort(404)
    path = Path(current_app.config["CALENDAR_UPLOAD_FOLDER"]) / stored_name
    if not path.is_file():
        abort(404)
    return send_file(
        path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=calendar_record.get("source_original_name") or "calendario.pdf",
    )


@calendar_bp.route("/<int:calendar_id>/template.csv")
@role_required("directivo")
def template_csv(calendar_id):
    calendar_record = SchoolCalendar.get(calendar_id)
    if not calendar_record:
        abort(404)
    return send_file(
        io.BytesIO(build_template_csv(calendar_record["academic_year"])),
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name=f"plantilla_calendario_{calendar_record['academic_year']}.csv",
    )


@calendar_bp.route("/<int:calendar_id>/import", methods=["POST"])
@role_required("directivo")
def import_csv(calendar_id):
    calendar_record = SchoolCalendar.get(calendar_id)
    if not calendar_record:
        abort(404)
    uploaded = request.files.get("calendar_csv")
    if not uploaded or not uploaded.filename:
        flash("Selecciona un archivo CSV.", "danger")
        return redirect(url_for("calendar.manage", calendar_id=calendar_id))
    original_name = secure_filename(uploaded.filename)
    if not original_name.lower().endswith(".csv"):
        flash("La carga anual debe usar la plantilla CSV.", "danger")
        return redirect(url_for("calendar.manage", calendar_id=calendar_id))
    content = uploaded.read()
    try:
        rows = parse_calendar_csv(content, calendar_record["academic_year"])
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("calendar.manage", calendar_id=calendar_id))

    import_id = SchoolCalendar.create_import(
        calendar_id, original_name, hashlib.sha256(content).hexdigest(), rows,
        current_user.id,
    )
    if not import_id:
        flash("No fue posible preparar la vista previa.", "danger")
        return redirect(url_for("calendar.manage", calendar_id=calendar_id))
    return redirect(url_for("calendar.import_preview", import_id=import_id))


@calendar_bp.route("/imports/<int:import_id>")
@role_required("directivo")
def import_preview(import_id):
    batch, rows = SchoolCalendar.get_import(import_id)
    if not batch:
        abort(404)
    return render_template("calendar/import_preview.html", batch=batch, rows=rows)


@calendar_bp.route("/imports/<int:import_id>/confirm", methods=["POST"])
@role_required("directivo")
def confirm_import(import_id):
    batch, _ = SchoolCalendar.get_import(import_id)
    if not batch:
        abort(404)
    if SchoolCalendar.confirm_import(import_id, current_user.id):
        flash("Los eventos validados fueron incorporados al borrador.", "success")
    else:
        flash("No se puede confirmar una carga con errores o ya procesada.", "danger")
    return redirect(url_for("calendar.manage", calendar_id=batch["calendar_id"]))


def _event_form_data():
    return {
        "titulo": request.form.get("title", ""),
        "fecha_inicio": request.form.get("start_date", ""),
        "fecha_fin": request.form.get("end_date", ""),
        "origen": request.form.get("origin", "escuela"),
        "categoria": request.form.get("category", "actividad"),
        "suspende_clases": "si" if request.form.get("affects_classes") else "no",
        "afecta_asistencia": "si" if request.form.get("affects_attendance") else "no",
        "descripcion": request.form.get("description", ""),
        "pagina_fuente": request.form.get("source_page", ""),
    }


@calendar_bp.route("/<int:calendar_id>/events/new", methods=["GET", "POST"])
@role_required("directivo")
def event_create(calendar_id):
    calendar_record = SchoolCalendar.get(calendar_id)
    if not calendar_record:
        abort(404)
    if request.method == "POST":
        try:
            data = validate_event(_event_form_data(), calendar_record["academic_year"])
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            if SchoolCalendar.create_event(calendar_id, data, current_user.id):
                flash("Evento agregado.", "success")
                return redirect(url_for("calendar.manage", calendar_id=calendar_id))
            flash("No fue posible guardar el evento.", "danger")
    return render_template(
        "calendar/event_form.html", calendar=calendar_record,
        event=None, categories=CATEGORIES,
    )


@calendar_bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@role_required("directivo")
def event_edit(event_id):
    event = SchoolCalendar.get_event(event_id)
    if not event:
        abort(404)
    calendar_record = SchoolCalendar.get(event["calendar_id"])
    if request.method == "POST":
        try:
            data = validate_event(_event_form_data(), calendar_record["academic_year"])
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            if SchoolCalendar.update_event(event_id, data, current_user.id):
                flash("Evento actualizado.", "success")
                return redirect(url_for("calendar.manage", calendar_id=event["calendar_id"]))
            flash("No fue posible actualizar el evento.", "danger")
    return render_template(
        "calendar/event_form.html", calendar=calendar_record,
        event=event, categories=CATEGORIES,
    )


@calendar_bp.route("/events/<int:event_id>/delete", methods=["POST"])
@role_required("directivo")
def event_delete(event_id):
    event = SchoolCalendar.get_event(event_id)
    if not event:
        abort(404)
    if SchoolCalendar.delete_event(event_id, current_user.id):
        flash("Evento retirado del calendario; la acción quedó auditada.", "success")
    else:
        flash("No fue posible retirar el evento.", "danger")
    return redirect(url_for("calendar.manage", calendar_id=event["calendar_id"]))


@calendar_bp.route("/<int:calendar_id>/publish", methods=["POST"])
@role_required("directivo")
def publish(calendar_id):
    if not SchoolCalendar.get(calendar_id):
        abort(404)
    if SchoolCalendar.publish(calendar_id, current_user.id):
        flash("Calendario publicado. Ya está visible en el dashboard.", "success")
    else:
        flash("El calendario debe contener al menos un evento para publicarse.", "danger")
    return redirect(url_for("calendar.manage", calendar_id=calendar_id))


@calendar_bp.route("/<int:calendar_id>/export.ics")
@login_required
def export_ics(calendar_id):
    calendar_record = _visible_calendar(calendar_id)
    if not calendar_record or calendar_record["id"] != calendar_id:
        abort(404)
    scope = request.args.get("scope", "both")
    if scope not in SCOPE_LABELS:
        scope = "both"
    events = SchoolCalendar.get_events(calendar_id, scope)
    name = f"{SCOPE_LABELS[scope]} {calendar_record['academic_year']}"
    content = build_ics(events, name, request.host.split(":", 1)[0])
    filename = f"calendario_{calendar_record['academic_year']}_{scope}.ics"
    return send_file(
        io.BytesIO(content),
        mimetype="text/calendar",
        as_attachment=True,
        download_name=filename,
    )
