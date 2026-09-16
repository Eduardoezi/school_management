from flask import Blueprint, render_template
from flask_login import login_required
from datetime import date

from app.models.student import Student
from app.models.teacher import Teacher
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.daily_attendance_stat import DailyAttendanceStat


main_bp = Blueprint('main', __name__)


# ---------- Página principal pública ----------
@main_bp.route('/')
def index():
    escuela = {
        'nombre': 'IEE Villa de Cura',
        'direccion': 'Calle Principal #123, Villa de Cura, Estado Aragua, Venezuela',
        'telefono': '+58 244-386-1234',
        'email': 'ieevilladecura@gmail.com',
        'codigo_DEA': 'OD-0459-05-16',
        'codigo_dependencia': '006417140',
        'Rif': 'j-30508137-9'
    }
    return render_template('index.html', escuela=escuela)


# ---------- Panel de control ----------
@main_bp.route('/dashboard')
@login_required
def dashboard():
    total_students = len(Student.get_all_with_details())
    total_teachers = len(Teacher.get_all())
    total_courses = len(Course.get_all())
    total_enrollments = Enrollment.count_active()

    # Estadística del día (opcional, para mostrar en el panel)
    hoy = date.today().strftime('%Y-%m-%d')
    stats_hoy = DailyAttendanceStat.get_summary_by_date(hoy)
    total_presentes_hoy = sum(row['total'] for row in stats_hoy) if stats_hoy else 0

    return render_template('dashboard.html',
                           total_students=total_students,
                           total_teachers=total_teachers,
                           total_courses=total_courses,
                           total_enrollments=total_enrollments,
                           total_presentes_hoy=total_presentes_hoy)