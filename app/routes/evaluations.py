"""
Rutas de evaluaciones.

Aplican autorización RBAC+ABAC (SEG-005 y SEG-006):
- Directivo/Secretario: gestión completa.
- Maestro: solo sobre estudiantes de sus cursos.
- Maestro especialista: toda la matrícula.

Incluye:
    - Configuración de áreas y períodos (directivo).
    - Registro de evaluaciones de período (L / EP / PL).
    - Histórico por estudiante.
    - Registro anecdótico por actividad del plan de aula.
"""

from itertools import groupby
from operator import itemgetter

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, abort,
)
from flask_login import login_required, current_user

from app.models.evaluation import EvaluationArea, EvaluationPeriod, Evaluation
from app.models.teacher import Teacher
from app.models.student import Student
from app.models.pedagogical_moment import PedagogicalMoment
from app.models.anecdotal_record import AnecdotalRecord
from app.utils.decorators import role_required
from app.utils.db import get_db_connection

from app.security import Permission
from app.security.helpers import get_student_or_403


evaluations_bp = Blueprint('evaluations', __name__, url_prefix='/evaluations')

# ============================================================
# ÍNDICE DE EVALUACIONES
# Lista de estudiantes para elegir cuál evaluar.
# Respeta el rol: maestro ve sus cursos, especialista ve todos,
# directivo/secretario ven todos.
# ============================================================
@evaluations_bp.route('/')
@login_required
@role_required('maestro', 'directivo', 'secretario')
def index():
    if current_user.role == 'maestro':
        teacher = Teacher.get_by_user_id(current_user.id)
        if not teacher:
            flash('Tu usuario no está vinculado a un docente.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.models.staff_detail import StaffDetail
        details = StaffDetail.get_by_teacher(teacher['id'])
        is_specialist = bool(
            details
            and details.get('specialist_type')
            and details['specialist_type'] != 'ninguno'
        )

        if is_specialist:
            students = Student.get_all_with_details(status='activo')
            view_mode = 'specialist'
        else:
            students = Student.get_by_teacher_course(teacher['id'])
            view_mode = 'teacher'
    else:
        view_mode = request.args.get('view', 'enrolled')
        if view_mode == 'all':
            students = Student.get_all_with_details(status=None)
        else:
            students = Student.get_all_with_details(status='activo')

    return render_template('evaluations/index.html',
                           students=students,
                           view_mode=view_mode)

# ============================================================
# CONFIGURACIÓN DE ÁREAS (solo directivo)
# ============================================================
@evaluations_bp.route('/areas')
@login_required
@role_required('directivo')
def areas_list():
    areas = EvaluationArea.get_all(only_active=False)
    # Enriquecer con conteos de uso
    for a in areas:
        a['plans_count'] = EvaluationArea.count_plans_using(a['id'])
        a['evaluations_count'] = EvaluationArea.count_evaluations_using(a['id'])
    return render_template('evaluations/areas_list.html', areas=areas)


@evaluations_bp.route('/areas/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo')
def area_create():
    if request.method == 'POST':
        EvaluationArea.create({
            'name':        request.form['name'],
            'description': request.form.get('description'),
            'sort_order':  int(request.form.get('sort_order', 0)),
        })
        flash('Área creada.', 'success')
        return redirect(url_for('evaluations.areas_list'))
    return render_template('evaluations/area_form.html')


# ============================================================
# CONFIGURACIÓN DE PERÍODOS
# ============================================================
@evaluations_bp.route('/periods')
@login_required
def periods_list():
    periods = EvaluationPeriod.get_all()

    periods_sorted = sorted(
        periods,
        key=lambda p: (p.get('moment_sort_order') or 0, p.get('sort_order') or 0)
    )
    grouped = [
        {'moment_name': name, 'periods': list(items)}
        for name, items in groupby(periods_sorted,
                                   key=itemgetter('moment_name'))
    ]
    return render_template(
        'evaluations/periods_list.html',
        periods=periods,
        grouped=grouped,
    )


@evaluations_bp.route('/periods/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo')
def period_create():
    moments = PedagogicalMoment.get_all(only_active=True)

    if request.method == 'POST':
        moment_id = request.form.get('pedagogical_moment_id', type=int)
        academic_year = (request.form.get('academic_year') or '').strip()

        errors = []
        if not moment_id:
            errors.append('Debes seleccionar un momento pedagógico.')
        if not academic_year:
            errors.append('El año académico es obligatorio.')

        moment = PedagogicalMoment.get_by_id(moment_id) if moment_id else None
        if moment_id and not moment:
            errors.append('El momento pedagógico seleccionado no existe.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template(
                'evaluations/period_form.html',
                moments=moments,
                form=request.form,
            )

        EvaluationPeriod.create({
            'name':                   moment['name'],
            'pedagogical_moment_id':  moment['id'],
            'academic_year':          academic_year,
            'start_date':             request.form.get('start_date'),
            'end_date':               request.form.get('end_date'),
            'sort_order':             int(request.form.get('sort_order', 0)),
        })
        flash(f'Periodo "{moment["name"]}" creado.', 'success')
        return redirect(url_for('evaluations.periods_list'))

    return render_template('evaluations/period_form.html',
                           moments=moments,
                           form={})


# ============================================================
# REGISTRO DE EVALUACIONES DE PERÍODO
# ============================================================
@evaluations_bp.route('/record/<int:student_id>', methods=['GET', 'POST'])
@login_required
@role_required('maestro', 'directivo', 'secretario')
def record(student_id):
    # 🔒 SEG-005 + SEG-006: valida acceso al estudiante.
    student = get_student_or_403(student_id, Permission.EVALUATION_CREATE)

    teacher = Teacher.get_by_user_id(current_user.id)
    areas = EvaluationArea.get_all()
    periods = EvaluationPeriod.get_all()

    if request.method == 'POST':
        period_id = request.form.get('period_id')
        if not period_id:
            flash('Debe seleccionar un periodo de evaluación.', 'danger')
            return redirect(url_for('evaluations.record', student_id=student_id))

        # 🔒 SEG-006: el usuario es responsable de lo que registra.
        responsible_teacher_id = teacher['id'] if teacher else None
        if responsible_teacher_id is None and current_user.role == 'maestro':
            flash('Tu usuario no está vinculado a un docente. '
                  'Contacta al directivo.', 'danger')
            return redirect(url_for('main.dashboard'))

        saved = 0
        for area in areas:
            literal = request.form.get(f'literal_{area["id"]}')
            description = request.form.get(f'description_{area["id"]}')
            recommendations = request.form.get(f'recommendations_{area["id"]}')

            if literal and description:
                ok = Evaluation.save({
                    'student_school_id': student['school_id'],
                    'area_id':           area['id'],
                    'period_id':         period_id,
                    'literal':           literal,
                    'description':       description,
                    'recommendations':   recommendations,
                    'teacher_id':        responsible_teacher_id,
                })
                if ok:
                    saved += 1

        flash(f'Se guardaron {saved} evaluaciones.', 'success')
        return redirect(url_for('evaluations.history', student_id=student_id))

    return render_template(
        'evaluations/record.html',
        student=student,
        areas=areas,
        periods=periods,
    )


# ============================================================
# HISTÓRICO
# ============================================================
@evaluations_bp.route('/history/<int:student_id>')
@login_required
@role_required('maestro', 'directivo', 'secretario')
def history(student_id):
    # 🔒 SEG-005: valida acceso al estudiante antes de exponer el histórico.
    student = get_student_or_403(student_id, Permission.STUDENT_VIEW_HISTORY)

    grouped = Evaluation.get_history_grouped(student['school_id'])
    return render_template(
        'evaluations/history.html',
        student=student,
        grouped=grouped,
    )


# ============================================================
# REGISTRO ANECDÓTICO
# ============================================================
@evaluations_bp.route('/anecdotal/student/<int:student_id>')
@login_required
@role_required('maestro', 'directivo', 'secretario')
def anecdotal_list_by_student(student_id):
    """Todas las anécdotas de un estudiante."""
    student = get_student_or_403(student_id, Permission.STUDENT_VIEW_HISTORY)

    # Si es maestro, solo sus propias anécdotas
    teacher = Teacher.get_by_user_id(current_user.id)
    filter_teacher_id = None
    if current_user.role == 'maestro':
        if not teacher:
            flash('Tu usuario no está vinculado a un docente.', 'danger')
            return redirect(url_for('main.dashboard'))
        filter_teacher_id = teacher['id']

    records = AnecdotalRecord.get_by_student(
        student['school_id'],
        teacher_id=filter_teacher_id,
    )

    return render_template(
        'evaluations/anecdotal_list.html',
        student=student,
        records=records,
        filter_by_teacher=filter_teacher_id is not None,
    )


@evaluations_bp.route('/anecdotal/student/<int:student_id>/new',
                      methods=['GET', 'POST'])
@login_required
@role_required('maestro', 'directivo')
def anecdotal_create(student_id):
    """Registrar una nueva anécdota."""
    student = get_student_or_403(student_id, Permission.EVALUATION_CREATE)

    teacher = Teacher.get_by_user_id(current_user.id)
    if current_user.role == 'maestro' and not teacher:
        flash('Tu usuario no está vinculado a un docente.', 'danger')
        return redirect(url_for('main.dashboard'))

    activities = _get_available_activities(teacher['id'] if teacher else None)

    if request.method == 'POST':
        observed_at = (request.form.get('observed_at') or '').strip()
        observation = (request.form.get('observation') or '').strip()
        recommendation = (request.form.get('recommendation') or '').strip()
        activity_id = request.form.get('plan_activity_id', type=int)

        errors = []
        if not observed_at:
            errors.append('La fecha de observación es obligatoria.')
        if not observation:
            errors.append('La observación es obligatoria.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template(
                'evaluations/anecdotal_form.html',
                student=student,
                activities=activities,
                form=request.form,
            )

        teacher_id = teacher['id'] if teacher else _get_any_teacher_id()
        if not teacher_id:
            flash('No hay un docente disponible para asociar la anécdota.',
                  'danger')
            return redirect(url_for('evaluations.anecdotal_list_by_student',
                                    student_id=student_id))

        record_id = AnecdotalRecord.create({
            'student_school_id': student['school_id'],
            'plan_activity_id':  activity_id,
            'observed_at':       observed_at,
            'observation':       observation,
            'recommendation':    recommendation,
            'teacher_id':        teacher_id,
        })

        if record_id:
            flash('Anécdota registrada.', 'success')
            return redirect(url_for('evaluations.anecdotal_list_by_student',
                                    student_id=student_id))
        flash('Error al registrar la anécdota.', 'danger')

    return render_template(
        'evaluations/anecdotal_form.html',
        student=student,
        activities=activities,
        form={},
    )


@evaluations_bp.route('/anecdotal/<int:record_id>/edit',
                      methods=['GET', 'POST'])
@login_required
@role_required('maestro', 'directivo')
def anecdotal_edit(record_id):
    """Editar una anécdota existente."""
    record = AnecdotalRecord.get_by_id(record_id)
    if not record:
        abort(404)

    # Permisos: el docente autor o el directivo
    teacher = Teacher.get_by_user_id(current_user.id)
    if current_user.role == 'maestro':
        if not teacher or record['teacher_id'] != teacher['id']:
            abort(403)

    student = Student.get_by_id(record['student_school_id'])
    if not student:
        student = _get_student_by_school_id(record['student_school_id'])

    activities = _get_available_activities(teacher['id'] if teacher else None)

    if request.method == 'POST':
        observed_at = (request.form.get('observed_at') or '').strip()
        observation = (request.form.get('observation') or '').strip()
        recommendation = (request.form.get('recommendation') or '').strip()
        activity_id = request.form.get('plan_activity_id', type=int)

        if not observed_at or not observation:
            flash('Fecha y observación son obligatorias.', 'danger')
        else:
            if AnecdotalRecord.update(record_id, {
                'observed_at':      observed_at,
                'observation':      observation,
                'recommendation':   recommendation,
                'plan_activity_id': activity_id,
            }):
                flash('Anécdota actualizada.', 'success')
                return redirect(url_for(
                    'evaluations.anecdotal_list_by_student',
                    student_id=student['id'] if student else None,
                ))
            flash('Error al actualizar.', 'danger')

    return render_template(
        'evaluations/anecdotal_form.html',
        student=student,
        record=record,
        activities=activities,
        form=request.form,
    )


@evaluations_bp.route('/anecdotal/<int:record_id>/delete', methods=['POST'])
@login_required
@role_required('maestro', 'directivo')
def anecdotal_delete(record_id):
    """Eliminar una anécdota."""
    record = AnecdotalRecord.get_by_id(record_id)
    if not record:
        abort(404)

    teacher = Teacher.get_by_user_id(current_user.id)
    if current_user.role == 'maestro':
        if not teacher or record['teacher_id'] != teacher['id']:
            abort(403)

    student = _get_student_by_school_id(record['student_school_id'])

    if AnecdotalRecord.delete(record_id):
        flash('Anécdota eliminada.', 'success')
    else:
        flash('Error al eliminar.', 'danger')

    if student:
        return redirect(url_for('evaluations.anecdotal_list_by_student',
                                student_id=student['id']))
    return redirect(url_for('students.list_view'))


# ============================================================
# HELPERS INTERNOS
# ============================================================
def _get_available_activities(teacher_id):
    """
    Devuelve las actividades del plan del docente para el año escolar activo.
    Si teacher_id es None, devuelve todas las actividades.
    """
    conn = get_db_connection()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT pa.id,
                   pa.title,
                   pa.start_datetime,
                   area.formation_area,
                   area.development_area_id,
                   ea.name AS development_area_name,
                   plan.id AS plan_id,
                   plan.learning_project_title AS plan_title,
                   plan.status AS plan_status
              FROM plan_activities pa
              JOIN plan_areas       area ON pa.plan_area_id = area.id
              LEFT JOIN evaluation_areas ea ON ea.id = area.development_area_id
              JOIN classroom_plans  plan ON area.plan_id = plan.id
             WHERE plan.deleted_at IS NULL
               AND plan.status IN ('aprobado', 'publicado')
        """
        params = []

        if teacher_id is not None:
            sql += " AND plan.teacher_id = %s"
            params.append(teacher_id)

        sql += " ORDER BY plan.id DESC, area.sort_order, pa.sort_order"

        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def _get_any_teacher_id():
    """Fallback: el primer docente activo."""
    conn = get_db_connection()
    if not conn:
        return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM teachers WHERE active = 1 LIMIT 1")
        row = cursor.fetchone()
        return int(row[0]) if row else None
    finally:
        cursor.close()
        conn.close()


def _get_student_by_school_id(school_id):
    """Busca un estudiante por su cédula escolar."""
    conn = get_db_connection()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM students WHERE school_id = %s LIMIT 1",
            (school_id,)
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()