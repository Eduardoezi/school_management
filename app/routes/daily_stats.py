"""
Rutas del módulo de estadística diaria.

Aplican autorización RBAC+ABAC (SEG-006):
- Un maestro solo puede reportar asistencia de SUS cursos.
- Un especialista puede reportar de cualquier curso (ve toda la matrícula).
- Directivo/Secretario tienen acceso total.

El `course_code` del formulario se valida contra el usuario actual
antes de cualquier operación de lectura o escritura.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import date

from app.models.daily_attendance_stat import DailyAttendanceStat
from app.models.enrollment import Enrollment
from app.models.teacher import Teacher
from app.models.course import Course
from app.utils.decorators import role_required

# 🔒 SEG-006: autorización por curso
from app.security import Permission
from app.security.helpers import get_course_or_403

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

    # ---------- Cálculo de matrícula (solo si ya hay curso) ----------
    matricula = {'total': 0, 'girls': 0, 'boys': 0, 'unknown': 0}
    if courses:
        matricula = Enrollment.get_matricula(courses[0]['code'], selected_date)

    # ---------- POST ----------
    if request.method == 'POST':
        stat_date = request.form.get('stat_date', '')
        if stat_date > today_str:
            flash('No puedes guardar reportes de fechas futuras.', 'danger')
            return redirect(url_for('daily_stats.my_report'))

        course_code = request.form.get('course_code')

        # 🔒 SEG-006: valida que el usuario pueda operar ese curso.
        # Lanza 403 si no es titular ni está en la M2M y no es especialista.
        get_course_or_403(course_code, Permission.DAILY_STATS_CREATE)

        # Validación de entrada: cantidades no negativas
        try:
            gp = int(request.form.get('girls_present', 0) or 0)
            bp = int(request.form.get('boys_present', 0) or 0)
            ga = int(request.form.get('girls_absent', 0) or 0)
            ba = int(request.form.get('boys_absent', 0) or 0)
        except ValueError:
            flash('Los valores de asistencia deben ser números enteros.', 'danger')
            return redirect(url_for('daily_stats.my_report'))

        if min(gp, bp, ga, ba) < 0:
            flash('Los valores de asistencia no pueden ser negativos.', 'danger')
            return redirect(url_for('daily_stats.my_report'))

        # Validación contra matrícula del curso a esa fecha
        matricula_actual = Enrollment.get_matricula(course_code, stat_date)
        if (gp + bp) > matricula_actual['total']:
            flash(
                f'La suma de presentes ({gp + bp}) supera la matrícula '
                f'({matricula_actual["total"]}) a esa fecha.',
                'danger'
            )
            return redirect(url_for('daily_stats.my_report'))

        data = {
            'girls_present': gp,
            'boys_present':  bp,
            'girls_absent':  ga,
            'boys_absent':   ba,
            'notes':         request.form.get('notes'),
        }
        if DailyAttendanceStat.get_or_create(course_code, stat_date,
                                             teacher['id'], data):
            flash('Reporte de asistencia guardado.', 'success')
            return redirect(url_for('daily_stats.my_report', date=stat_date))
        flash('Error al guardar.', 'danger')

    # ---------- GET: reportes ya cargados ----------
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

        teacher = Teacher.get_by_user_id(current_user.id)
        teacher_id = teacher['id'] if teacher else course.get('teacher_id')

        # Fallback: si no hay docente vinculado, se rechaza (antes se inventaba).
        if not teacher_id:
            flash('No hay docente asignado para asociar el reporte.', 'danger')
            return redirect(url_for('daily_stats.admin_view', date=stat_date))

        # Validación de entrada
        try:
            gp = int(request.form.get('girls_present', 0) or 0)
            bp = int(request.form.get('boys_present', 0) or 0)
            ga = int(request.form.get('girls_absent', 0) or 0)
            ba = int(request.form.get('boys_absent', 0) or 0)
        except ValueError:
            flash('Los valores de asistencia deben ser números enteros.', 'danger')
            return redirect(url_for('daily_stats.admin_report',
                                    course=course_code, date=stat_date))

        if min(gp, bp, ga, ba) < 0:
            flash('Los valores de asistencia no pueden ser negativos.', 'danger')
            return redirect(url_for('daily_stats.admin_report',
                                    course=course_code, date=stat_date))

        if (gp + bp) > matricula['total']:
            flash(
                f'La suma de presentes ({gp + bp}) supera la matrícula '
                f'({matricula["total"]}) a esa fecha.',
                'danger'
            )
            return redirect(url_for('daily_stats.admin_report',
                                    course=course_code, date=stat_date))

        data = {
            'girls_present': gp,
            'boys_present':  bp,
            'girls_absent':  ga,
            'boys_absent':   ba,
            'notes':         request.form.get('notes'),
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