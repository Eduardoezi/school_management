"""
Blueprint de planes de aula.

Rutas:
    GET  /plans/                     → mis planes (docente) / bandeja (directivo)
    GET  /plans/new                  → crear plan
    POST /plans/new                  → guardar
    GET  /plans/<id>                 → ver detalle
    GET  /plans/<id>/edit            → editar (wizard)
    POST /plans/<id>/edit            → guardar cabecera
    GET  /plans/<id>/validate        → validar antes de enviar
    POST /plans/<id>/submit          → enviar a revisión
    POST /plans/<id>/delete          → soft delete
    GET  /plans/review               → bandeja del director

    # Áreas
    POST /plans/<id>/areas/add
    GET  /plans/areas/<id>/edit
    POST /plans/areas/<id>/edit
    POST /plans/areas/<id>/delete

    # Actividades
    POST /plans/areas/<id>/activities/add
    GET  /plans/activities/<id>/edit
    POST /plans/activities/<id>/edit
    POST /plans/activities/<id>/delete

    # Revisión del director
    GET  /plans/review/<id>          → revisar plan completo
    POST /plans/<id>/approve         → aprobar
    POST /plans/<id>/return          → devolver con observaciones
    POST /plans/<id>/comment         → agregar comentario
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
from app.models.pedagogical_moment import PedagogicalMoment
from app.models.evaluation_period import EvaluationPeriod

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
# HELPERS INTERNOS
# ============================================================
def _safe_model_list(model, *method_names):
    """
    Devuelve el resultado del primer método que exista en `model`
    entre los nombres provistos. Si ninguno existe o falla,
    devuelve una lista vacía (evita que la vista se rompa).

    Uso:
        _safe_model_list(PedagogicalMoment, 'get_all_active', 'get_all')
    """
    for name in method_names:
        fn = getattr(model, name, None)
        if callable(fn):
            try:
                result = fn()
                if result:
                    return result
            except Exception as exc:
                print(f"[plans._safe_model_list] {model.__name__}.{name} -> {exc}")
    return []


def _load_catalogs():
    """
    Carga los catálogos para el formulario de planes:
      - pedagogical_moments: los 3 LAPSOS del año escolar
      - academic_periods:    los ~9 períodos de evaluación
                             (3 por lapso: Diagnóstico / Formativa / Calificativa)
    """
    pedagogical_moments = _safe_model_list(
        PedagogicalMoment,
        'get_all_active', 'get_active', 'get_all', 'list_all',
    )
    academic_periods = _safe_model_list(
        EvaluationPeriod,
        'get_all_active', 'get_all', 'list_all',
    )
    return pedagogical_moments, academic_periods


# ============================================================
# LISTADO
# ============================================================
@plans_bp.route('/')
@login_required
def list_view():
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
    assignments = get_teacher_assignments(teacher['id'], year['id'])

    pedagogical_moments, academic_periods = _load_catalogs()

    if request.method == 'POST':
        start_date = (request.form.get('start_date') or '').strip()
        end_date = (request.form.get('end_date') or '').strip()
        course_code = (request.form.get('course_code') or '').strip() or None

        errors = []
        if not start_date:
            errors.append('La fecha de inicio es obligatoria.')
        if not end_date:
            errors.append('La fecha de fin es obligatoria.')
        if start_date and end_date and start_date > end_date:
            errors.append('La fecha de inicio no puede ser posterior a la de fin.')

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
                                   pedagogical_moments=pedagogical_moments,
                                   academic_periods=academic_periods,
                                   form=request.form)

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
            'academic_year_id': year['id'],
            'teacher_id': teacher['id'],
            'teacher_role_in_plan': request.form.get('teacher_role_in_plan', 'titular'),
            'course_code': course_code,
            'grade': grade,
            'section': section,
            'planning_type': request.form.get('planning_type', 'semanal'),
            'pedagogical_moment': request.form.get('pedagogical_moment'),
            'start_date': start_date,
            'end_date': end_date,
            'location_type': request.form.get('location_type', 'aula'),
            'enrollment_count': enrollment_count,
            'situational_diagnosis': request.form.get('situational_diagnosis'),
            'theoretical_foundation': request.form.get('theoretical_foundation'),
            'learning_project_title': request.form.get('learning_project_title'),
            'purposes': request.form.get('purposes'),
            'research_line': request.form.get('research_line'),
            'general_observations': request.form.get('general_observations'),
        }

        plan_id = ClassroomPlan.create(data)
        if plan_id:
            flash('Plan creado. Ahora agrega las áreas y actividades.', 'success')
            return redirect(url_for('plans.edit_view', plan_id=plan_id))

        flash('Error al crear el plan.', 'danger')

    return render_template('plans/new.html',
                           year=year,
                           teacher=teacher,
                           assignments=assignments,
                           pedagogical_moments=pedagogical_moments,
                           academic_periods=academic_periods,
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

    pedagogical_moments, academic_periods = _load_catalogs()

    if request.method == 'POST':
        start_date = (request.form.get('start_date') or '').strip()
        end_date = (request.form.get('end_date') or '').strip()
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
            'course_code': course_code,
            'grade': grade,
            'section': section,
            'planning_type': request.form.get('planning_type', 'semanal'),
            'pedagogical_moment': request.form.get('pedagogical_moment'),
            'start_date': start_date,
            'end_date': end_date,
            'location_type': request.form.get('location_type', 'aula'),
            'enrollment_count': enrollment_count,
            'situational_diagnosis': request.form.get('situational_diagnosis'),
            'theoretical_foundation': request.form.get('theoretical_foundation'),
            'learning_project_title': request.form.get('learning_project_title'),
            'purposes': request.form.get('purposes'),
            'research_line': request.form.get('research_line'),
            'general_observations': request.form.get('general_observations'),
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
                           year=year,
                           pedagogical_moments=pedagogical_moments,
                           academic_periods=academic_periods)


# ============================================================
# VALIDAR (antes de enviar)
# ============================================================
@plans_bp.route('/<int:plan_id>/validate')
@login_required
@role_required('maestro', 'directivo')
@plan_access_required('edit')
def validate_view(plan_id, plan):
    from app.utils.plan_validation import validate_plan_for_submission
    result = validate_plan_for_submission(plan_id)
    return render_template('plans/validate.html',
                           plan=plan,
                           result=result)


# ============================================================
# ENVIAR A REVISIÓN
# ============================================================
@plans_bp.route('/<int:plan_id>/submit', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
@plan_access_required('edit')
def submit_view(plan_id, plan):
    from app.utils.plan_validation import validate_plan_for_submission

    result = validate_plan_for_submission(plan_id)

    if not result['is_valid']:
        flash(
            f'No puedes enviar el plan todavía. Se encontraron '
            f'{result["summary"]["total_errors"]} problemas.',
            'danger'
        )
        return redirect(url_for('plans.validate_view', plan_id=plan_id))

    if ClassroomPlan.submit_for_review(plan_id):
        PlanReview.create(
            plan_id=plan_id,
            reviewer_id=current_user.id,
            action='comentario',
            comment='Plan enviado a revisión por el docente.',
        )
        flash('Plan enviado a revisión.', 'success')
        return redirect(url_for('plans.detail_view', plan_id=plan_id))

    flash('Error al enviar el plan.', 'danger')
    return redirect(url_for('plans.edit_view', plan_id=plan_id))


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
# BANDEJA DE REVISIÓN
# ============================================================
@plans_bp.route('/review')
@login_required
@role_required('directivo', 'secretario')
def review_queue():
    """Bandeja con filtros y contadores."""
    year = get_active_year_or_abort()

    teacher_filter = request.args.get('teacher', type=int)
    grade_filter = request.args.get('grade', type=str)
    status_filter = request.args.get('status', default='enviado')

    if status_filter not in ('enviado', 'devuelto', 'aprobado', 'todos'):
        status_filter = 'enviado'

    all_plans = ClassroomPlan.get_by_academic_year(year['id'])

    plans = []
    for p in all_plans:
        if status_filter != 'todos' and p['status'] != status_filter:
            continue
        if teacher_filter and p['teacher_id'] != teacher_filter:
            continue
        if grade_filter and p.get('grade') != grade_filter:
            continue
        plans.append(p)

    counters = {
        'enviado': sum(1 for p in all_plans if p['status'] == 'enviado'),
        'devuelto': sum(1 for p in all_plans if p['status'] == 'devuelto'),
        'aprobado': sum(1 for p in all_plans if p['status'] == 'aprobado'),
        'publicado': sum(1 for p in all_plans if p['status'] == 'publicado'),
        'total': len(all_plans),
    }

    from app.models.teacher import Teacher
    teachers = Teacher.get_all()
    grades = sorted({p['grade'] for p in all_plans if p.get('grade')})

    return render_template('plans/review_queue.html',
                           plans=plans,
                           year=year,
                           counters=counters,
                           teachers=teachers,
                           grades=grades,
                           teacher_filter=teacher_filter,
                           grade_filter=grade_filter,
                           status_filter=status_filter)


# ============================================================
# REVISIÓN DEL DIRECTOR
# ============================================================
@plans_bp.route('/review/<int:plan_id>')
@login_required
@role_required('directivo', 'secretario')
def review_view(plan_id):
    """Vista de revisión: el director ve el plan completo."""
    plan = ClassroomPlan.get_by_id(plan_id)
    if not plan:
        abort(404)

    areas = PlanArea.get_by_plan(plan_id)
    for area in areas:
        area['activities'] = PlanActivity.get_by_area(area['id'])

    reviews = PlanReview.get_by_plan(plan_id)

    return render_template('plans/review.html',
                           plan=plan,
                           areas=areas,
                           reviews=reviews)


@plans_bp.route('/<int:plan_id>/approve', methods=['POST'])
@login_required
@role_required('directivo')
@plan_access_required('review')
def approve_view(plan_id, plan):
    """El director aprueba el plan."""
    comment = (request.form.get('comment') or '').strip()

    if ClassroomPlan.approve(plan_id):
        PlanReview.create(
            plan_id=plan_id,
            reviewer_id=current_user.id,
            action='aprobado',
            comment=comment or 'Plan aprobado.',
        )
        flash(
            'Plan aprobado. El docente puede publicarlo cuando esté listo.',
            'success'
        )
        return redirect(url_for('plans.review_queue'))

    flash('Error al aprobar el plan.', 'danger')
    return redirect(url_for('plans.review_view', plan_id=plan_id))


@plans_bp.route('/<int:plan_id>/return', methods=['POST'])
@login_required
@role_required('directivo')
@plan_access_required('review')
def return_view(plan_id, plan):
    """El director devuelve el plan con observaciones."""
    comment = (request.form.get('comment') or '').strip()

    if not comment:
        flash('Debes indicar las observaciones para devolver el plan.', 'danger')
        return redirect(url_for('plans.review_view', plan_id=plan_id))

    if ClassroomPlan.return_for_correction(plan_id):
        PlanReview.create(
            plan_id=plan_id,
            reviewer_id=current_user.id,
            action='devuelto',
            comment=comment,
        )
        flash('Plan devuelto al docente con recomendaciones.', 'info')
        return redirect(url_for('plans.review_queue'))

    flash('Error al devolver el plan.', 'danger')
    return redirect(url_for('plans.review_view', plan_id=plan_id))


@plans_bp.route('/<int:plan_id>/comment', methods=['POST'])
@login_required
@role_required('directivo', 'secretario')
def add_comment_view(plan_id):
    """Agrega un comentario sin cambiar el estado."""
    plan = ClassroomPlan.get_by_id(plan_id)
    if not plan:
        abort(404)

    comment = (request.form.get('comment') or '').strip()
    if not comment:
        flash('El comentario no puede estar vacío.', 'danger')
        return redirect(url_for('plans.review_view', plan_id=plan_id))

    PlanReview.create(
        plan_id=plan_id,
        reviewer_id=current_user.id,
        action='comentario',
        comment=comment,
    )
    flash('Comentario agregado.', 'success')
    return redirect(url_for('plans.review_view', plan_id=plan_id))


# ============================================================
# ÁREAS
# ============================================================
@plans_bp.route('/<int:plan_id>/areas/add', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
@plan_access_required('edit')
def add_area(plan_id, plan):
    area_id = PlanArea.create(plan_id, {
        'formation_area': request.form.get('formation_area'),
        'pedagogical_approach': request.form.get('pedagogical_approach'),
        'curricular_components': request.form.get('curricular_components'),
        'essential_themes': request.form.get('essential_themes'),
        'contents': request.form.get('contents'),
        'expected_learning': request.form.get('expected_learning'),
        'tasks': request.form.get('tasks'),
    })

    if area_id:
        flash('Área agregada.', 'success')
    else:
        flash('Error al agregar el área.', 'danger')

    return redirect(url_for('plans.edit_view', plan_id=plan_id))


@plans_bp.route('/areas/<int:area_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('maestro', 'directivo')
@area_access_required('edit')
def edit_area(area_id, area, plan):
    if request.method == 'POST':
        data = {
            'formation_area': request.form.get('formation_area'),
            'pedagogical_approach': request.form.get('pedagogical_approach'),
            'curricular_components': request.form.get('curricular_components'),
            'essential_themes': request.form.get('essential_themes'),
            'contents': request.form.get('contents'),
            'expected_learning': request.form.get('expected_learning'),
            'tasks': request.form.get('tasks'),
        }
        if PlanArea.update(area_id, data):
            flash('Área actualizada.', 'success')
            return redirect(url_for('plans.edit_view', plan_id=plan['id']))
        flash('Error al actualizar el área.', 'danger')

    return render_template('plans/area_edit.html',
                           area=area,
                           plan=plan)


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
        'title': request.form.get('title'),
        'description': request.form.get('description'),
        'strategy': request.form.get('strategy'),
        'indicators': request.form.get('indicators'),
        'resources': request.form.get('resources'),
        'evaluation_technique': request.form.get('evaluation_technique'),
        'evaluation_instrument': request.form.get('evaluation_instrument'),
        'curricular_emphasis': request.form.get('curricular_emphasis'),
        'start_datetime': request.form.get('start_datetime') or None,
        'end_datetime': request.form.get('end_datetime') or None,
        'location': request.form.get('location'),
    })

    if activity_id:
        flash('Actividad agregada.', 'success')
    else:
        flash('Error al agregar la actividad.', 'danger')

    return redirect(url_for('plans.edit_view', plan_id=plan['id']))


@plans_bp.route('/activities/<int:activity_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('maestro', 'directivo')
@activity_access_required('edit')
def edit_activity(activity_id, activity, area, plan):
    if request.method == 'POST':
        data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'strategy': request.form.get('strategy'),
            'indicators': request.form.get('indicators'),
            'resources': request.form.get('resources'),
            'evaluation_technique': request.form.get('evaluation_technique'),
            'evaluation_instrument': request.form.get('evaluation_instrument'),
            'curricular_emphasis': request.form.get('curricular_emphasis'),
            'start_datetime': request.form.get('start_datetime') or None,
            'end_datetime': request.form.get('end_datetime') or None,
            'location': request.form.get('location'),
        }
        if PlanActivity.update(activity_id, data):
            flash('Actividad actualizada.', 'success')
            return redirect(url_for('plans.edit_view', plan_id=plan['id']))
        flash('Error al actualizar la actividad.', 'danger')

    return render_template('plans/activity_edit.html',
                           activity=activity,
                           area=area,
                           plan=plan)


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