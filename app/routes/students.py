from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask import jsonify
from flask_login import login_required
from app.models.student import Student
from app.models.course import Course
from app.models.representative import Representative
from app.utils.decorators import role_required

students_bp = Blueprint('students', __name__, url_prefix='/students')

# ---------- LISTAR ----------
@students_bp.route('/')
@login_required
def list_view():
    students = Student.get_all_with_details()
    return render_template('students/list.html', students=students)

# ---------- CREAR (NUEVO) ----------
@students_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def create_view():
    if request.method == 'POST':
        # 1. Guardar representante
        rep_data = {
            'cedula_id': request.form['rep_cedula_id'],
            'first_name': request.form['rep_first_name'],
            'last_name': request.form['rep_last_name'],
            'email': request.form.get('rep_email'),
            'phone': request.form.get('rep_phone'),
            'address': request.form.get('rep_address'),
            'relationship': request.form.get('rep_relationship')
        }
        
        rep_cedula = Representative.get_or_create(rep_data)
        if not rep_cedula:
            flash('Error al guardar representante. Verifique que la cédula no esté duplicada.', 'danger')
            return render_template('students/create.html', courses=Course.get_all())

        # 2. Guardar estudiante
        student_data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'multiple_birth_order': int(request.form.get('multiple_birth_order', 1)),
            'birth_date': request.form.get('birth_date'),
            'representative_cedula': rep_cedula,
            'course_code': request.form.get('course_code') or None,
            'disability': request.form.get('disability')
        }
        school_id = Student.create_full(student_data)
        if school_id:
            flash(f'Estudiante creado con cédula escolar {school_id}.', 'success')
            return redirect(url_for('students.list_view'))
        else:
            flash('Error al crear estudiante.', 'danger')

    return render_template('students/create.html', courses=Course.get_all())



# ---------- DETALLE (VER) ----------
@students_bp.route('/<int:student_id>')
@login_required
@role_required('directivo', 'secretario')
def detail_view(student_id):
    student = Student.get_by_id(student_id)
    if not student:
        flash('Estudiante no encontrado.', 'danger')
        return redirect(url_for('students.list_view'))
    return render_template('students/detail_edit.html', student=student, courses=Course.get_all())

# ---------- EDITAR ----------
@students_bp.route('/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def edit_view(student_id):
    student = Student.get_by_id(student_id)
    if not student:
        flash('Estudiante no encontrado.', 'danger')
        return redirect(url_for('students.list_view'))

    if request.method == 'POST':
        data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'multiple_birth_order': int(request.form.get('multiple_birth_order', 1)),
            'birth_date': request.form.get('birth_date'),
            'course_code': request.form.get('course_code') or None,
            'disability': request.form.get('disability'),
            'rep_cedula_id': request.form.get('rep_cedula_id'),
            'rep_first_name': request.form['rep_first_name'],
            'rep_last_name': request.form['rep_last_name'],
            'rep_email': request.form.get('rep_email'),
            'rep_phone': request.form.get('rep_phone'),
            'rep_address': request.form.get('rep_address'),
            'rep_relationship': request.form.get('rep_relationship')
        }
        
        if Student.update_full(student_id, data):
            flash('Estudiante actualizado exitosamente.', 'success')
            return redirect(url_for('students.detail_view', student_id=student_id))
        else:
            flash('Error al actualizar estudiante.', 'danger')

    # GET: mostrar formulario con datos actuales
    courses = Course.get_all()
    representatives = Representative.get_all()
    return render_template('students/edit.html', 
                           student=student, 
                           courses=courses,
                           representatives=representatives)

# ---------- ELIMINAR ----------
@students_bp.route('/<int:student_id>/delete')
@login_required
@role_required('directivo')
def delete_view(student_id):
    if Student.delete(student_id):
        flash('Estudiante eliminado.', 'success')
    else:
        flash('Error al eliminar estudiante.', 'danger')
    return redirect(url_for('students.list_view'))

@students_bp.route('/api/representative/<cedula>')
@login_required
def api_get_representative(cedula):
    rep = Representative.get_by_cedula(cedula)
    if rep:
        return {'found': True, 'data': rep}
    return {'found': False}