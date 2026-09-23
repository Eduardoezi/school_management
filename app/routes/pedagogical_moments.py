"""
Administración del catálogo de momentos pedagógicos (lapsos).

Solo el directivo puede crear/editar/desactivar.
Todos los roles autenticados pueden listar los activos (para usar en selects).
"""

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, abort
)
from flask_login import login_required

from app.models.pedagogical_moment import PedagogicalMoment
from app.utils.decorators import role_required


moments_bp = Blueprint(
    'pedagogical_moments',
    __name__,
    url_prefix='/admin/pedagogical-moments'
)


@moments_bp.route('/')
@login_required
@role_required('directivo')
def list_view():
    moments = PedagogicalMoment.get_all(only_active=False)

    # Adjuntar cuántos períodos usan cada momento
    for m in moments:
        m['periods_count'] = PedagogicalMoment.count_periods_using(m['id'])

    return render_template('admin/pedagogical_moments/list.html',
                           moments=moments)


@moments_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo')
def create_view():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        sort_order = request.form.get('sort_order', type=int) or 0

        if not name:
            flash('El nombre es obligatorio.', 'danger')
            return render_template('admin/pedagogical_moments/form.html',
                                   form=request.form)

        if len(name) > 80:
            flash('El nombre no puede superar 80 caracteres.', 'danger')
            return render_template('admin/pedagogical_moments/form.html',
                                   form=request.form)

        moment_id = PedagogicalMoment.create(name, sort_order)
        if moment_id:
            flash(f'Momento "{name}" creado.', 'success')
            return redirect(url_for('pedagogical_moments.list_view'))
        flash('Error al crear. ¿Ya existe un momento con ese nombre?', 'danger')

    return render_template('admin/pedagogical_moments/form.html', form={})


@moments_bp.route('/<int:moment_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('directivo')
def edit_view(moment_id):
    moment = PedagogicalMoment.get_by_id(moment_id)
    if not moment:
        abort(404)

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        sort_order = request.form.get('sort_order', type=int) or 0
        is_active = request.form.get('is_active') == 'on'

        if not name:
            flash('El nombre es obligatorio.', 'danger')
        elif len(name) > 80:
            flash('El nombre no puede superar 80 caracteres.', 'danger')
        else:
            # Si intentan desactivar un momento que ya tiene períodos,
            # advertirles.
            if not is_active:
                count = PedagogicalMoment.count_periods_using(moment_id)
                if count > 0:
                    flash(
                        f'No puedes desactivar este momento: {count} período(s) '
                        f'lo están usando. Elimina o cambia esos períodos primero.',
                        'danger'
                    )
                    return redirect(url_for('pedagogical_moments.edit_view',
                                            moment_id=moment_id))

            if PedagogicalMoment.update(moment_id, name, sort_order, is_active):
                flash('Momento actualizado.', 'success')
                return redirect(url_for('pedagogical_moments.list_view'))
            flash('Error al actualizar.', 'danger')

    return render_template('admin/pedagogical_moments/form.html',
                           moment=moment, form=request.form)


@moments_bp.route('/<int:moment_id>/toggle', methods=['POST'])
@login_required
@role_required('directivo')
def toggle_view(moment_id):
    moment = PedagogicalMoment.get_by_id(moment_id)
    if not moment:
        abort(404)

    new_state = not bool(moment['is_active'])

    # Si quieren desactivar y tiene períodos, bloquear
    if not new_state:
        count = PedagogicalMoment.count_periods_using(moment_id)
        if count > 0:
            flash(
                f'No puedes desactivar "{moment["name"]}": {count} período(s) '
                f'lo están usando.',
                'danger'
            )
            return redirect(url_for('pedagogical_moments.list_view'))

    if PedagogicalMoment.soft_toggle(moment_id, new_state):
        flash(
            f'Momento "{moment["name"]}" {"activado" if new_state else "desactivado"}.',
            'success'
        )
    else:
        flash('Error al cambiar el estado.', 'danger')

    return redirect(url_for('pedagogical_moments.list_view'))