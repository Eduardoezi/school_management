from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models.course import Course
from app.models.teacher import Teacher
from app.utils.decorators import role_required

courses_bp = Blueprint('courses', __name__, url_prefix='/courses')

@courses_bp.route('/')
@login_required
def list_view():
    courses = Course.get_all()
    return render_template('courses/list.html', courses=courses)

@courses_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def create_view():
    if request.method == 'POST':
        code = request.form['code'].strip()
        data = {
            'name': request.form['name'].strip(),
            'code': code,
            'teacher_id': request.form.get('teacher_id') or None,
            'grade': request.form.get('grade'),
            'section': request.form.get('section'),
            'academic_year': request.form.get('academic_year')
        }
        result = Course.create(data)
        if result['success']:
            flash('Curso creado exitosamente.', 'success')
            return redirect(url_for('courses.list_view'))
        else:
            flash(f'Error: {result["error"]}', 'danger')
    teachers = Teacher.get_all()
    return render_template('courses/create.html', teachers=teachers)

@courses_bp.route('/<string:course_code>/edit', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def edit_view(course_code):
    course = Course.get_by_code(course_code)
    if not course:
        flash('Curso no encontrado.', 'danger')
        return redirect(url_for('courses.list_view'))
    if request.method == 'POST':
        data = {
            'name': request.form['name'].strip(),
            'teacher_id': request.form.get('teacher_id') or None,
            'grade': request.form.get('grade'),
            'section': request.form.get('section'),
            'academic_year': request.form.get('academic_year')
        }
        result = Course.update(course_code, data)
        if result['success']:
            flash('Curso actualizado.', 'success')
            return redirect(url_for('courses.list_view'))
        else:
            flash(f'Error: {result["error"]}', 'danger')
    teachers = Teacher.get_all()
    return render_template('courses/edit.html', course=course, teachers=teachers)

@courses_bp.route('/<string:course_code>/delete')
@login_required
@role_required('directivo')
def delete_view(course_code):
    result = Course.delete(course_code)
    if result['success']:
        flash('Curso eliminado.', 'success')
    else:
        flash(f'Error: {result["error"]}', 'danger')
    return redirect(url_for('courses.list_view'))