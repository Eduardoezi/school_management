from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.models.teacher import Teacher
from app.models.teacher_attendance import TeacherAttendance
from app.models.school_schedule import SchoolSchedule
from app.utils.decorators import role_required
from app.utils import messages as MSG
from app.models.attendance_batch_load import AttendanceBatchLoad
from datetime import date as date_module, datetime as dt_module
from app.utils.db import get_db_connection

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')


# ============================================================
# PÚBLICO: marcar entrada/salida (kiosco)
# ============================================================
@attendance_bp.route('/clock', methods=['GET', 'POST'])
def clock():
    # Horario del día actual (1=Lunes ... 7=Domingo)
    day_today = datetime.now().isoweekday()
    schedule = SchoolSchedule.get_by_day(day_today)

    if request.method == 'POST':
        cedula = request.form.get('teacher_id', '').strip()
        action = request.form.get('action')

        # --- Validación 1: cédula vacía ---
        if not cedula:
            flash(MSG.CEDULA_VACIA, 'danger')
            return render_template('attendance/clock.html', schedule=schedule)

        # --- Validación 2: cédula no numérica ---
        if not cedula.isdigit():
            flash(MSG.CEDULA_INVALIDA, 'danger')
            return render_template('attendance/clock.html', schedule=schedule)

        # --- Validación 3: cédula no registrada como docente ---
        teacher = Teacher.get_by_id(int(cedula))
        if not teacher:
            flash(MSG.CEDULA_NO_ENCONTRADA.format(cedula=cedula), 'danger')
            return render_template('attendance/clock.html', schedule=schedule)

        # --- Registro del día (si ya existe) ---
        record = TeacherAttendance.get_today(teacher['id'])

        # --- Validación 4: acción desconocida ---
        if action not in ('in', 'out'):
            flash('Acción no válida.', 'danger')
            return render_template('attendance/clock.html',
                                   record=record, teacher=teacher, schedule=schedule)

        # --- MARCAR ENTRADA ---
        if action == 'in':
            if record and record.get('check_in'):
                flash(MSG.ENTRADA_YA_REGISTRADA.format(hora=record['check_in']), 'warning')
                return render_template('attendance/clock.html',
                                       record=record, teacher=teacher, schedule=schedule)

            result = TeacherAttendance.check_in(teacher['id'])

        # --- MARCAR SALIDA ---
        else:  # action == 'out'
            if not record or not record.get('check_in'):
                flash(MSG.SALIDA_SIN_ENTRADA, 'danger')
                return render_template('attendance/clock.html',
                                       teacher=teacher, schedule=schedule)

            if record.get('check_out'):
                flash(MSG.SALIDA_YA_REGISTRADA.format(hora=record['check_out']), 'warning')
                return render_template('attendance/clock.html',
                                       record=record, teacher=teacher, schedule=schedule)

            result = TeacherAttendance.check_out(teacher['id'])

        # --- Resultado ---
        if result.get('success'):
            flash(f'✅ {teacher["first_name"]} {teacher["last_name"]}: operación registrada.', 'success')
            record = TeacherAttendance.get_today(teacher['id'])
            return render_template('attendance/clock.html',
                                   record=record, teacher=teacher, schedule=schedule)

        flash(result.get('error', 'Error desconocido.'), 'danger')
        return render_template('attendance/clock.html',
                               record=record, teacher=teacher, schedule=schedule)

    # GET
    return render_template('attendance/clock.html', schedule=schedule)


# ============================================================
# API AJAX: buscar docente por cédula (para previsualización)
# ============================================================
@attendance_bp.route('/api/teacher/<cedula>')
def api_teacher(cedula):
    if not cedula.isdigit():
        return jsonify({'found': False})
    teacher = Teacher.get_by_id(int(cedula))
    if teacher:
        return jsonify({
            'found': True,
            'id': teacher['id'],
            'first_name': teacher['first_name'],
            'last_name': teacher['last_name']
        })
    return jsonify({'found': False})


# ============================================================
# ADMIN: listado del día
# ============================================================
@attendance_bp.route('/')
@login_required
@role_required('directivo', 'secretario')
def index():
    attendance_list = TeacherAttendance.get_all_by_date()
    return render_template('attendance/admin_view.html', attendance_list=attendance_list)


# ============================================================
# API para consultar estado actual
# ============================================================
@attendance_bp.route('/api/status/<int:teacher_id>')
def api_status(teacher_id):
    record = TeacherAttendance.get_today(teacher_id)
    return jsonify(record or {})


# ============================================================
# REPORTES
# ============================================================
@attendance_bp.route('/report', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def report():
    teachers = Teacher.get_all()
    records = []
    summary = []
    filters = {}

    if request.method == 'POST':
        filters = {
            'from_date': request.form.get('from_date'),
            'to_date': request.form.get('to_date'),
            'teacher_ids': [int(x) for x in request.form.getlist('teacher_ids') if x],
            'status': request.form.get('status') or None,
            'days_of_week': [int(x) for x in request.form.getlist('days_of_week') if x]
        }
        if filters['from_date'] and filters['to_date']:
            records = TeacherAttendance.get_report(filters)
            summary = TeacherAttendance.get_summary_by_teacher(filters)

    return render_template('attendance/report.html',
                           teachers=teachers,
                           records=records,
                           summary=summary,
                           filters=filters)


# ============================================================
# JUSTIFICAR
# ============================================================
@attendance_bp.route('/<int:attendance_id>/justify', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def justify_view(attendance_id):
    record = TeacherAttendance.get_by_id(attendance_id)
    if not record:
        flash('Registro no encontrado.', 'danger')
        return redirect(url_for('attendance.report'))

    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        if not reason:
            flash('Debe indicar el motivo de la justificación.', 'danger')
        elif TeacherAttendance.justify(attendance_id, current_user.id, reason):
            flash('Asistencia justificada correctamente.', 'success')
            return redirect(url_for('attendance.report'))
        else:
            flash('Error al justificar.', 'danger')

    return render_template('attendance/justify.html', record=record)


# ============================================================
# EXPORTAR CSV
# ============================================================
@attendance_bp.route('/report/csv')
@login_required
@role_required('directivo', 'secretario')
def report_csv():
    import csv
    from io import StringIO
    from flask import Response

    filters = {
        'from_date': request.args.get('from_date'),
        'to_date': request.args.get('to_date'),
        'teacher_ids': [int(x) for x in request.args.getlist('teacher_ids') if x],
        'status': request.args.get('status') or None,
        'days_of_week': [int(x) for x in request.args.getlist('days_of_week') if x]
    }
    records = TeacherAttendance.get_report(filters)

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Cédula', 'Docente', 'Fecha', 'Entrada', 'Salida', 'Estado', 'Observaciones'])
    for r in records:
        writer.writerow([r['teacher_id'], f"{r['first_name']} {r['last_name']}",
                         r['attendance_date'], r['check_in'] or '', r['check_out'] or '',
                         r['status'], r['remarks'] or ''])

    return Response(si.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=reporte_asistencia.csv'})

# ============================================================
# CARGA MANUAL DE ASISTENCIA (directivo / secretario)
# ============================================================


@attendance_bp.route('/manual-load', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def manual_load():
    today = date_module.today()
    today_str = today.strftime('%Y-%m-%d')

    # Fecha seleccionada (GET: puede venir de query, POST: del form)
    selected_date = request.args.get('date') or request.form.get('attendance_date')

# Validación 1: no futuras, no hoy, no más de 30 días
    if selected_date:
        if selected_date > today_str:
            flash('No puedes cargar asistencia de fechas futuras.', 'danger')
            return redirect(url_for('attendance.manual_load'))
        if selected_date == today_str:
            flash('Para la asistencia de hoy usa el kiosco. Solo puedes cargar fechas pasadas.', 'warning')
            return redirect(url_for('attendance.manual_load'))

        # Calcular días transcurridos
        try:
            d_sel = dt_module.strptime(selected_date, '%Y-%m-%d').date()
            days_ago = (today - d_sel).days
        except Exception:
            days_ago = 0

        # Bloquear mayor a 30 días
        if days_ago > 30:
            flash(
                f'No se puede cargar asistencia con más de 30 días de antigüedad. '
                f'La fecha seleccionada tiene {days_ago} días. '
                f'Contacta al administrador del sistema para casos excepcionales.',
                'danger'
            )
            return redirect(url_for('attendance.manual_load'))

    # GET sin fecha: mostrar formulario para elegirla
    if request.method == 'GET' and not selected_date:
        return render_template('attendance/manual_load_pick_date.html',
                               today=today_str)

    # POST: procesar la carga
    if request.method == 'POST':
        reason = (request.form.get('reason') or '').strip()
        if not reason:
            flash('Debes indicar la razón por la cual cargas la asistencia manualmente.', 'danger')
            return redirect(url_for('attendance.manual_load', date=selected_date))

        # Verificar que no exista un lote previo para esta fecha
        existing_batch = AttendanceBatchLoad.get_by_attendance_date(selected_date)
        if existing_batch and request.form.get('confirm_overwrite') != 'yes':
            flash(
                f'Ya existe una carga manual para el {selected_date} '
                f'(lote {existing_batch["batch_number"]}). Marca la casilla '
                f'para confirmar que quieres sobrescribir los registros cargados manualmente.',
                'warning'
            )
            return redirect(url_for('attendance.manual_load', date=selected_date))

        # Recolectar los registros del formulario
        teachers = Teacher.get_all()
        source = 'manual_director' if current_user.role == 'directivo' else 'manual_secretary'
        records_to_save = []

        for t in teachers:
            tid = t['id']
            # Solo procesamos si el checkbox "incluir" está marcado
            if request.form.get(f'include_{tid}') != 'on':
                continue

            status = request.form.get(f'status_{tid}') or 'present'
            check_in = request.form.get(f'check_in_{tid}') or None
            check_out = request.form.get(f'check_out_{tid}') or None
            remarks = request.form.get(f'remarks_{tid}') or None

            # Validaciones
            if status in ('absent', 'justified'):
                # No requiere check_in
                pass
            elif status == 'present' or status == 'late':
                if not check_in:
                    flash(f'Falta la hora de entrada para {t["first_name"]} {t["last_name"]}.', 'danger')
                    return redirect(url_for('attendance.manual_load', date=selected_date))

            if check_out and check_in and check_out < check_in:
                flash(f'La salida no puede ser antes de la entrada para {t["first_name"]} {t["last_name"]}.', 'danger')
                return redirect(url_for('attendance.manual_load', date=selected_date))

            records_to_save.append({
                'teacher_id': tid,
                'status': status,
                'check_in': check_in,
                'check_out': check_out,
                'remarks': remarks
            })

        if not records_to_save:
            flash('No marcaste ningún docente para incluir en la carga.', 'warning')
            return redirect(url_for('attendance.manual_load', date=selected_date))

        # Crear el lote (marcando si es tardío)
        batch = AttendanceBatchLoad.create_v2(
            attendance_date=selected_date,
            reason=reason,
            loaded_by=current_user.id,
            teachers_count=len(records_to_save),
            days_after_event=days_ago
        )
        if not batch:
            flash('Error al crear el lote de carga manual.', 'danger')
            return redirect(url_for('attendance.manual_load', date=selected_date))

        # Guardar cada registro
        saved = 0
        for rec in records_to_save:
            ok = TeacherAttendance.save_manual(
                rec['teacher_id'], selected_date,
                rec, batch['id'], source=source
            )
            if ok:
                saved += 1

        flash(
            f'Lote {batch["batch_number"]} creado. '
            f'{saved} registros cargados para el {selected_date}.',
            'success'
        )
        return redirect(url_for('attendance.manual_load_detail', batch_id=batch['id']))

    # GET con fecha: mostrar el formulario de carga
    teachers_list = TeacherAttendance.get_all_teachers_for_date(selected_date)
    existing_batch = AttendanceBatchLoad.get_by_attendance_date(selected_date)

    # Días de antigüedad
    try:
        d_sel = dt_module.strptime(selected_date, '%Y-%m-%d').date()
        days_ago = (today - d_sel).days
    except Exception:
        days_ago = 0

    return render_template('attendance/manual_load.html',
                           selected_date=selected_date,
                           teachers_list=teachers_list,
                           existing_batch=existing_batch,
                           days_ago=days_ago,
                           today=today_str)


@attendance_bp.route('/manual-load/detail/<int:batch_id>')
@login_required
@role_required('directivo', 'secretario')
def manual_load_detail(batch_id):
    batch = AttendanceBatchLoad.get_by_id(batch_id)
    if not batch:
        flash('Lote no encontrado.', 'danger')
        return redirect(url_for('attendance.manual_load'))

    # Registros del lote
    conn = get_db_connection()
    records = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ta.*, t.first_name, t.last_name
            FROM teacher_attendance ta
            JOIN teachers t ON ta.teacher_id = t.id
            WHERE ta.batch_id = %s
            ORDER BY t.last_name, t.first_name
        """, (batch_id,))
        records = cursor.fetchall()
        cursor.close()
        conn.close()

    return render_template('attendance/manual_load_detail.html',
                           batch=batch,
                           records=records)


@attendance_bp.route('/manual-load/history')
@login_required
@role_required('directivo', 'secretario')
def manual_load_history():
    batches = AttendanceBatchLoad.get_all(limit=200)
    return render_template('attendance/manual_load_history.html',
                           batches=batches)

# ============================================================
# EDITAR JUSTIFICACIÓN DEL LOTE
# ============================================================
@attendance_bp.route('/manual-load/<int:batch_id>/edit-reason', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def manual_load_edit_reason(batch_id):
    batch = AttendanceBatchLoad.get_by_id(batch_id)
    if not batch:
        flash('Lote no encontrado.', 'danger')
        return redirect(url_for('attendance.manual_load_history'))

    if request.method == 'POST':
        new_reason = (request.form.get('reason') or '').strip()
        if not new_reason:
            flash('La razón no puede estar vacía.', 'danger')
            return redirect(url_for('attendance.manual_load_edit_reason', batch_id=batch_id))

        if AttendanceBatchLoad.update_reason(batch_id, new_reason, current_user.id):
            flash('Justificación del lote actualizada.', 'success')
            return redirect(url_for('attendance.manual_load_detail', batch_id=batch_id))
        flash('Error al actualizar la justificación.', 'danger')

    return render_template('attendance/manual_load_edit_reason.html', batch=batch)


# ============================================================
# EDITAR OBSERVACIÓN INDIVIDUAL DE UN DOCENTE
# ============================================================
@attendance_bp.route('/manual-load/record/<int:attendance_id>/edit-remarks', methods=['POST'])
@login_required
@role_required('directivo', 'secretario')
def manual_load_edit_remarks(attendance_id):
    new_remarks = (request.form.get('remarks') or '').strip()
    batch_id = request.form.get('batch_id')

    if AttendanceBatchLoad.update_teacher_remarks(attendance_id, new_remarks or None):
        flash('Observación actualizada.', 'success')
    else:
        flash('Error al actualizar la observación.', 'danger')

    if batch_id:
        return redirect(url_for('attendance.manual_load_detail', batch_id=batch_id))
    return redirect(url_for('attendance.manual_load_history'))