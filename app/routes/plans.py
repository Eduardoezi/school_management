"""
Blueprint de planes de aula.

Rutas:
    GET  /plans/                     → mis planes
    GET  /plans/new                  → crear plan (formulario)
    POST /plans/new                  → guardar plan nuevo
    GET  /plans/<id>                 → ver detalle del plan
    GET  /plans/<id>/edit            → editar (wizard)
    POST /plans/<id>/edit            → guardar cabecera
    POST /plans/<id>/submit          → enviar a revisión
    POST /plans/<id>/delete          → soft delete

Reglas de permisos:
    - Un docente solo ve/edita SUS planes.
    - Un directivo puede ver todos (para revisión, Fase 4).
    - Solo el estado 'borrador' y 'devuelto' son editables.
"""

from __future__ import annotations

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, abort
)
from flask_login import login_required, current_user

from app.models.academic_year import AcademicYear
from app.models.classroom_plan import ClassroomPlan
from app.models.plan_area import PlanArea
from app.models.plan_activity import PlanActivity
from app.models.plan_review import PlanReview
from app.models.teacher import Teacher
from app.models.course import Course
from app.utils.decorators import role_required


plans_bp = Blueprint('plans', __name__, url_prefix='/plans')


# ============================================================
# Helpers
# ============================================================
def _current_teacher_or_404():
    """Devuelve el docente vinculado al usuario actual o aborta."""
    teacher = Teacher.get_by_user_id(current_user.id)
    if not teacher:
        abort(403, 'Tu usuario no está vinculado a un docente.')
    return teacher


def _can_access_plan(plan: dict) -> bool:
    """
    Determina si el usuario actual puede ver un plan.
    - Directivo/secretario: sí, cualquiera (para revisión).
    - Maestro: solo los suyos.
    """
    if not plan:
        return False
    if current_user.role in ('directivo', 'secretario'):
        return True
    teacher = Teacher.get_by_user_id(current_user.id)
    return teacher and plan['teacher_id'] == teacher['id']


def _can_edit_plan(plan: dict) -> bool:
    """Solo el autor del plan y solo en borrador/devuelto."""
    if not plan:
        return False
    teacher = Teacher.get_by_user_id(current_user.id)
    if not teacher or plan['teacher_id'] != teacher['id']:
        return False
    return plan['status'] in ('borrador', 'devuelto')


# ============================================================
# LISTADO
# ============================================================
@plans_bp.route('/')
@login_required
def list_view():
    """Listado de planes. Docentes ven solo los suyos."""
    year = AcademicYear.get_active()
    if not year:
        flash('No hay un año escolar activo. Contacta al directivo.', 'warning')
        return redirect(url_for('main.dashboard'))

    if current_user.role in ('directivo', 'secretario'):
        # Los directivos van a la bandeja de revisión (Fase 4)
        return redirect(url_for('plans.review_queue'))

    teacher = _current_teacher_or_404()

    plans = ClassroomPlan.get_by_teacher(
        teacher['id'],
        academic_year_id=year['id'],
    )
    return render_template('plans/list.html',
                           plans=plans,
                           teacher=teacher,
                           year=year)


# ============================================================
# CREAR
# ============================================================
@plans_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('maestro', 'directivo')
def create_view():
    year = AcademicYear.get_active()
    if not year:
        flash('No hay un año escolar activo.', 'warning')
        return redirect(url_for('plans.list_view'))

    teacher = _current_teacher_or_404()

    courses = Course.get_all()
    return render_template('plans/new.html',
                        year=year,
                        teacher=teacher,
                        courses=courses,
                        form={})

    if request.method == 'POST':
        # Validaciones mínimas
        start_date = (request.form.get('start_date') or '').strip()
        end_date   = (request.form.get('end_date') or '').strip()
        planning_type = request.form.get('planning_type', 'semanal')

        errors = []
        if not start_date:
            errors.append('La fecha de inicio es obligatoria.')
        if not end_date:
            errors.append('La fecha de fin es obligatoria.')
        if start_date and end_date and start_date > end_date:
            errors.append('La fecha de inicio no puede ser posterior a la de fin.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('plans/new.html',
                                   year=year,
                                   teacher=teacher,
                                   form=request.form)

        data = {
            'academic_year_id':       year['id'],
            'teacher_id':             teacher['id'],
            'teacher_role_in_plan':   request.form.get('teacher_role_in_plan', 'titular'),
            'course_code':            request.form.get('course_code') or None,
            'grade':                  request.form.get('grade'),
            'section':                request.form.get('section'),
            'planning_type':          planning_type,
            'pedagogical_moment':     request.form.get('pedagogical_moment'),
            'start_date':             start_date,
            'end_date':               end_date,
            'location_type':          request.form.get('location_type', 'aula'),
            'enrollment_count':       request.form.get('enrollment_count') or None,
            'situational_diagnosis':  request.form.get('situational_diagnosis'),
            'theoretical_foundation': request.form.get('theoretical_foundation'),
            'learning_project_title': request.form.get('learning_project_title'),
            'purposes':               request.form.get('purposes'),
            'research_line':          request.form.get('research_line'),
            'general_observations':   request.form.get('general_observations'),
        }

        plan_id = ClassroomPlan.create(data)
        if plan_id:
            flash('Plan creado. Ahora agrega las áreas y actividades.', 'success')
            return redirect(url_for('plans.edit_view', plan_id=plan_id))

        flash('Error al crear el plan.', 'danger')

    return render_template('plans/new.html',
                           year=year,
                           teacher=teacher,
                           form={})


# ============================================================
# VER DETALLE
# ============================================================
@plans_bp.route('/<int:plan_id>')
@login_required
def detail_view(plan_id):
    plan = ClassroomPlan.get_by_id(plan_id)
    if not _can_access_plan(plan):
        abort(404)

    areas = PlanArea.get_by_plan(plan_id)
    # Cargar actividades por área
    for area in areas:
        area['activities'] = PlanActivity.get_by_area(area['id'])

    reviews = PlanReview.get_by_plan(plan_id)

    return render_template('plans/detail.html',
                           plan=plan,
                           areas=areas,
                           reviews=reviews)


# ============================================================
# EDITAR (wizard)
# ============================================================
@plans_bp.route('/<int:plan_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('maestro', 'directivo')
def edit_view(plan_id):
    plan = ClassroomPlan.get_by_id(plan_id)
    if not _can_access_plan(plan):
        abort(404)

    if not _can_edit_plan(plan):
        flash('Este plan no se puede editar en su estado actual.', 'warning')
        return redirect(url_for('plans.detail_view', plan_id=plan_id))

    if request.method == 'POST':
        start_date = (request.form.get('start_date') or '').strip()
        end_date   = (request.form.get('end_date') or '').strip()

        if start_date and end_date and start_date > end_date:
            flash('La fecha de inicio no puede ser posterior a la de fin.', 'danger')
            return redirect(url_for('plans.edit_view', plan_id=plan_id))

        data = {
            'course_code':            request.form.get('course_code') or None,
            'grade':                  request.form.get('grade'),
            'section':                request.form.get('section'),
            'planning_type':          request.form.get('planning_type', 'semanal'),
            'pedagogical_moment':     request.form.get('pedagogical_moment'),
            'start_date':             start_date,
            'end_date':               end_date,
            'location_type':          request.form.get('location_type', 'aula'),
            'enrollment_count':       request.form.get('enrollment_count') or None,
            'situational_diagnosis':  request.form.get('situational_diagnosis'),
            'theoretical_foundation': request.form.get('theoretical_foundation'),
            'learning_project_title': request.form.get('learning_project_title'),
            'purposes':               request.form.get('purposes'),
            'research_line':          request.form.get('research_line'),
            'general_observations':   request.form.get('general_observations'),
        }

        if ClassroomPlan.update(plan_id, data):
            flash('Plan actualizado.', 'success')
        else:
            flash('Error al actualizar.', 'danger')

        return redirect(url_for('plans.edit_view', plan_id=plan_id))

    # GET: cargar áreas y actividades para mostrarlas en el wizard
    areas = PlanArea.get_by_plan(plan_id)
    for area in areas:
        area['activities'] = PlanActivity.get_by_area(area['id'])

    courses = Course.get_all()

    return render_template('plans/edit.html',
                           plan=plan,
                           areas=areas,
                           courses=courses)


# ============================================================
# ENVIAR A REVISIÓN
# ============================================================
@plans_bp.route('/<int:plan_id>/submit', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
def submit_view(plan_id):
    plan = ClassroomPlan.get_by_id(plan_id)
    if not _can_edit_plan(plan):
        flash('No puedes enviar este plan a revisión.', 'danger')
        return redirect(url_for('plans.detail_view', plan_id=plan_id))

    # Validar que tenga al menos un área
    areas = PlanArea.get_by_plan(plan_id)
    if not areas:
        flash('El plan debe tener al menos un área antes de enviarse.', 'warning')
        return redirect(url_for('plans.edit_view', plan_id=plan_id))

    if ClassroomPlan.submit_for_review(plan_id):
        flash('Plan enviado a revisión. El directivo lo evaluará pronto.', 'success')
    else:
        flash('Error al enviar el plan.', 'danger')

    return redirect(url_for('plans.detail_view', plan_id=plan_id))


# ============================================================
# SOFT DELETE
# ============================================================
@plans_bp.route('/<int:plan_id>/delete', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
def delete_view(plan_id):
    plan = ClassroomPlan.get_by_id(plan_id)
    if not _can_edit_plan(plan):
        flash('No puedes eliminar este plan.', 'danger')
        return redirect(url_for('plans.detail_view', plan_id=plan_id))

    if ClassroomPlan.soft_delete(plan_id):
        flash('Plan eliminado.', 'success')
    else:
        flash('Error al eliminar.', 'danger')

    return redirect(url_for('plans.list_view'))


# ============================================================
# ÁREAS: acciones AJAX
# ============================================================
@plans_bp.route('/<int:plan_id>/areas/add', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
def add_area(plan_id):
    plan = ClassroomPlan.get_by_id(plan_id)
    if not _can_edit_plan(plan):
        abort(403)

    area_id = PlanArea.create(plan_id, {
        'formation_area':        request.form.get('formation_area'),
        'pedagogical_approach':  request.form.get('pedagogical_approach'),
        'curricular_components': request.form.get('curricular_components'),
        'essential_themes':      request.form.get('essential_themes'),
        'contents':              request.form.get('contents'),
        'expected_learning':     request.form.get('expected_learning'),
        'tasks':                 request.form.get('tasks'),
    })

    if area_id:
        flash('Área agregada.', 'success')
    else:
        flash('Error al agregar el área.', 'danger')

    return redirect(url_for('plans.edit_view', plan_id=plan_id))


@plans_bp.route('/areas/<int:area_id>/delete', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
def delete_area(area_id):
    area = PlanArea.get_by_id(area_id)
    if not area:
        abort(404)

    plan = ClassroomPlan.get_by_id(area['plan_id'])
    if not _can_edit_plan(plan):
        abort(403)

    if PlanArea.delete(area_id):
        flash('Área eliminada.', 'success')
    else:
        flash('Error al eliminar.', 'danger')

    return redirect(url_for('plans.edit_view', plan_id=plan['id']))


# ============================================================
# ACTIVIDADES: acciones AJAX
# ============================================================
@plans_bp.route('/areas/<int:area_id>/activities/add', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
def add_activity(area_id):
    area = PlanArea.get_by_id(area_id)
    if not area:
        abort(404)

    plan = ClassroomPlan.get_by_id(area['plan_id'])
    if not _can_edit_plan(plan):
        abort(403)

    activity_id = PlanActivity.create(area_id, {
        'title':                  request.form.get('title'),
        'description':            request.form.get('description'),
        'strategy':               request.form.get('strategy'),
        'indicators':             request.form.get('indicators'),
        'resources':              request.form.get('resources'),
        'evaluation_technique':   request.form.get('evaluation_technique'),
        'evaluation_instrument':  request.form.get('evaluation_instrument'),
        'curricular_emphasis':    request.form.get('curricular_emphasis'),
        'start_datetime':         request.form.get('start_datetime') or None,
        'end_datetime':           request.form.get('end_datetime') or None,
        'location':               request.form.get('location'),
    })

    if activity_id:
        flash('Actividad agregada.', 'success')
    else:
        flash('Error al agregar la actividad.', 'danger')

    return redirect(url_for('plans.edit_view', plan_id=plan['id']))


# ============================================================
# BANDEJA DE REVISIÓN (Fase 4, provisional)
# ============================================================
@plans_bp.route('/review')
@login_required
@role_required('directivo', 'secretario')
def review_queue():
    """Bandeja de planes pendientes de revisión."""
    year = AcademicYear.get_active()
    if not year:
        flash('No hay un año escolar activo.', 'warning')
        return redirect(url_for('main.dashboard'))

    plans = ClassroomPlan.get_pending_review(academic_year_id=year['id'])
    return render_template('plans/review_queue.html',
                           plans=plans,
                           year=year)


@plans_bp.route('/activities/<int:activity_id>/delete', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
def delete_activity(activity_id):
    activity = PlanActivity.get_by_id(activity_id)
    if not activity:
        abort(404)

    area = PlanArea.get_by_id(activity['plan_area_id'])
    plan = ClassroomPlan.get_by_id(area['plan_id'])
    if not _can_edit_plan(plan):
        abort(403)

    if PlanActivity.delete(activity_id):
        flash('Actividad eliminada.', 'success')
    else:
        flash('Error al eliminar.', 'danger')

    return redirect(url_for('plans.edit_view', plan_id=plan['id']))

@plans_bp.route('/activities/<int:activity_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('maestro', 'directivo')
def edit_activity(activity_id):
    activity = PlanActivity.get_by_id(activity_id)
    if not activity:
        abort(404)

    area = PlanArea.get_by_id(activity['plan_area_id'])
    plan = ClassroomPlan.get_by_id(area['plan_id'])
    if not _can_edit_plan(plan):
        abort(403)

    if request.method == 'POST':
        data = {
            'title':                  request.form.get('title'),
            'description':            request.form.get('description'),
            'strategy':               request.form.get('strategy'),
            'indicators':             request.form.get('indicators'),
            'resources':              request.form.get('resources'),
            'evaluation_technique':   request.form.get('evaluation_technique'),
            'evaluation_instrument':  request.form.get('evaluation_instrument'),
            'curricular_emphasis':    request.form.get('curricular_emphasis'),
            'start_datetime':         request.form.get('start_datetime') or None,
            'end_datetime':           request.form.get('end_datetime') or None,
            'location':               request.form.get('location'),
        }
        if PlanActivity.update(activity_id, data):
            flash('Actividad actualizada.', 'success')
        else:
            flash('Error al actualizar.', 'danger')
        return redirect(url_for('plans.edit_view', plan_id=plan['id']))

    return render_template('plans/activity_edit.html',
                           activity=activity, area=area, plan=plan)