from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.teacher import Teacher
from app.models.staff_detail import StaffDetail
from app.utils.decorators import role_required


teachers_bp = Blueprint('teachers', __name__, url_prefix='/teachers')


# ---------- LISTAR ----------
@teachers_bp.route('/')
@login_required
def list_view():
    show_inactive = request.args.get('inactive') == '1'
    teachers = Teacher.get_all(only_active=not show_inactive)
    return render_template('teachers/list.html',
                           teachers=teachers,
                           show_inactive=show_inactive)


# ---------- CREAR ----------
@teachers_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def create_view():
    if request.method == 'POST':
        # 1. Datos básicos del docente
        teacher_data = {
            'id': request.form['id'].strip(),
            'first_name': request.form['first_name'].strip(),
            'last_name': request.form['last_name'].strip(),
            'email': request.form.get('email', '').strip() or None,
            'hire_date': request.form.get('hire_date') or None,
        }

        # Crear docente
        teacher_id = Teacher.create(teacher_data)
        if not teacher_id:
            flash('Error al registrar. Verifique que la cédula no esté duplicada.', 'danger')
            return render_template('teachers/create.html')

        # 2. Datos laborales extendidos (staff_details)
        staff_data = {
            'codigo_rac':      request.form.get('codigo_rac') or None,
            'cargo':           request.form.get('cargo') or None,
            'staff_type':      request.form.get('staff_type') or None,
            'specialist_type': request.form.get('specialist_type') or 'ninguno',
            'sex':             request.form.get('sex') or None,
            'shirt_size':      request.form.get('shirt_size') or None,
            'pants_size':      request.form.get('pants_size') or None,
            'shoe_size':       request.form.get('shoe_size') or None,
            'academic_hours':  request.form.get('academic_hours') or None,
            'admin_hours':     request.form.get('admin_hours') or None,
            'shift':           request.form.get('shift') or None,
            'worker_status':   request.form.get('worker_status') or None,
            'observations':    request.form.get('observations') or None,
            'specialty':       request.form.get('specialty') or None,
            'birth_city':      request.form.get('birth_city') or None,
            'birth_state':     request.form.get('birth_state') or None,
        }
        StaffDetail.save(teacher_id, staff_data)

        flash(f'Personal registrado exitosamente con cédula {teacher_id}.', 'success')
        return redirect(url_for('staff_profile.view', teacher_id=teacher_id))

    return render_template('teachers/create.html')


# ---------- EDITAR (datos básicos) ----------
@teachers_bp.route('/<int:teacher_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def edit_view(teacher_id):
    teacher = Teacher.get_by_id(teacher_id)
    if not teacher:
        flash('Docente no encontrado.', 'danger')
        return redirect(url_for('teachers.list_view'))

    if request.method == 'POST':
        data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'email': request.form.get('email'),
            'hire_date': request.form.get('hire_date')
        }
        if Teacher.update(teacher_id, data):
            flash('Docente actualizado exitosamente.', 'success')
            return redirect(url_for('teachers.list_view'))
        flash('Error al actualizar docente.', 'danger')

    return render_template('teachers/edit.html', teacher=teacher)


# ---------- DESACTIVAR ----------
@teachers_bp.route('/<int:teacher_id>/deactivate', methods=['POST'])
@login_required
@role_required('directivo')
def deactivate_view(teacher_id):
    teacher = Teacher.get_by_id(teacher_id)
    if not teacher:
        flash('Docente no encontrado.', 'danger')
        return redirect(url_for('teachers.list_view'))

    if Teacher.deactivate(teacher_id):
        flash(f'Docente {teacher["first_name"]} {teacher["last_name"]} desactivado.', 'success')
    else:
        flash('Error al desactivar docente.', 'danger')
    return redirect(url_for('teachers.list_view'))


# ---------- REACTIVAR ----------
@teachers_bp.route('/<int:teacher_id>/reactivate', methods=['POST'])
@login_required
@role_required('directivo')
def reactivate_view(teacher_id):
    if Teacher.reactivate(teacher_id):
        flash('Docente reactivado correctamente.', 'success')
    else:
        flash('Error al reactivar docente.', 'danger')
    return redirect(url_for('teachers.list_view', inactive=1))


# ---------- ELIMINAR (solo si no tiene registros) ----------
@teachers_bp.route('/<int:teacher_id>/delete')
@login_required
@role_required('directivo')
def delete_view(teacher_id):
    ok, error = Teacher.delete_hard(teacher_id)
    if ok:
        flash('Docente eliminado definitivamente.', 'success')
    else:
        flash(f'No se pudo eliminar: {error}. Usa "Desactivar" en su lugar.', 'danger')
    return redirect(url_for('teachers.list_view'))