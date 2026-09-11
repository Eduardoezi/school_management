from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.teacher import Teacher
from app.utils.decorators import role_required

teachers_bp = Blueprint('teachers', __name__, url_prefix='/teachers')

# ---------- LISTAR ----------
@teachers_bp.route('/')
@login_required
def list_view():
    teachers = Teacher.get_all()
    return render_template('teachers/list.html', teachers=teachers)

# ---------- CREAR ----------
@teachers_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def create_view():
    if request.method == 'POST':
        data = {
            'id': request.form['id'],
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'email': request.form.get('email'),
            'hire_date': request.form.get('hire_date')
        }
        if Teacher.create(data):
            flash('Docente registrado exitosamente.', 'success')
            return redirect(url_for('teachers.list_view'))
        else:
            flash('Error al registrar docente. Verifique que la cédula no esté duplicada.', 'danger')
    
    # GET: mostrar formulario
    return render_template('teachers/create.html')

# ---------- EDITAR ----------
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
        else:
            flash('Error al actualizar docente.', 'danger')
    
    # 🔥 CORREGIDO: ahora usa 'edit.html'
    return render_template('teachers/edit.html', teacher=teacher)

# ---------- ELIMINAR ----------
@teachers_bp.route('/<int:teacher_id>/delete')
@login_required
@role_required('directivo')
def delete_view(teacher_id):
    if Teacher.delete(teacher_id):
        flash('Docente eliminado.', 'success')
    else:
        flash('Error al eliminar docente.', 'danger')
    return redirect(url_for('teachers.list_view'))