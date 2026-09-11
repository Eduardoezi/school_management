from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response
from flask_login import login_required, current_user
from app.models.teacher import Teacher
from app.models.teacher_attendance import TeacherAttendance
from app.utils.decorators import role_required

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

# ---------- PÚBLICO: marcar entrada/salida ----------
@attendance_bp.route('/clock', methods=['GET', 'POST'])
def clock():
    """Página pública: profesor ingresa cédula y marca entrada/salida."""
    if request.method == 'POST':
        cedula = request.form.get('teacher_id', '').strip()
        action = request.form.get('action')
        if not cedula:
            flash('Debe ingresar su cédula.', 'danger')
            return render_template('attendance/clock.html')

        teacher = Teacher.get_by_id(int(cedula)) if cedula.isdigit() else None
        if not teacher:
            flash('Cédula no encontrada. Verifique con el administrador.', 'danger')
            return render_template('attendance/clock.html')

        if action == 'in':
            result = TeacherAttendance.check_in(teacher['id'])
        elif action == 'out':
            result = TeacherAttendance.check_out(teacher['id'])
        else:
            result = {'success': False, 'error': 'Acción no válida.'}

        if result['success']:
            flash(f'✅ {teacher["first_name"]} {teacher["last_name"]}: operación registrada.', 'success')
            record = TeacherAttendance.get_today(teacher['id'])
            return render_template('attendance/clock.html', record=record, teacher=teacher)
        else:
            flash(result['error'], 'danger')

    return render_template('attendance/clock.html')


# ---------- ADMIN: listado del día ----------
@attendance_bp.route('/')
@login_required
@role_required('directivo', 'secretario')
def index():
    attendance_list = TeacherAttendance.get_all_by_date()
    return render_template('attendance/admin_view.html', attendance_list=attendance_list)


# ---------- API para consultar estado actual ----------
@attendance_bp.route('/api/status/<int:teacher_id>')
def api_status(teacher_id):
    record = TeacherAttendance.get_today(teacher_id)
    return jsonify(record or {})


# ---------- REPORTES ----------
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


# ---------- JUSTIFICAR ----------
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


# ---------- EXPORTAR CSV ----------    ⬅️ ESTO ES LO NUEVO, VA AQUÍ AL FINAL
@attendance_bp.route('/report/csv')
@login_required
@role_required('directivo', 'secretario')
def report_csv():
    import csv
    from io import StringIO

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