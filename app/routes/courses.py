"""
Rutas del módulo de cursos.

Vistas:
    - list_view:       listado según rol (admin / teacher / specialist).
    - create_view:     alta (solo directivo/secretario).
    - edit_view:       edición (solo directivo/secretario).
    - confirm_delete:  confirmación previa a eliminar (solo directivo).
    - delete:          elimina un curso (solo directivo).
"""

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, abort,
)
from flask_login import login_required, current_user

from app.models.course import Course
from app.models.teacher import Teacher
from app.utils.decorators import role_required


courses_bp = Blueprint('courses', __name__, url_prefix='/courses')


# ============================================================
# LISTAR
# ============================================================
@courses_bp.route('/')
@login_required
def list_view():
    """
    Listado de cursos según el rol del usuario:

        - maestro:     solo sus cursos (o todos si es especialista).
        - directivo/secretario: todos los cursos con acciones.
    """
    # ---------- Maestro / especialista ----------
    if current_user.role == 'maestro':
        teacher = Teacher.get_by_user_id(current_user.id)
        if not teacher:
            flash('Tu usuario no está vinculado a un docente.', 'danger')
            return redirect(url_for('main.dashboard'))

        # Especialistas ven toda la matrícula
        specialist = teacher.get('specialist_type')
        if specialist and specialist != 'ninguno':
            return render_template(
                'courses/list.html',
                courses=Course.get_all(),
                view_mode='specialist',
            )

        return render_template(
            'courses/list.html',
            courses=Course.get_by_teacher(teacher['id']),
            view_mode='teacher',
        )

    # ---------- Directivo / secretario ----------
    return render_template(
        'courses/list.html',
        courses=Course.get_all(),
        view_mode='admin',
    )


# ============================================================
# CREAR
# ============================================================
@courses_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def create_view():
    """Alta de curso. Solo directivo/secretario."""
    if request.method == 'POST':
        data = {
            'name':          request.form['name'].strip(),
            'code':          request.form['code'].strip(),
            'teacher_id':    request.form.get('teacher_id') or None,
            'grade':         request.form.get('grade'),
            'section':       request.form.get('section'),
            'academic_year': request.form.get('academic_year'),
        }

        result = Course.create(data)
        if result['success']:
            flash('Curso creado exitosamente.', 'success')
            return redirect(url_for('courses.list_view'))
        flash(f'Error: {result["error"]}', 'danger')

    return render_template(
        'courses/create.html',
        teachers=Teacher.get_all(),
    )


# ============================================================
# EDITAR
# ============================================================
@courses_bp.route('/<string:course_code>/edit', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def edit_view(course_code):
    """Edición de curso. Solo directivo/secretario."""
    course = Course.get_by_code(course_code)
    if not course:
        abort(404)

    if request.method == 'POST':
        data = {
            'name':          request.form['name'].strip(),
            'teacher_id':    request.form.get('teacher_id') or None,
            'grade':         request.form.get('grade'),
            'section':       request.form.get('section'),
            'academic_year': request.form.get('academic_year'),
        }

        result = Course.update(course_code, data)
        if result['success']:
            flash('Curso actualizado.', 'success')
            return redirect(url_for('courses.list_view'))
        flash(f'Error: {result["error"]}', 'danger')

    return render_template(
        'courses/edit.html',
        course=course,
        teachers=Teacher.get_all(),
    )


# ============================================================
# ELIMINAR: paso 1 (confirmación)
# ============================================================
@courses_bp.route('/<string:course_code>/delete', methods=['GET'])
@login_required
@role_required('directivo')
def confirm_delete(course_code):
    """Muestra la pantalla de confirmación antes de eliminar."""
    course = Course.get_by_code(course_code)
    if not course:
        abort(404)

    students_count = Course.count_students(course_code)

    return render_template(
        '_confirm_delete.html',
        title=f'¿Eliminar el curso {course.get("name", course_code)}?',
        message=(
            'Si el curso tiene estudiantes inscritos no podrá eliminarse.'
            if students_count > 0
            else 'Esta acción es permanente.'
        ),
        details=[
            ('Código',         course.get('code')),
            ('Grado/Sección',  f"{course.get('grade', '')} {course.get('section', '')}".strip()),
            ('Año académico',  course.get('academic_year')),
            ('Docente titular', course.get('teacher_name') or 'Sin asignar'),
            ('Estudiantes inscritos', students_count),
        ],
        action_url=url_for('courses.delete', course_code=course_code),
        cancel_url=url_for('courses.list_view'),
    )


# ============================================================
# ELIMINAR: paso 2 (ejecución)
# ============================================================
@courses_bp.route('/<string:course_code>/delete', methods=['POST'])
@login_required
@role_required('directivo')
def delete(course_code):
    """Elimina el curso. Falla si tiene estudiantes inscritos."""
    result = Course.delete(course_code)
    if result['success']:
        flash('Curso eliminado.', 'success')
    else:
        flash(f'Error: {result["error"]}', 'danger')
    return redirect(url_for('courses.list_view'))