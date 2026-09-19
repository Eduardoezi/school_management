from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, abort
)
from flask_login import login_required

from app.models.school_schedule import SchoolSchedule
from app.utils.decorators import role_required

schedule_bp = Blueprint('schedule', __name__, url_prefix='/schedule')


# ---------- LISTAR ----------
@schedule_bp.route('/')
@login_required
@role_required('directivo', 'secretario')
def list_view():
    schedules = SchoolSchedule.get_all()
    return render_template('schedule/list.html', schedules=schedules)


# ---------- CREAR ----------
@schedule_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def create_view():
    if request.method == 'POST':
        data = {
            'code_schedules': request.form.get('code_schedules'),
            'day_of_week':    request.form['day_of_week'],
            'start_time':     request.form['start_time'],
            'end_time':       request.form['end_time'],
        }
        if SchoolSchedule.create(data):
            flash('Horario creado.', 'success')
            return redirect(url_for('schedule.list_view'))
        flash('Error al crear horario.', 'danger')

    return render_template('schedule/form.html')


# ---------- EDITAR ----------
@schedule_bp.route('/<int:schedule_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def edit_view(schedule_id):
    schedule = SchoolSchedule.get_by_id(schedule_id)
    if not schedule:
        abort(404)

    if request.method == 'POST':
        data = {
            'code_schedules': request.form.get('code_schedules'),
            'day_of_week':    request.form['day_of_week'],
            'start_time':     request.form['start_time'],
            'end_time':       request.form['end_time'],
        }
        if SchoolSchedule.update(schedule_id, data):
            flash('Horario actualizado.', 'success')
            return redirect(url_for('schedule.list_view'))
        flash('Error al actualizar.', 'danger')

    return render_template('schedule/form.html', schedule=schedule)


# ---------- ELIMINAR: paso 1 (confirmación, GET) ----------
@schedule_bp.route('/<int:schedule_id>/delete', methods=['GET'])
@login_required
@role_required('directivo')
def confirm_delete(schedule_id):
    schedule = SchoolSchedule.get_by_id(schedule_id)
    if not schedule:
        abort(404)

    return render_template(
        '_confirm_delete.html',
        title='¿Eliminar este horario?',
        message='El horario dejará de estar disponible para el kiosco de asistencia.',
        details=[
            ('Código', schedule.get('code_schedules')),
            ('Día',    schedule.get('day_of_week')),
            ('Inicio', schedule.get('start_time')),
            ('Fin',    schedule.get('end_time')),
        ],
        action_url=url_for('schedule.delete', schedule_id=schedule_id),
        cancel_url=url_for('schedule.list_view'),
    )


# ---------- ELIMINAR: paso 2 (ejecución, POST) ----------
@schedule_bp.route('/<int:schedule_id>/delete', methods=['POST'])
@login_required
@role_required('directivo')
def delete(schedule_id):
    if SchoolSchedule.delete(schedule_id):
        flash('Horario eliminado.', 'success')
    else:
        flash('Error al eliminar.', 'danger')
    return redirect(url_for('schedule.list_view'))