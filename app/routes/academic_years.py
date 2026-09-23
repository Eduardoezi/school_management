"""
Blueprint de administración de años escolares.

Solo el directivo puede crear, activar o marcar años como próximos.
Los demás roles pueden consultar el año activo desde la API interna.

Rutas:
    GET  /admin/academic-years               → listado
    GET  /admin/academic-years/new           → formulario de creación
    POST /admin/academic-years/new           → guardar
    POST /admin/academic-years/<id>/activate → activar (desactiva el anterior)
    POST /admin/academic-years/<id>/mark-next → marcar como próximo
    POST /admin/academic-years/<id>/delete   → eliminar (si no tiene dependencias)
"""

from __future__ import annotations

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, abort
)
from flask_login import login_required, current_user

from app.models.academic_year import AcademicYear
from app.utils.decorators import role_required


academic_years_bp = Blueprint(
    'academic_years',
    __name__,
    url_prefix='/admin/academic-years'
)


# ============================================================
# LISTADO
# ============================================================
@academic_years_bp.route('/')
@login_required
@role_required('directivo')
def list_view():
    """Listado completo de años escolares."""
    years = AcademicYear.get_all()
    active = AcademicYear.get_active()
    next_year = AcademicYear.get_next()

    return render_template(
        'admin/academic_years/list.html',
        years=years,
        active=active,
        next_year=next_year,
    )


# ============================================================
# CREAR
# ============================================================
@academic_years_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo')
def create_view():
    if request.method == 'POST':
        name       = (request.form.get('name') or '').strip()
        start_date = (request.form.get('start_date') or '').strip()
        end_date   = (request.form.get('end_date') or '').strip()

        errors = []
        if not name:
            errors.append('El nombre es obligatorio.')
        if not start_date:
            errors.append('La fecha de inicio es obligatoria.')
        if not end_date:
            errors.append('La fecha de fin es obligatoria.')
        if start_date and end_date and start_date >= end_date:
            errors.append('La fecha de inicio debe ser anterior a la de fin.')

        # Verificar nombre único
        if name and any(y['name'] == name for y in AcademicYear.get_all()):
            errors.append(f'Ya existe un año escolar llamado "{name}".')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template(
                'admin/academic_years/form.html',
                form=request.form,
            )

        year_id = AcademicYear.create(name, start_date, end_date)
        if year_id:
            flash(
                f'Año escolar "{name}" creado correctamente. '
                f'Puedes activarlo cuando quieras.',
                'success'
            )
            return redirect(url_for('academic_years.list_view'))

        flash('Error al crear el año escolar.', 'danger')

    return render_template('admin/academic_years/form.html', form={})


# ============================================================
# ACTIVAR
# ============================================================
@academic_years_bp.route('/<int:year_id>/activate', methods=['POST'])
@login_required
@role_required('directivo')
def activate_view(year_id):
    year = AcademicYear.get_by_id(year_id)
    if not year:
        abort(404)

    if year['is_active']:
        flash('Este año ya está activo.', 'info')
        return redirect(url_for('academic_years.list_view'))

    # Confirmación con doble clic (se manda un hidden confirm=yes)
    if request.form.get('confirm') != 'yes':
        flash('Confirma la acción para activar el año.', 'warning')
        return redirect(url_for('academic_years.list_view'))

    if AcademicYear.activate(year_id):
        flash(
            f'Año escolar "{year["name"]}" activado. '
            f'Los nuevos planes se asociarán a este año.',
            'success'
        )
    else:
        flash('Error al activar el año.', 'danger')

    return redirect(url_for('academic_years.list_view'))


# ============================================================
# MARCAR COMO PRÓXIMO
# ============================================================
@academic_years_bp.route('/<int:year_id>/mark-next', methods=['POST'])
@login_required
@role_required('directivo')
def mark_next_view(year_id):
    year = AcademicYear.get_by_id(year_id)
    if not year:
        abort(404)

    if year['is_active']:
        flash(
            'El año activo no puede marcarse como próximo. '
            'Marca otro año y luego activa ese cuando termine el ciclo.',
            'warning'
        )
        return redirect(url_for('academic_years.list_view'))

    if AcademicYear.mark_as_next(year_id):
        flash(
            f'Año escolar "{year["name"]}" marcado como próximo.',
            'success'
        )
    else:
        flash('Error al marcar como próximo.', 'danger')

    return redirect(url_for('academic_years.list_view'))


# ============================================================
# ELIMINAR
# ============================================================
@academic_years_bp.route('/<int:year_id>/delete', methods=['POST'])
@login_required
@role_required('directivo')
def delete_view(year_id):
    year = AcademicYear.get_by_id(year_id)
    if not year:
        abort(404)

    if year['is_active']:
        flash('No puedes eliminar el año activo.', 'danger')
        return redirect(url_for('academic_years.list_view'))

    if AcademicYear.has_dependencies(year_id):
        flash(
            'Este año tiene planes u otros datos asociados. '
            'No se puede eliminar. Archívalo en su lugar.',
            'danger'
        )
        return redirect(url_for('academic_years.list_view'))

    if AcademicYear.delete(year_id):
        flash(f'Año escolar "{year["name"]}" eliminado.', 'success')
    else:
        flash('Error al eliminar el año escolar.', 'danger')

    return redirect(url_for('academic_years.list_view'))