from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.models.course import Course
from app.utils.decorators import role_required

enrollment_bp = Blueprint('enrollment', __name__, url_prefix='/enrollment')

@enrollment_bp.route('/')
@login_required
@role_required('directivo', 'secretario')
def list_view():
    enrollments = Enrollment.get_all()
    return render_template('enrollment/list.html', enrollments=enrollments)

@enrollment_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def new_enrollment():
    if request.method == 'POST':
        data = {
            'school_id': request.form['school_id'],
            'course_code': request.form['course_code'],
            'enrollment_date': request.form.get('enrollment_date'),
            'status': request.form.get('status', 'activo'),
            'egreso_date': request.form.get('egreso_date') or None
        }
        if Enrollment.create(data):
            flash('Inscripción registrada exitosamente.', 'success')
            return redirect(url_for('enrollment.list_view'))
        else:
            flash('Error al registrar la inscripción. Verifique que el estudiante no esté ya inscrito en ese curso.', 'danger')
    
    students = Student.get_all_with_details()
    courses = Course.get_all()
    return render_template('enrollment/form.html', students=students, courses=courses)

@enrollment_bp.route('/<int:enrollment_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def edit_view(enrollment_id):
    enrollment = Enrollment.get_by_id(enrollment_id)
    if not enrollment:
        flash('Inscripción no encontrada.', 'danger')
        return redirect(url_for('enrollment.list_view'))
    if request.method == 'POST':
        data = {
            'school_id': request.form['school_id'],
            'course_code': request.form['course_code'],
            'enrollment_date': request.form.get('enrollment_date'),
            'status': request.form.get('status'),
            'egreso_date': request.form.get('egreso_date') or None
        }
        if Enrollment.update(enrollment_id, data):
            flash('Inscripción actualizada.', 'success')
            return redirect(url_for('enrollment.list_view'))
        else:
            flash('Error al actualizar.', 'danger')
    
    students = Student.get_all_with_details()
    courses = Course.get_all()
    return render_template('enrollment/form.html', enrollment=enrollment, students=students, courses=courses)

@enrollment_bp.route('/<int:enrollment_id>/delete')
@login_required
@role_required('directivo')
def delete_view(enrollment_id):
    if Enrollment.delete(enrollment_id):
        flash('Inscripción eliminada.', 'success')
    else:
        flash('Error al eliminar.', 'danger')
    return redirect(url_for('enrollment.list_view'))