from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import date
from app.models.daily_attendance_stat import DailyAttendanceStat
from app.models.enrollment import Enrollment
from app.models.teacher import Teacher
from app.models.course import Course
from app.utils.decorators import role_required

daily_stats_bp = Blueprint('daily_stats', __name__, url_prefix='/daily-stats')


# ============================================================
# MAESTRO: reportar el curso asignado
# ============================================================
@daily_stats_bp.route('/', methods=['GET', 'POST'])
@login_required
def my_report():
    teacher = Teacher.get_by_user_id(current_user.id)

    if current_user.role == 'maestro' and not teacher:
        flash('Tu usuario no está vinculado a un docente. Contacta al directivo.', 'danger')
        return redirect(url_for('main.dashboard'))

    courses = []
    if teacher:
        conn_courses = Course.get_all()
        courses = [c for c in conn_courses if c.get('teacher_id') == teacher['id']]

    today_str = date.today().strftime('%Y-%m-%d')
    selected_date = request.args.get('date') or today_str

    if selected_date > today_str:
        flash('No puedes seleccionar una fecha futura.', 'warning')
        return redirect(url_for('daily_stats.my_report'))

    matricula = {'total': 0, 'girls': 0, 'boys': 0, 'unknown': 0}
    if courses:
        matricula = Enrollment.get_matricula(courses[0]['code'], selected_date)

    if request.method == 'POST':
        stat_date = request.form.get('stat_date', '')
        if stat_date > today_str:
            flash('No puedes guardar reportes de fechas futuras.', 'danger')
            return redirect(url_for('daily_stats.my_report'))

        course_code = request.form['course_code']
        data = {
            'girls_present': int(request.form.get('girls_present', 0) or 0),
            'boys_present':  int(request.form.get('boys_present', 0) or 0),
            'girls_absent':  int(request.form.get('girls_absent', 0) or 0),
            'boys_absent':   int(request.form.get('boys_absent', 0) or 0),
            'notes':         request.form.get('notes')
        }
        if DailyAttendanceStat.get_or_create(course_code, stat_date,
                                             teacher['id'], data):
            flash('Reporte de asistencia guardado.', 'success')
            return redirect(url_for('daily_stats.my_report', date=stat_date))
        flash('Error al guardar.', 'danger')

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
                           my_stats=my_stats,
                           matricula=matricula,
                           today=today_str)


# ============================================================
# DIRECTIVO / SECRETARIO: ver reporte del día
# ============================================================
@daily_stats_bp.route('/admin')
@login_required
@role_required('directivo', 'secretario')
def admin_view():
    selected_date = request.args.get('date') or date.today().strftime('%Y-%m-%d')
    stats = DailyAttendanceStat.get_all_by_date(selected_date)
    summary = DailyAttendanceStat.get_summary_by_date(selected_date)

    # Lista de TODOS los cursos para ofrecer "cargar" los que no tengan reporte
    all_courses = Course.get_all()
    reported_codes = {s['course_code'] for s in stats}
    missing_courses = [c for c in all_courses if c['code'] not in reported_codes]

    return render_template('daily_stats/admin_view.html',
                           stats=stats,
                           summary=summary,
                           selected_date=selected_date,
                           missing_courses=missing_courses,
                           all_courses=all_courses)


# ============================================================
# DIRECTIVO / SECRETARIO: cargar o editar reporte de un curso
# ============================================================
@daily_stats_bp.route('/admin/report', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def admin_report():
    today_str = date.today().strftime('%Y-%m-%d')

    # Parámetros desde la URL: ?course=PE-0202&date=2026-09-15
    course_code = request.args.get('course') or request.form.get('course_code')
    stat_date = request.args.get('date') or request.form.get('stat_date') or today_str

    if stat_date > today_str:
        flash('No puedes trabajar con fechas futuras.', 'warning')
        return redirect(url_for('daily_stats.admin_view'))

    course = Course.get_by_code(course_code)
    if not course:
        flash('Curso no encontrado.', 'danger')
        return redirect(url_for('daily_stats.admin_view', date=stat_date))

    matricula = Enrollment.get_matricula(course_code, stat_date)
    existing = DailyAttendanceStat.get_by_course_and_date(course_code, stat_date)

    if request.method == 'POST':
        if stat_date > today_str:
            flash('No puedes guardar reportes de fechas futuras.', 'danger')
            return redirect(url_for('daily_stats.admin_view'))

        # El directivo usa su propio user_id cuando no hay docente vinculado
        teacher = Teacher.get_by_user_id(current_user.id)
        teacher_id = teacher['id'] if teacher else course.get('teacher_id')
        if not teacher_id:
            # Fallback: usar el primer docente para no romper la FK
            all_teachers = Teacher.get_all()
            if not all_teachers:
                flash('No hay docentes registrados para asociar el reporte.', 'danger')
                return redirect(url_for('daily_stats.admin_view', date=stat_date))
            teacher_id = all_teachers[0]['id']

        data = {
            'girls_present': int(request.form.get('girls_present', 0) or 0),
            'boys_present':  int(request.form.get('boys_present', 0) or 0),
            'girls_absent':  int(request.form.get('girls_absent', 0) or 0),
            'boys_absent':   int(request.form.get('boys_absent', 0) or 0),
            'notes':         request.form.get('notes')
        }
        if DailyAttendanceStat.get_or_create(course_code, stat_date, teacher_id, data):
            flash(f'Reporte de {course["name"]} guardado correctamente.', 'success')
            return redirect(url_for('daily_stats.admin_view', date=stat_date))
        flash('Error al guardar.', 'danger')

    return render_template('daily_stats/admin_report.html',
                           course=course,
                           matricula=matricula,
                           existing=existing,
                           selected_date=stat_date,
                           today=today_str)


# ============================================================
# HISTÓRICO
# ============================================================
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