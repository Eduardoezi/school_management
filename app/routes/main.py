from flask import Blueprint, render_template
from flask_login import login_required
from datetime import date
from app.models.institution_data import InstitutionData
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.daily_attendance_stat import DailyAttendanceStat
from flask import send_file
import os




main_bp = Blueprint('main', __name__)


# ---------- Página principal pública ----------
@main_bp.route('/')
def index():
    escuela = InstitutionData.get() or {
        'nombre': 'Institución Educativa',
        'direccion': '-',
        'telefono': '-',
        'email': '-',
        'codigo_dea': '-',
        'codigo_dependencia': '-',
        'codigo_administrativo': '-',
        'rif': '-'
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

@main_bp.route('/ca.pem')
def download_ca():
    path = os.path.join(os.getcwd(), 'certs', 'public', 'rootCA.pem')
    return send_file(path, as_attachment=True, download_name='rootCA.pem')