from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models.student import Student
from app.models.student_detail import StudentDetail
from app.models.family_member import FamilyMember
from app.models.medical_info import MedicalInfo
from app.models.socioeconomic_info import SocioeconomicInfo
from app.models.enrollment import Enrollment
from app.models.evaluation import Evaluation
from app.models.representative import Representative
from app.utils.decorators import role_required

student_profile_bp = Blueprint('student_profile', __name__,
                                url_prefix='/students/<int:student_id>/profile')


# ============================================================
# VISTA PRINCIPAL DEL PERFIL
# ============================================================
@student_profile_bp.route('/')
@login_required
@role_required('directivo', 'secretario', 'maestro')
def view(student_id):
    student = Student.get_by_id(student_id)
    if not student:
        flash('Estudiante no encontrado.', 'danger')
        return redirect(url_for('students.list_view'))

    details = StudentDetail.get_by_student(student_id)
    family = FamilyMember.get_by_student(student_id)
    medical = MedicalInfo.get_by_student(student_id)
    socioeconomic = SocioeconomicInfo.get_by_student(student_id)
    enrollments = Enrollment.get_by_student(student_id)

    # Representante destacado
    representative = None
    if student.get('representative_cedula'):
        representative = Representative.get_by_cedula(student['representative_cedula'])

    return render_template('students/profile/view.html',
                           student=student,
                           details=details,
                           family=family,
                           medical=medical,
                           socioeconomic=socioeconomic,
                           enrollments=enrollments,
                           representative=representative)


# ============================================================
# DATOS PERSONALES
# ============================================================
@student_profile_bp.route('/edit-personal', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def edit_personal(student_id):
    student = Student.get_by_id(student_id)
    if not student:
        flash('Estudiante no encontrado.', 'danger')
        return redirect(url_for('students.list_view'))

    details = StudentDetail.get_by_student(student_id)

    if request.method == 'POST':
        data = {
            'sex': request.form.get('sex') or None,
            'birth_place': request.form.get('birth_place'),
            'laterality': request.form.get('laterality') or None,
            'shirt_size': request.form.get('shirt_size'),
            'pants_size': request.form.get('pants_size'),
            'shoe_size': request.form.get('shoe_size'),
            'contact_phone': request.form.get('contact_phone'),
            'address': request.form.get('address'),
            'municipality': request.form.get('municipality'),
            'parish': request.form.get('parish'),
            'state': request.form.get('state')
        }
        if StudentDetail.save(student_id, data):
            flash('Datos personales actualizados.', 'success')
            return redirect(url_for('student_profile.view', student_id=student_id))
        flash('Error al guardar.', 'danger')

    return render_template('students/profile/edit_personal.html',
                           student=student, details=details)


# ============================================================
# FAMILIA
# ============================================================
@student_profile_bp.route('/family/add', methods=['POST'])
@login_required
@role_required('directivo', 'secretario')
def family_add(student_id):
    data = _extract_family_form(request.form)
    if FamilyMember.create(student_id, data):
        flash('Familiar agregado.', 'success')
    else:
        flash('Error al agregar familiar.', 'danger')
    return redirect(url_for('student_profile.view', student_id=student_id))


@student_profile_bp.route('/family/<int:member_id>/edit', methods=['POST'])
@login_required
@role_required('directivo', 'secretario')
def family_edit(student_id, member_id):
    data = _extract_family_form(request.form)
    if FamilyMember.update(member_id, data):
        flash('Familiar actualizado.', 'success')
    else:
        flash('Error al actualizar.', 'danger')
    return redirect(url_for('student_profile.view', student_id=student_id))


@student_profile_bp.route('/family/<int:member_id>/delete', methods=['POST'])
@login_required
@role_required('directivo', 'secretario')
def family_delete(student_id, member_id):
    if FamilyMember.delete(member_id):
        flash('Familiar eliminado.', 'success')
    else:
        flash('Error al eliminar.', 'danger')
    return redirect(url_for('student_profile.view', student_id=student_id))


def _extract_family_form(form):
    return {
        'role': form['role'],
        'first_name': form['first_name'],
        'last_name': form['last_name'],
        'cedula_id': form.get('cedula_id'),
        'age': form.get('age') or None,
        'marital_status': form.get('marital_status'),
        'birth_date': form.get('birth_date') or None,
        'birth_place': form.get('birth_place'),
        'education_level': form.get('education_level'),
        'profession': form.get('profession'),
        'position': form.get('position'),
        'occupation': form.get('occupation'),
        'address': form.get('address'),
        'phone': form.get('phone'),
        'email': form.get('email')
    }


# ============================================================
# FICHA MÉDICA
# ============================================================
@student_profile_bp.route('/medical', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def medical_edit(student_id):
    student = Student.get_by_id(student_id)
    if not student:
        flash('Estudiante no encontrado.', 'danger')
        return redirect(url_for('students.list_view'))

    if request.method == 'POST':
        data = {k: request.form.get(k) for k in [
            'vaccine_bcg', 'vaccine_polio', 'vaccine_triple',
            'vaccine_measles', 'vaccine_rubella', 'vaccine_yellow_fever',
            'vaccine_toxoid', 'vaccine_covid_1', 'vaccine_covid_2',
            'vaccine_covid_3', 'vaccine_others', 'allergies',
            'chronic_conditions', 'convulsions', 'current_medication',
            'medical_attention', 'upen_attention', 'fever_protocol',
            'report_medical', 'report_psychological', 'report_neurological'
        ]}
        if MedicalInfo.save(student_id, data):
            flash('Información médica actualizada.', 'success')
            return redirect(url_for('student_profile.view', student_id=student_id))
        flash('Error al guardar.', 'danger')

    medical = MedicalInfo.get_by_student(student_id)
    return render_template('students/profile/edit_medical.html',
                           student=student, medical=medical)


# ============================================================
# ESTUDIO SOCIOECONÓMICO
# ============================================================
@student_profile_bp.route('/socioeconomic', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def socioeconomic_edit(student_id):
    student = Student.get_by_id(student_id)
    if not student:
        flash('Estudiante no encontrado.', 'danger')
        return redirect(url_for('students.list_view'))

    if request.method == 'POST':
        data = {
            'lives_with': request.form.get('lives_with'),
            'other_family_members': request.form.get('other_family_members'),
            'working_members': request.form.get('working_members') or None,
            'monthly_income': request.form.get('monthly_income') or None,
            'household_members': request.form.get('household_members') or None,
            'housing_type': request.form.get('housing_type'),
            'rooms_count': request.form.get('rooms_count') or None,
            'housing_condition': request.form.get('housing_condition'),
            'housing_infrastructure': request.form.get('housing_infrastructure')
        }
        if SocioeconomicInfo.save(student_id, data):
            flash('Estudio socioeconómico actualizado.', 'success')
            return redirect(url_for('student_profile.view', student_id=student_id))
        flash('Error al guardar.', 'danger')

    socioeconomic = SocioeconomicInfo.get_by_student(student_id)
    return render_template('students/profile/edit_socioeconomic.html',
                           student=student, socioeconomic=socioeconomic)