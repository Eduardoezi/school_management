from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from app.models.teacher import Teacher
from app.models.staff_detail import StaffDetail
from app.models.course import Course
from app.utils.decorators import role_required
from app.utils.db import get_db_connection


staff_profile_bp = Blueprint('staff_profile', __name__,
                              url_prefix='/staff/<int:teacher_id>/profile')


# ============================================================
# Helpers
# ============================================================
def _parse_hours(value):
    """
    Convierte un valor de formulario a Decimal o None.

    Acepta:
        '55', '55.33', Decimal('55.33'), None, '', 'None'
    Devuelve:
        Decimal o None (si vacío o inválido).
    """
    if value in (None, '', 'None'):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


# ============================================================
# VISTA: ver perfil del personal
# ============================================================
@staff_profile_bp.route('/')
@login_required
@role_required('directivo', 'secretario')
def view(teacher_id):
    teacher = Teacher.get_by_id(teacher_id)
    if not teacher:
        flash('Personal no encontrado.', 'danger')
        return redirect(url_for('teachers.list_view'))

    details = StaffDetail.get_by_teacher(teacher_id)

    all_courses = Course.get_all()
    courses_taught = Course.get_by_teacher(teacher_id)
    assigned_codes = {c['code'] for c in courses_taught}
    available_courses = [c for c in all_courses if c['code'] not in assigned_codes]

    is_specialist = bool(
        details
        and details.get('specialist_type')
        and details['specialist_type'] != 'ninguno'
    )

    return render_template('staff/profile/view.html',
                           teacher=teacher,
                           details=details,
                           courses_taught=courses_taught,
                           available_courses=available_courses,
                           is_specialist=is_specialist)


# ============================================================
# EDITAR: perfil laboral + datos bancarios
# ============================================================
@staff_profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def edit(teacher_id):
    teacher = Teacher.get_by_id(teacher_id)
    if not teacher:
        flash('Personal no encontrado.', 'danger')
        return redirect(url_for('teachers.list_view'))

    details = StaffDetail.get_by_teacher(teacher_id)

    if request.method == 'POST':
        # ---------------- Construcción del dict `data` ----------------
        # Aquí van TODOS los campos del formulario, incluidos los nuevos.
        data = {
            # ---- Datos laborales ----
            'codigo_rac':         request.form.get('codigo_rac'),
            'cargo':              request.form.get('cargo'),
            'staff_type':         request.form.get('staff_type') or None,
            'specialist_type':    request.form.get('specialist_type') or 'ninguno',
            'nominal_condition':  request.form.get('nominal_condition') or None,
            'sex':                request.form.get('sex') or None,
            'shirt_size':         request.form.get('shirt_size'),
            'pants_size':         request.form.get('pants_size'),
            'shoe_size':          request.form.get('shoe_size'),

            # ---- Horas (ahora como Decimal) ----
            'academic_hours':     _parse_hours(request.form.get('academic_hours')),
            'admin_hours':        _parse_hours(request.form.get('admin_hours')),

            'shift':              request.form.get('shift'),
            'worker_status':      request.form.get('worker_status'),
            'observations':       request.form.get('observations'),
            'specialty':          request.form.get('specialty'),
            'birth_city':         request.form.get('birth_city'),
            'birth_state':        request.form.get('birth_state'),

            # ---- Datos bancarios (NUEVOS) ----
            'bank_name':          request.form.get('bank_name'),
            'bank_account_type':  request.form.get('bank_account_type') or None,
            'bank_account_number': request.form.get('bank_account_number'),
        }

        if StaffDetail.save(teacher_id, data):
            flash('Perfil actualizado correctamente.', 'success')
            return redirect(url_for('staff_profile.view', teacher_id=teacher_id))
        flash('Error al guardar.', 'danger')

    return render_template('staff/profile/edit.html',
                           teacher=teacher,
                           details=details)


# ============================================================
# ASIGNAR CURSO (titular o especialista)
# ============================================================
@staff_profile_bp.route('/assign-course', methods=['POST'])
@login_required
@role_required('directivo', 'secretario')
def assign_course(teacher_id):
    teacher = Teacher.get_by_id(teacher_id)
    if not teacher:
        flash('Personal no encontrado.', 'danger')
        return redirect(url_for('teachers.list_view'))

    course_code = request.form.get('course_code')
    role = request.form.get('role', 'especialista')

    if not course_code:
        flash('Debes seleccionar un curso.', 'danger')
        return redirect(url_for('staff_profile.view', teacher_id=teacher_id))

    if role not in ('titular', 'especialista', 'auxiliar'):
        role = 'especialista'

    course = Course.get_by_code(course_code)
    if not course:
        flash('Curso no encontrado.', 'danger')
        return redirect(url_for('staff_profile.view', teacher_id=teacher_id))

    if role == 'titular':
        if course.get('teacher_id'):
            flash('Este curso ya tiene un titular asignado. '
                  'Asígnalo como especialista o auxiliar.', 'warning')
            return redirect(url_for('staff_profile.view', teacher_id=teacher_id))

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE courses SET teacher_id = %s WHERE code = %s",
                    (teacher_id, course_code)
                )
                conn.commit()
            finally:
                cursor.close()
                conn.close()

    if Course.assign_teacher(course_code, teacher_id, role):
        flash(f'Curso asignado como {role}.', 'success')
    else:
        flash('Error al asignar el curso.', 'danger')

    return redirect(url_for('staff_profile.view', teacher_id=teacher_id))


# ============================================================
# DESASIGNAR CURSO
# ============================================================
@staff_profile_bp.route('/unassign-course/<course_code>', methods=['POST'])
@login_required
@role_required('directivo', 'secretario')
def unassign_course(teacher_id, course_code):
    course = Course.get_by_code(course_code)
    if course and course.get('teacher_id') == teacher_id:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE courses SET teacher_id = NULL WHERE code = %s",
                    (course_code,)
                )
                conn.commit()
            finally:
                cursor.close()
                conn.close()

    if Course.unassign_teacher(course_code, teacher_id):
        flash('Curso desasignado correctamente.', 'success')
    else:
        flash('Error al desasignar el curso.', 'danger')

    return redirect(url_for('staff_profile.view', teacher_id=teacher_id))