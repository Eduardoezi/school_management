from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask import jsonify
from flask_login import login_required, current_user
from app.models.student import Student
from app.models.course import Course
from app.models.representative import Representative
from app.utils.decorators import role_required
from app.models.teacher import Teacher

students_bp = Blueprint('students', __name__, url_prefix='/students')


def _is_specialist(teacher):
    """Devuelve True si el docente es especialista (ve toda la matrícula)."""
    if not teacher:
        return False
    spec = teacher.get('specialist_type')
    return bool(spec and spec != 'ninguno')


# ---------- LISTAR ----------
@students_bp.route('/')
@login_required
def list_view():
    # --- MAESTRO / ESPECIALISTA ---
    if current_user.role == 'maestro':
        teacher = Teacher.get_by_user_id(current_user.id)
        if not teacher:
            flash('Tu usuario no está vinculado a un docente.', 'danger')
            return redirect(url_for('main.dashboard'))

        # Especialista: ve toda la matrícula activa
        if _is_specialist(teacher):
            students = Student.get_all_with_details(status='activo')
            return render_template('students/list.html',
                                students=students,
                                view_mode='specialist')

        # Docente normal: solo sus cursos (todos los que tenga asignados)
        students = Student.get_by_teacher_course(teacher['id'])
        return render_template('students/list.html',
                            students=students,
                            view_mode='teacher')
    # --- DIRECTIVO / SECRETARIO ---
    view_mode = request.args.get('view', 'enrolled')

    if view_mode == 'all':
        students = Student.get_all_with_details(status=None)
    else:
        students = Student.get_all_with_details(status='activo')

    return render_template('students/list.html',
                           students=students,
                           view_mode=view_mode)


# ---------- CREAR ----------
@students_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def create_view():
    if request.method == 'POST':
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
        flash('Error al crear estudiante.', 'danger')

    return render_template('students/create.html', courses=Course.get_all())


# ---------- DETALLE ----------
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
            'representative_cedula': request.form['representative_cedula'],
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
        flash('Error al actualizar estudiante.', 'danger')

    courses = Course.get_all()
    return render_template('students/edit.html', student=student, courses=courses)


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


# ---------- API REPRESENTANTE ----------
@students_bp.route('/api/representative/<path:cedula>')
@login_required
def api_get_representative(cedula):
    rep = Representative.get_by_cedula(cedula)
    if rep:
        return jsonify({'found': True, 'data': rep})
    return jsonify({'found': False})