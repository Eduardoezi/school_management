"""
Blueprint de planes de aula.

Rutas:
    GET  /plans/                     → mis planes (docente) o bandeja (directivo)
    GET  /plans/new                  → crear plan
    POST /plans/new                  → guardar plan nuevo
    GET  /plans/<id>                 → ver detalle
    GET  /plans/<id>/edit            → editar (wizard)
    POST /plans/<id>/edit            → guardar cabecera
    POST /plans/<id>/submit          → enviar a revisión
    POST /plans/<id>/delete          → soft delete

    # Áreas
    POST /plans/<id>/areas/add
    POST /plans/areas/<area_id>/delete

    # Actividades
    POST /plans/areas/<area_id>/activities/add
    POST /plans/activities/<activity_id>/delete
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
from app.models.course import Course
from app.utils.decorators import role_required

from app.routes.plans_helpers import (
    get_current_teacher_or_403,
    get_active_year_or_abort,
    get_teacher_assignments,
    get_course_enrollment_count,
    teacher_can_use_course,
    can_view_plan,
    can_edit_plan,
    plan_access_required,
    area_access_required,
    activity_access_required,
)


plans_bp = Blueprint('plans', __name__, url_prefix='/plans')


# ============================================================
# LISTADO
# ============================================================
@plans_bp.route('/')
@login_required
def list_view():
    """Docentes ven sus planes. Directivos van a la bandeja."""
    year = get_active_year_or_abort()

    if current_user.role in ('directivo', 'secretario'):
        return redirect(url_for('plans.review_queue'))

    teacher = get_current_teacher_or_403()

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
    year = get_active_year_or_abort()
    teacher = get_current_teacher_or_403()

    # Asignaciones reales del docente
    assignments = get_teacher_assignments(teacher['id'], year['id'])

    if request.method == 'POST':
        # ---------------- Validaciones ----------------
        start_date = (request.form.get('start_date') or '').strip()
        end_date   = (request.form.get('end_date') or '').strip()
        course_code = (request.form.get('course_code') or '').strip() or None

        errors = []
        if not start_date:
            errors.append('La fecha de inicio es obligatoria.')
        if not end_date:
            errors.append('La fecha de fin es obligatoria.')
        if start_date and end_date and start_date > end_date:
            errors.append('La fecha de inicio no puede ser posterior a la de fin.')

        # Verificar que el curso pertenece al docente
        if course_code:
            allowed = {a['course_code'] for a in assignments}
            if course_code not in allowed:
                errors.append('El curso seleccionado no está entre tus asignaciones.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('plans/new.html',
                                   year=year,
                                   teacher=teacher,
                                   assignments=assignments,
                                   form=request.form)

        # ---------------- Persistencia ----------------
        # Buscar matrícula automáticamente
        enrollment_count = get_course_enrollment_count(course_code) if course_code else None

        # Buscar grado y sección del curso asignado
        grade = request.form.get('grade')
        section = request.form.get('section')
        if course_code:
            for a in assignments:
                if a['course_code'] == course_code:
                    grade = a['grade'] or grade
                    section = a['section'] or section
                    break

        data = {
            'academic_year_id':       year['id'],
            'teacher_id':             teacher['id'],
            'teacher_role_in_plan':   request.form.get('teacher_role_in_plan', 'titular'),
            'course_code':            course_code,
            'grade':                  grade,
            'section':                section,
            'planning_type':          request.form.get('planning_type', 'semanal'),
            'pedagogical_moment':     request.form.get('pedagogical_moment'),
            'start_date':             start_date,
            'end_date':               end_date,
            'location_type':          request.form.get('location_type', 'aula'),
            'enrollment_count':       enrollment_count,
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

    # GET
    return render_template('plans/new.html',
                           year=year,
                           teacher=teacher,
                           assignments=assignments,
                           form={})


# ============================================================
# DETALLE
# ============================================================
@plans_bp.route('/<int:plan_id>')
@login_required
def detail_view(plan_id):
    plan = ClassroomPlan.get_by_id(plan_id)
    if not can_view_plan(plan):
        abort(404)

    areas = PlanArea.get_by_plan(plan_id)
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
    if not can_view_plan(plan):
        abort(404)
    if not can_edit_plan(plan):
        flash('Este plan no se puede editar en su estado actual.', 'warning')
        return redirect(url_for('plans.detail_view', plan_id=plan_id))

    teacher = get_current_teacher_or_403()
    year = AcademicYear.get_by_id(plan['academic_year_id'])
    assignments = get_teacher_assignments(teacher['id'], year['id']) if year else []

    if request.method == 'POST':
        start_date = (request.form.get('start_date') or '').strip()
        end_date   = (request.form.get('end_date') or '').strip()
        course_code = (request.form.get('course_code') or '').strip() or None

        if start_date and end_date and start_date > end_date:
            flash('La fecha de inicio no puede ser posterior a la de fin.', 'danger')
            return redirect(url_for('plans.edit_view', plan_id=plan_id))

        if course_code:
            allowed = {a['course_code'] for a in assignments}
            if course_code not in allowed:
                flash('El curso seleccionado no está entre tus asignaciones.', 'danger')
                return redirect(url_for('plans.edit_view', plan_id=plan_id))

        enrollment_count = get_course_enrollment_count(course_code) if course_code else None

        grade = request.form.get('grade')
        section = request.form.get('section')
        if course_code:
            for a in assignments:
                if a['course_code'] == course_code:
                    grade = a['grade'] or grade
                    section = a['section'] or section
                    break

        data = {
            'course_code':            course_code,
            'grade':                  grade,
            'section':                section,
            'planning_type':          request.form.get('planning_type', 'semanal'),
            'pedagogical_moment':     request.form.get('pedagogical_moment'),
            'start_date':             start_date,
            'end_date':               end_date,
            'location_type':          request.form.get('location_type', 'aula'),
            'enrollment_count':       enrollment_count,
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

    areas = PlanArea.get_by_plan(plan_id)
    for area in areas:
        area['activities'] = PlanActivity.get_by_area(area['id'])

    return render_template('plans/edit.html',
                           plan=plan,
                           areas=areas,
                           assignments=assignments,
                           year=year)


# ============================================================
# ENVIAR A REVISIÓN
# ============================================================
@plans_bp.route('/<int:plan_id>/submit', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
@plan_access_required('edit')
def submit_view(plan_id, plan):
    areas = PlanArea.get_by_plan(plan_id)
    if not areas:
        flash('El plan debe tener al menos un área antes de enviarse.', 'warning')
        return redirect(url_for('plans.edit_view', plan_id=plan_id))

    if ClassroomPlan.submit_for_review(plan_id):
        PlanReview.create(
            plan_id=plan_id,
            reviewer_id=current_user.id,
            action='comentario',
            comment='Plan enviado a revisión por el docente.',
        )
        flash('Plan enviado a revisión.', 'success')
    else:
        flash('Error al enviar el plan.', 'danger')

    return redirect(url_for('plans.detail_view', plan_id=plan_id))


# ============================================================
# SOFT DELETE
# ============================================================
@plans_bp.route('/<int:plan_id>/delete', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
@plan_access_required('edit')
def delete_view(plan_id, plan):
    if ClassroomPlan.soft_delete(plan_id):
        flash('Plan eliminado.', 'success')
        return redirect(url_for('plans.list_view'))
    flash('Error al eliminar.', 'danger')
    return redirect(url_for('plans.detail_view', plan_id=plan_id))


# ============================================================
# BANDEJA DE REVISIÓN (Fase 3)
# ============================================================
@plans_bp.route('/review')
@login_required
@role_required('directivo', 'secretario')
def review_queue():
    year = get_active_year_or_abort()
    plans = ClassroomPlan.get_pending_review(academic_year_id=year['id'])
    return render_template('plans/review_queue.html',
                           plans=plans,
                           year=year)


# ============================================================
# ÁREAS
# ============================================================
@plans_bp.route('/<int:plan_id>/areas/add', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
@plan_access_required('edit')
def add_area(plan_id, plan):
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
@area_access_required('edit')
def delete_area(area_id, area, plan):
    if PlanArea.delete(area_id):
        flash('Área eliminada.', 'success')
    else:
        flash('Error al eliminar.', 'danger')
    return redirect(url_for('plans.edit_view', plan_id=plan['id']))


# ============================================================
# ACTIVIDADES
# ============================================================
@plans_bp.route('/areas/<int:area_id>/activities/add', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
@area_access_required('edit')
def add_activity(area_id, area, plan):
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


@plans_bp.route('/activities/<int:activity_id>/delete', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
@activity_access_required('edit')
def delete_activity(activity_id, activity, area, plan):
    if PlanActivity.delete(activity_id):
        flash('Actividad eliminada.', 'success')
    else:
        flash('Error al eliminar.', 'danger')
    return redirect(url_for('plans.edit_view', plan_id=plan['id']))