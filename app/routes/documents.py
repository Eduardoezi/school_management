from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, make_response, current_app
)
from flask_login import login_required, current_user
from datetime import date
import os
import base64

from app.models.student import Student
from app.models.teacher import Teacher
from app.models.staff_detail import StaffDetail
from app.models.institution_data import InstitutionData
from app.models.document_log import DocumentLog
from app.models.enrollment import Enrollment
from app.utils.decorators import role_required

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')


# ============================================================
# HELPERS
# ============================================================
def _logo_base64(institution):
    """Convierte el logo a base64 para embeberlo en el PDF."""
    if not institution or not institution.get('logo_path'):
        return None

    base_dir = os.path.join(current_app.root_path, 'static')
    logo_path = os.path.join(base_dir, institution['logo_path'])

    if not os.path.exists(logo_path):
        return None

    try:
        with open(logo_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
        ext = logo_path.rsplit('.', 1)[1].lower()
        mime = 'image/png' if ext == 'png' else 'image/jpeg'
        return f"data:{mime};base64,{data}"
    except Exception as e:
        print(f"[_logo_base64] {e}")
        return None


def _generate_pdf(html, filename):
    """Genera un PDF desde HTML usando xhtml2pdf."""
    from xhtml2pdf import pisa
    from io import BytesIO

    pdf_bytes = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_bytes, encoding='utf-8')

    if pisa_status.err:
        return None

    pdf_bytes.seek(0)
    response = make_response(pdf_bytes.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def _mes_en_letras(mes_num):
    meses = ['enero','febrero','marzo','abril','mayo','junio',
             'julio','agosto','septiembre','octubre','noviembre','diciembre']
    return meses[mes_num - 1]


def _fecha_en_letras(d):
    """Convierte una fecha a texto: '15 días del mes de abril del año 2026'."""
    return f"{d.day:02d} días del mes de {_mes_en_letras(d.month)} del año {d.year}"


def _edad_en_anios(birth_date):
    """Calcula la edad a partir de la fecha de nacimiento."""
    if not birth_date:
        return None
    hoy = date.today()
    return hoy.year - birth_date.year - (
        (hoy.month, hoy.day) < (birth_date.month, birth_date.day)
    )


# ============================================================
# CONSTANCIA DE ESTUDIOS
# ============================================================
@documents_bp.route('/constancia-estudio/<int:student_id>', methods=['GET'])
@login_required
@role_required('directivo', 'secretario', 'maestro')
def constancia_estudio(student_id):
    student = Student.get_by_id(student_id)
    if not student:
        flash('Estudiante no encontrado.', 'danger')
        return redirect(url_for('students.list_view'))

    # ¿Existe un documento ya emitido?
    existing = DocumentLog.find_existing('constancia_estudio', student_id=student_id)

    if existing:
        return redirect(url_for('documents.constancia_estudio_reprint',
                                log_id=existing['id']))

    # Emitir uno nuevo
    log = DocumentLog.issue(
        'constancia_estudio',
        student_id=student_id,
        issued_by=current_user.id
    )
    if not log:
        flash('Error al generar la constancia.', 'danger')
        return redirect(url_for('students.list_view'))

    return redirect(url_for('documents.constancia_estudio_pdf', log_id=log['id']))


@documents_bp.route('/constancia-estudio/reprint/<int:log_id>', methods=['GET'])
@login_required
@role_required('directivo', 'secretario', 'maestro')
def constancia_estudio_reprint(log_id):
    """Vista intermedia: pregunta si reimprimir la existente o emitir nueva."""
    log = DocumentLog.get_by_id(log_id)
    if not log or log['doc_type'] != 'constancia_estudio':
        flash('Documento no encontrado.', 'danger')
        return redirect(url_for('students.list_view'))

    student = Student.get_by_id(log['student_id'])
    if not student:
        flash('Estudiante no encontrado.', 'danger')
        return redirect(url_for('students.list_view'))

    return render_template('documents/confirm_reprint.html',
                           log=log,
                           student=student,
                           type='constancia_estudio')


@documents_bp.route('/constancia-estudio/new/<int:student_id>', methods=['POST'])
@login_required
@role_required('directivo', 'secretario')
def constancia_estudio_new(student_id):
    """Fuerza la emisión de una nueva constancia (con nuevo número)."""
    log = DocumentLog.issue(
        'constancia_estudio',
        student_id=student_id,
        issued_by=current_user.id
    )
    if not log:
        flash('Error al generar la constancia.', 'danger')
        return redirect(url_for('students.list_view'))

    return redirect(url_for('documents.constancia_estudio_pdf', log_id=log['id']))


@documents_bp.route('/constancia-estudio/pdf/<int:log_id>', methods=['GET'])
@login_required
@role_required('directivo', 'secretario', 'maestro')
def constancia_estudio_pdf(log_id):
    log = DocumentLog.get_by_id(log_id)
    if not log or log['doc_type'] != 'constancia_estudio':
        flash('Documento no encontrado.', 'danger')
        return redirect(url_for('students.list_view'))

    student = Student.get_by_id(log['student_id'])
    if not student:
        flash('Estudiante no encontrado.', 'danger')
        return redirect(url_for('students.list_view'))

    # Marcar como impreso
    DocumentLog.mark_printed(log_id)

    institution = InstitutionData.get()
    director = Teacher.get_director()
    logo_b64 = _logo_base64(institution)

    # Calcular edad
    birth = student.get('birth_date')
    if isinstance(birth, str):
        from datetime import datetime
        try:
            birth = datetime.strptime(birth, '%Y-%m-%d').date()
        except Exception:
            birth = None
    edad = _edad_en_anios(birth) if birth else None

    # Datos del curso actual
    course_info = None
    if student.get('course_code'):
        course_info = {
            'name': student.get('course_name'),
            'code': student.get('course_code')
        }
    else:
        # Intentar obtener inscripción activa
        enrollments = Enrollment.get_by_student(student['id'])
        active = [e for e in enrollments if e.get('status') == 'activo']
        if active:
            course_info = {
                'name': active[0].get('course_name'),
                'code': active[0].get('course_code')
            }

    today = date.today()
    context = {
        'institution': institution,
        'director': director,
        'logo_b64': logo_b64,
        'student': student,
        'edad': edad,
        'course_info': course_info,
        'log': log,
        'today': today,
        'fecha_letras': _fecha_en_letras(today),
        'year': today.year,
    }

    html = render_template('documents/constancia_estudio.html', **context)
    filename = f"{log['doc_number']}.pdf"
    return _generate_pdf(html, filename)


# ============================================================
# CERTIFICACIÓN DE FUNCIONES
# ============================================================
@documents_bp.route('/certificacion-funciones/<int:teacher_id>', methods=['GET'])
@login_required
@role_required('directivo', 'secretario')
def certificacion_funciones(teacher_id):
    teacher = Teacher.get_by_id(teacher_id)
    if not teacher:
        flash('Docente no encontrado.', 'danger')
        return redirect(url_for('teachers.list_view'))

    existing = DocumentLog.find_existing('certificacion_funciones', teacher_id=teacher_id)

    if existing:
        return redirect(url_for('documents.certificacion_funciones_reprint',
                                log_id=existing['id']))

    log = DocumentLog.issue(
        'certificacion_funciones',
        teacher_id=teacher_id,
        issued_by=current_user.id
    )
    if not log:
        flash('Error al generar la certificación.', 'danger')
        return redirect(url_for('teachers.list_view'))

    return redirect(url_for('documents.certificacion_funciones_pdf', log_id=log['id']))


@documents_bp.route('/certificacion-funciones/reprint/<int:log_id>', methods=['GET'])
@login_required
@role_required('directivo', 'secretario')
def certificacion_funciones_reprint(log_id):
    log = DocumentLog.get_by_id(log_id)
    if not log or log['doc_type'] != 'certificacion_funciones':
        flash('Documento no encontrado.', 'danger')
        return redirect(url_for('teachers.list_view'))

    teacher = Teacher.get_by_id(log['teacher_id'])
    if not teacher:
        flash('Docente no encontrado.', 'danger')
        return redirect(url_for('teachers.list_view'))

    return render_template('documents/confirm_reprint.html',
                           log=log,
                           teacher=teacher,
                           type='certificacion_funciones')


@documents_bp.route('/certificacion-funciones/new/<int:teacher_id>', methods=['POST'])
@login_required
@role_required('directivo', 'secretario')
def certificacion_funciones_new(teacher_id):
    log = DocumentLog.issue(
        'certificacion_funciones',
        teacher_id=teacher_id,
        issued_by=current_user.id
    )
    if not log:
        flash('Error al generar la certificación.', 'danger')
        return redirect(url_for('teachers.list_view'))

    return redirect(url_for('documents.certificacion_funciones_pdf', log_id=log['id']))


@documents_bp.route('/certificacion-funciones/pdf/<int:log_id>', methods=['GET'])
@login_required
@role_required('directivo', 'secretario')
def certificacion_funciones_pdf(log_id):
    log = DocumentLog.get_by_id(log_id)
    if not log or log['doc_type'] != 'certificacion_funciones':
        flash('Documento no encontrado.', 'danger')
        return redirect(url_for('teachers.list_view'))

    teacher = Teacher.get_by_id(log['teacher_id'])
    if not teacher:
        flash('Docente no encontrado.', 'danger')
        return redirect(url_for('teachers.list_view'))

    details = StaffDetail.get_by_teacher(log['teacher_id'])
    DocumentLog.mark_printed(log_id)

    institution = InstitutionData.get()
    director = Teacher.get_director()
    logo_b64 = _logo_base64(institution)

    # Fecha de ingreso en letras
    hire_date = teacher.get('hire_date')
    if isinstance(hire_date, str):
        from datetime import datetime
        try:
            hire_date = datetime.strptime(hire_date, '%Y-%m-%d').date()
        except Exception:
            hire_date = None

    hire_date_letras = None
    if hire_date:
        hire_date_letras = f"{hire_date.day} de {_mes_en_letras(hire_date.month).capitalize()} de {hire_date.year}"

    today = date.today()
    context = {
        'institution': institution,
        'director': director,
        'logo_b64': logo_b64,
        'teacher': teacher,
        'details': details,
        'log': log,
        'today': today,
        'fecha_letras': _fecha_en_letras(today),
        'hire_date_letras': hire_date_letras,
        'year': today.year,
    }

    html = render_template('documents/certificacion_funciones.html', **context)
    filename = f"{log['doc_number']}.pdf"
    return _generate_pdf(html, filename)