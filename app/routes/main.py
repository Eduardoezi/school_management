from flask import Blueprint, render_template
from flask_login import login_required
from datetime import date, timedelta
from app.models.institution_data import InstitutionData
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.daily_attendance_stat import DailyAttendanceStat
from app.models.school_calendar import SchoolCalendar
from flask import send_file
from flask_login import current_user
import json
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

    # ---------- Calendario visible según rol ----------
    calendar_record = None
    published = SchoolCalendar.get_current_published()

    if current_user.role == 'directivo':
        all_cal = SchoolCalendar.get_all()
        calendar_record = all_cal[0] if all_cal else published
    else:
        calendar_record = published

    events_json = "[]"
    total_holidays = 0

    if calendar_record:
        events = SchoolCalendar.get_events(calendar_record['id'], 'both')
        serialized = []
        for ev in events:
            color = "#3b82f6" if ev['origin'] == 'ministerio' else "#10b981"
            # FullCalendar usa 'end' exclusivo → sumamos 1 día
            end_exclusive = ev['end_date'] + timedelta(days=1)
            item = {
                'id': ev['id'],
                'title': ev['title'],
                'start': ev['start_date'].isoformat(),
                'end': end_exclusive.isoformat(),
                'allDay': True,
                'backgroundColor': color,
                'borderColor': color,
                'textColor': '#ffffff',
                'extendedProps': {
                    'origin': ev['origin'],
                    'category': ev.get('category') or '',
                    'description': ev.get('description') or '',
                    'affects_classes': bool(ev.get('affects_classes')),
                    'affects_attendance': bool(ev.get('affects_attendance')),
                },
            }
            if current_user.role == 'directivo':
                from flask import url_for
                item['url'] = url_for('calendar.event_edit', event_id=ev['id'])
            serialized.append(item)

            # Contador de feriados / asuetos / recesos
            if ev.get('category') in ('feriado', 'asueto', 'receso'):
                total_holidays += 1

        events_json = json.dumps(serialized, ensure_ascii=False)

    return render_template(
        'dashboard.html',
        total_students=total_students,
        total_teachers=total_teachers,
        total_courses=total_courses,
        total_enrollments=total_enrollments,
        total_presentes_hoy=total_presentes_hoy,
        calendar=calendar_record,
        events_json=events_json,
        total_holidays=total_holidays,
    )


@main_bp.route('/ca.pem')
def download_ca():
    path = os.path.join(os.getcwd(), 'certs', 'public', 'rootCA.pem')
    return send_file(path, as_attachment=True, download_name='rootCA.pem')