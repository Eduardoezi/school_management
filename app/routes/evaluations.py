from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.evaluation import EvaluationArea, EvaluationPeriod, Evaluation
from app.models.student import Student
from app.models.teacher import Teacher
from app.utils.decorators import role_required

evaluations_bp = Blueprint('evaluations', __name__, url_prefix='/evaluations')


# ---------- Configuración (solo directivo) ----------
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
            'name': request.form['name'],
            'description': request.form.get('description'),
            'sort_order': int(request.form.get('sort_order', 0))
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
            'name': request.form['name'],
            'academic_year': request.form['academic_year'],
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'sort_order': int(request.form.get('sort_order', 0))
        })
        flash('Periodo creado.', 'success')
        return redirect(url_for('evaluations.periods_list'))
    return render_template('evaluations/period_form.html')


# ---------- Registro de evaluaciones (maestro) ----------
@evaluations_bp.route('/record/<student_id>', methods=['GET', 'POST'])
@login_required
@role_required('maestro', 'directivo', 'secretario')
def record(student_id):
    student = Student.get_by_id(student_id)
    if not student:
        flash('Estudiante no encontrado.', 'danger')
        return redirect(url_for('students.list_view'))

    teacher = Teacher.get_by_user_id(current_user.id)
    areas = EvaluationArea.get_all()
    periods = EvaluationPeriod.get_all()

    if request.method == 'POST':
        period_id = request.form['period_id']
        saved = 0
        for area in areas:
            lit = request.form.get(f'literal_{area["id"]}')
            desc = request.form.get(f'description_{area["id"]}')
            rec = request.form.get(f'recommendations_{area["id"]}')
            if lit and desc:
                ok = Evaluation.save({
                    'student_school_id': student['school_id'],
                    'area_id': area['id'],
                    'period_id': period_id,
                    'literal': lit,
                    'description': desc,
                    'recommendations': rec,
                    'teacher_id': teacher['id'] if teacher else 1
                })
                if ok: saved += 1
        flash(f'Se guardaron {saved} evaluaciones.', 'success')
        return redirect(url_for('evaluations.history', student_id=student_id))

    return render_template('evaluations/record.html',
                           student=student,
                           areas=areas,
                           periods=periods)

# ---------- Histórico del estudiante ----------
@evaluations_bp.route('/history/<student_id>')
@login_required
@role_required('maestro', 'directivo', 'secretario')
def history(student_id):
    student = Student.get_by_id(student_id)
    if not student:
        flash('Estudiante no encontrado.', 'danger')
        return redirect(url_for('students.list_view'))

    grouped = Evaluation.get_history_grouped(student['school_id'])
    return render_template('evaluations/history.html', student=student, grouped=grouped)