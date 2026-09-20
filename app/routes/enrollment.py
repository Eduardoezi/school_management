from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, abort
)
from flask_login import login_required

from app.models.enrollment import Enrollment
from app.models.student import Student
from app.models.course import Course
from app.utils.decorators import role_required

enrollment_bp = Blueprint('enrollment', __name__, url_prefix='/enrollment')


# ---------- LISTAR ----------
@enrollment_bp.route('/')
@login_required
@role_required('directivo', 'secretario')
def list_view():
    enrollments = Enrollment.get_all()
    return render_template('enrollment/list.html', enrollments=enrollments)


# ---------- CREAR ----------
@enrollment_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def new_enrollment():
    if request.method == 'POST':
        data = {
            'school_id':       request.form['school_id'],
            'course_code':     request.form['course_code'],
            'enrollment_date': request.form.get('enrollment_date'),
            'status':          request.form.get('status', 'activo'),
            'egreso_date':     request.form.get('egreso_date') or None,
        }
        if Enrollment.create(data):
            flash('Inscripción registrada exitosamente.', 'success')
            return redirect(url_for('enrollment.list_view'))
        flash(
            'Error al registrar la inscripción. Verifique que el estudiante '
            'no esté ya inscrito en ese curso.',
            'danger'
        )

    return render_template('enrollment/form.html',
                           students=Student.get_all_with_details(),
                           courses=Course.get_all())


# ---------- EDITAR ----------
@enrollment_bp.route('/<int:enrollment_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def edit_view(enrollment_id):
    enrollment = Enrollment.get_by_id(enrollment_id)
    if not enrollment:
        abort(404)

    if request.method == 'POST':
        data = {
            'school_id':       request.form['school_id'],
            'course_code':     request.form['course_code'],
            'enrollment_date': request.form.get('enrollment_date'),
            'status':          request.form.get('status'),
            'egreso_date':     request.form.get('egreso_date') or None,
        }
        if Enrollment.update(enrollment_id, data):
            flash('Inscripción actualizada.', 'success')
            return redirect(url_for('enrollment.list_view'))
        flash('Error al actualizar.', 'danger')

    return render_template('enrollment/form.html',
                           enrollment=enrollment,
                           students=Student.get_all_with_details(),
                           courses=Course.get_all())


# ---------- ELIMINAR: paso 1 (confirmación, GET) ----------
@enrollment_bp.route('/<int:enrollment_id>/delete', methods=['GET'])
@login_required
@role_required('directivo')
def confirm_delete(enrollment_id):
    enrollment = Enrollment.get_by_id(enrollment_id)
    if not enrollment:
        abort(404)

    return render_template(
        '_confirm_delete.html',
        title='¿Eliminar esta inscripción?',
        message=(
            'La inscripción se eliminará del registro. Si el estudiante '
            'tiene asistencias o evaluaciones asociadas, considera mejor '
            'cambiar el estado a "retirado" en lugar de borrar.'
        ),
        details=[
            ('Estudiante',    enrollment.get('student_name')),
            ('Curso',         enrollment.get('course_name') or enrollment.get('course_code')),
            ('Fecha ingreso', enrollment.get('enrollment_date')),
            ('Estado',        enrollment.get('status')),
        ],
        action_url=url_for('enrollment.delete', enrollment_id=enrollment_id),
        cancel_url=url_for('enrollment.list_view'),
    )


# ---------- ELIMINAR: paso 2 (ejecución, POST) ----------
@enrollment_bp.route('/<int:enrollment_id>/delete', methods=['POST'])
@login_required
@role_required('directivo')
def delete(enrollment_id):
    # ⚠️ Consideración: si más adelante decides NO borrar en duro,
    # reemplaza esta llamada por algo como:
    #   Enrollment.mark_as_withdrawn(enrollment_id, reason='...')
    # y deja la fila con status='retirado' para conservar historial.
    if Enrollment.delete(enrollment_id):
        flash('Inscripción eliminada.', 'success')
    else:
        flash('Error al eliminar.', 'danger')
    return redirect(url_for('enrollment.list_view'))