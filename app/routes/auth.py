from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app.models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.get_by_username(username)
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        flash('Usuario o contraseña incorrectos', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'maestro')
        # Validar que el rol sea permitido
        if role not in ['directivo', 'secretario', 'maestro']:
            role = 'maestro'
        if not username or not email or not password:
            flash('Todos los campos son obligatorios', 'danger')
            return render_template('register.html')
        user_id = User.create(username, email, password, role)
        if user_id:
            flash('Usuario registrado exitosamente. Inicia sesión.', 'success')
            return redirect(url_for('auth.login'))
        flash('Nombre de usuario o email ya existen', 'danger')
    return render_template('register.html')