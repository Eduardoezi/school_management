from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models.school_schedule import SchoolSchedule
from app.utils.decorators import role_required
from app.utils.db import get_db_connection

schedule_bp = Blueprint('schedule', __name__, url_prefix='/schedule')

@schedule_bp.route('/')
@login_required
@role_required('directivo', 'secretario')
def list_view():
    schedules = SchoolSchedule.get_all()
    return render_template('schedule/list.html', schedules=schedules)

@schedule_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def create_view():
    if request.method == 'POST':
        data = {
            'code_schedules': request.form.get('code_schedules'),
            'day_of_week': request.form['day_of_week'],
            'start_time': request.form['start_time'],
            'end_time': request.form['end_time']
        }
        if SchoolSchedule.create(data):
            flash('Horario creado.', 'success')
            return redirect(url_for('schedule.list_view'))
        flash('Error al crear horario.', 'danger')
    return render_template('schedule/form.html')

@schedule_bp.route('/<int:schedule_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def edit_view(schedule_id):
    schedule = SchoolSchedule.get_by_id(schedule_id)
    if not schedule:
        flash('Horario no encontrado.', 'danger')
        return redirect(url_for('schedule.list_view'))
    if request.method == 'POST':
        data = {
            'code_schedules': request.form.get('code_schedules'),
            'day_of_week': request.form['day_of_week'],
            'start_time': request.form['start_time'],
            'end_time': request.form['end_time']
        }
        if SchoolSchedule.update(schedule_id, data):
            flash('Horario actualizado.', 'success')
            return redirect(url_for('schedule.list_view'))
        flash('Error al actualizar.', 'danger')
    return render_template('schedule/form.html', schedule=schedule)

@schedule_bp.route('/<int:schedule_id>/delete')
@login_required
@role_required('directivo')
def delete_view(schedule_id):
    if SchoolSchedule.delete(schedule_id):
        flash('Horario eliminado.', 'success')
    else:
        flash('Error al eliminar.', 'danger')
    return redirect(url_for('schedule.list_view'))

@staticmethod
def get_by_day(day_of_week):
    """Devuelve el horario del día (1=Lunes...7=Domingo)."""
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM school_schedules 
        WHERE day_of_week = %s ORDER BY start_time LIMIT 1
    """, (day_of_week,))
    row = cursor.fetchone()
    cursor.close(); conn.close()
    return row