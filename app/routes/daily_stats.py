from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import date
from app.models.daily_attendance_stat import DailyAttendanceStat
from app.models.teacher import Teacher
from app.models.course import Course
from app.utils.decorators import role_required

daily_stats_bp = Blueprint('daily_stats', __name__, url_prefix='/daily-stats')


# ---------- MAESTRO: reportar el curso asignado ----------
@daily_stats_bp.route('/', methods=['GET', 'POST'])
@login_required
def my_report():
    # Solo docentes pueden reportar (directivo/secretario también pueden ver, pero no reportar)
    teacher = Teacher.get_by_user_id(current_user.id)

    if current_user.role == 'maestro' and not teacher:
        flash('Tu usuario no está vinculado a un docente. Contacta al directivo.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Buscar el curso asignado al docente (por teacher_id en courses)
    courses = []
    if teacher:
        conn_courses = Course.get_all()
        courses = [c for c in conn_courses if c.get('teacher_id') == teacher['id']]

    selected_date = request.args.get('date') or date.today().strftime('%Y-%m-%d')

    if request.method == 'POST':
        course_code = request.form['course_code']
        data = {
            'girls_present': int(request.form.get('girls_present', 0) or 0),
            'boys_present':  int(request.form.get('boys_present', 0) or 0),
            'girls_absent':  int(request.form.get('girls_absent', 0) or 0),
            'boys_absent':   int(request.form.get('boys_absent', 0) or 0),
            'notes':         request.form.get('notes')
        }
        if DailyAttendanceStat.get_or_create(course_code, request.form['stat_date'],
                                             teacher['id'], data):
            flash('Reporte de asistencia guardado.', 'success')
            return redirect(url_for('daily_stats.my_report', date=request.form['stat_date']))
        flash('Error al guardar.', 'danger')

    # Cargar reportes ya hechos por el docente en esa fecha
    my_stats = []
    if teacher:
        for c in courses:
            stat = DailyAttendanceStat.get_by_course_and_date(c['code'], selected_date)
            if stat:
                my_stats.append(stat)

    return render_template('daily_stats/my_report.html',
                           teacher=teacher,
                           courses=courses,
                           selected_date=selected_date,
                           my_stats=my_stats)


# ---------- DIRECTIVO / SECRETARIO: ver reporte del día ----------
@daily_stats_bp.route('/admin')
@login_required
@role_required('directivo', 'secretario')
def admin_view():
    selected_date = request.args.get('date') or date.today().strftime('%Y-%m-%d')
    stats = DailyAttendanceStat.get_all_by_date(selected_date)
    summary = DailyAttendanceStat.get_summary_by_date(selected_date)
    return render_template('daily_stats/admin_view.html',
                           stats=stats,
                           summary=summary,
                           selected_date=selected_date)


# ---------- HISTÓRICO ----------
@daily_stats_bp.route('/history')
@login_required
@role_required('directivo', 'secretario')
def history():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    course_code = request.args.get('course_code') or None
    records = []
    if from_date and to_date:
        records = DailyAttendanceStat.get_history(from_date, to_date, course_code)
    courses = Course.get_all()
    return render_template('daily_stats/history.html',
                           records=records,
                           courses=courses,
                           from_date=from_date,
                           to_date=to_date,
                           course_code=course_code)