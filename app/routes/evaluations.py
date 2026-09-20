"""
Rutas de evaluaciones.

Aplican autorización RBAC+ABAC (SEG-005 y SEG-006):
- Directivo/Secretario: gestión completa.
- Maestro: solo sobre estudiantes de sus cursos.
- Maestro especialista: toda la matrícula.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.models.evaluation import EvaluationArea, EvaluationPeriod, Evaluation
from app.models.teacher import Teacher
from app.utils.decorators import role_required

from app.security import Permission
from app.security.helpers import get_student_or_403

evaluations_bp = Blueprint('evaluations', __name__, url_prefix='/evaluations')


# ============================================================
# CONFIGURACIÓN (solo directivo)
# ============================================================
@evaluations_bp.route('/areas')
@login_required
@role_required('directivo')
def areas_list():
    areas = EvaluationArea.get_all(only_active=False)
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


@evaluations_bp.route('/periods')
@login_required
@role_required('directivo')
def periods_list():
    periods = EvaluationPeriod.get_all()
    return render_template('evaluations/periods_list.html', periods=periods)


@evaluations_bp.route('/periods/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo')
def period_create():
    if request.method == 'POST':
        EvaluationPeriod.create({
            'name':          request.form['name'],
            'academic_year': request.form['academic_year'],
            'start_date':    request.form.get('start_date'),
            'end_date':      request.form.get('end_date'),
            'sort_order':    int(request.form.get('sort_order', 0)),
        })
        flash('Periodo creado.', 'success')
        return redirect(url_for('evaluations.periods_list'))
    return render_template('evaluations/period_form.html')


# ============================================================
# REGISTRO DE EVALUACIONES
# ============================================================
@evaluations_bp.route('/record/<int:student_id>', methods=['GET', 'POST'])
@login_required
@role_required('maestro', 'directivo', 'secretario')
def record(student_id):
    # 🔒 SEG-005 + SEG-006: valida acceso al estudiante.
    # Un maestro solo puede registrar evaluaciones de sus estudiantes.
    student = get_student_or_403(student_id, Permission.EVALUATION_CREATE)

    teacher = Teacher.get_by_user_id(current_user.id)
    areas = EvaluationArea.get_all()
    periods = EvaluationPeriod.get_all()

    if request.method == 'POST':
        # Validación de entrada: period_id obligatorio
        period_id = request.form.get('period_id')
        if not period_id:
            flash('Debe seleccionar un periodo de evaluación.', 'danger')
            return redirect(url_for('evaluations.record', student_id=student_id))

        # 🔒 SEG-006: el usuario es responsable de lo que registra.
        # Si no tiene teacher vinculado (ej: directivo sin perfil docente),
        # no se inventa una atribución ficticia.
        responsible_teacher_id = teacher['id'] if teacher else None
        if responsible_teacher_id is None and current_user.role == 'maestro':
            flash('Tu usuario no está vinculado a un docente. Contacta al directivo.', 'danger')
            return redirect(url_for('main.dashboard'))

        saved = 0
        for area in areas:
            literal = request.form.get(f'literal_{area["id"]}')
            description = request.form.get(f'description_{area["id"]}')
            recommendations = request.form.get(f'recommendations_{area["id"]}')

            # Solo se guarda si el literal está presente (permite evaluar
            # solo algunas áreas por periodo).
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