# app/routes/webauthn_auth.py
import json
import secrets
import base64

from flask import (
    Blueprint, render_template, request, jsonify,
    session, flash, redirect, url_for, current_app
)
from flask_login import login_required, current_user

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
    UserVerificationRequirement,
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
)
from webauthn.helpers import base64url_to_bytes

from app.models.teacher import Teacher
from app.models.webauthn_credential import WebAuthnCredential
from app.models.teacher_attendance import TeacherAttendance
from app.utils.db import get_db_connection

webauthn_bp = Blueprint('webauthn_auth', __name__, url_prefix='/webauthn')


# ============================================================
# HELPERS
# ============================================================

def _rp_id():
    return current_app.config['WEBAUTHN_RP_ID']

def _rp_name():
    return current_app.config['WEBAUTHN_RP_NAME']

def _origin():
    return current_app.config['WEBAUTHN_ORIGIN']


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


# ============================================================
# REGISTRO DE DISPOSITIVO (desde el perfil del docente)
# ============================================================

@webauthn_bp.route('/register/begin', methods=['POST'])
@login_required
def register_begin():
    """Paso 1: el servidor genera las opciones de registro."""
    teacher = Teacher.get_by_user_id(current_user.id)
    if not teacher:
        return jsonify({'error': 'Usuario no vinculado a un docente.'}), 400

    # Credenciales ya existentes (para evitar duplicados)
    existing = WebAuthnCredential.get_by_teacher(teacher['id'])
    exclude_credentials = [
        PublicKeyCredentialDescriptor(id=_b64url_decode(c['credential_id']))
        for c in existing
    ]

    options = generate_registration_options(
        rp_id=_rp_id(),
        rp_name=_rp_name(),
        user_id=str(teacher['id']).encode(),
        user_name=teacher.get('email') or f"docente_{teacher['id']}",
        user_display_name=f"{teacher['first_name']} {teacher['last_name']}",
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )

    # Guardar el challenge en sesión (se usará en /register/complete)
    session['webauthn_register_challenge'] = _b64url_encode(options.challenge)
    session['webauthn_register_teacher_id'] = teacher['id']

    return options_to_json(options), 200, {'Content-Type': 'application/json'}


@webauthn_bp.route('/register/complete', methods=['POST'])
@login_required
def register_complete():
    """Paso 2: el servidor verifica la respuesta del autenticador."""
    challenge_b64 = session.pop('webauthn_register_challenge', None)
    teacher_id = session.pop('webauthn_register_teacher_id', None)

    if not challenge_b64 or not teacher_id:
        return jsonify({'error': 'Sesión de registro expirada. Intenta de nuevo.'}), 400

    try:
        body = request.get_json()
        verification = verify_registration_response(
            credential=body,
            expected_challenge=_b64url_decode(challenge_b64),
            expected_origin=_origin(),
            expected_rp_id=_rp_id(),
        )
    except Exception as e:
        print(f"[register_complete] Error: {e}")
        return jsonify({'error': 'No se pudo verificar el registro biométrico.'}), 400

    # Guardar la credencial (solo clave pública)
    credential_data = {
        'credential_id': _b64url_encode(verification.credential_id),
        'credential_public_key': _b64url_encode(verification.credential_public_key),
        'sign_count': verification.sign_count,
        'device_name': body.get('device_name', 'Dispositivo móvil'),
        'aaguid': verification.aaguid,
        'backup_eligible': verification.credential_device_type == 'multi_device',
        'backup_state': False,
    }

    if WebAuthnCredential.create(teacher_id, credential_data):
        return jsonify({'success': True, 'message': 'Dispositivo registrado correctamente.'}), 200

    return jsonify({'error': 'Error al guardar la credencial.'}), 500


# ============================================================
# AUTENTICACIÓN BIOMÉTRICA (marcar asistencia)
# ============================================================

@webauthn_bp.route('/authenticate/begin', methods=['POST'])
def auth_begin():
    """Paso 1: el kiosco pide la cédula, el servidor busca sus credenciales."""
    cedula = (request.get_json() or {}).get('cedula', '').strip()

    if not cedula or not cedula.isdigit():
        return jsonify({'error': 'Cédula inválida.'}), 400

    teacher = Teacher.get_by_id(int(cedula))
    if not teacher:
        # Respuesta genérica: no revelamos si la cédula existe
        return jsonify({'error': 'Credenciales no válidas.'}), 401

    credentials = WebAuthnCredential.get_by_teacher(teacher['id'])
    if not credentials:
        return jsonify({'error': 'No tienes un dispositivo registrado. Regístralo en tu perfil.'}), 400

    options = generate_authentication_options(
        rp_id=_rp_id(),
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=_b64url_decode(c['credential_id']))
            for c in credentials
        ],
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    session['webauthn_auth_challenge'] = _b64url_encode(options.challenge)
    session['webauthn_auth_teacher_id'] = teacher['id']

    return options_to_json(options), 200, {'Content-Type': 'application/json'}


@webauthn_bp.route('/authenticate/complete', methods=['POST'])
def auth_complete():
    """Paso 2: el servidor verifica la firma biométrica y marca asistencia."""
    challenge_b64 = session.pop('webauthn_auth_challenge', None)
    teacher_id = session.pop('webauthn_auth_teacher_id', None)

    if not challenge_b64 or not teacher_id:
        return jsonify({'error': 'Sesión expirada. Intenta de nuevo.'}), 400

    body = request.get_json()
    if not body:
        return jsonify({'error': 'Datos incompletos.'}), 400

    credential_id = body.get('id')
    credential = WebAuthnCredential.get_by_credential_id(credential_id)

    if not credential or credential['teacher_id'] != teacher_id:
        return jsonify({'error': 'Credencial no válida.'}), 401

    try:
        verification = verify_authentication_response(
            credential=body,
            expected_challenge=_b64url_decode(challenge_b64),
            expected_origin=_origin(),
            expected_rp_id=_rp_id(),
            credential_public_key=_b64url_decode(credential['credential_public_key']),
            credential_current_sign_count=credential['sign_count'],
        )
    except Exception as e:
        print(f"[auth_complete] Error: {e}")
        return jsonify({'error': 'Verificación biométrica fallida.'}), 401

    # Actualizar contador de firmas (protege contra clonación)
    WebAuthnCredential.update_sign_count(
        credential_id, verification.new_sign_count
    )

    # Marcar entrada/salida
    action = body.get('action', 'in')
    record = TeacherAttendance.get_today(teacher_id)

    if action == 'in':
        if record and record.get('check_in'):
            return jsonify({'success': True, 'message': 'Ya registraste tu entrada hoy.', 'already': True}), 200
        result = TeacherAttendance.check_in(teacher_id)
    else:
        if not record or not record.get('check_in'):
            return jsonify({'error': 'Debes marcar entrada primero.'}), 400
        if record.get('check_out'):
            return jsonify({'success': True, 'message': 'Ya registraste tu salida hoy.', 'already': True}), 200
        result = TeacherAttendance.check_out(teacher_id)

    if result.get('success'):
        teacher = Teacher.get_by_id(teacher_id)
        return jsonify({
            'success': True,
            'message': f"{'Entrada' if action == 'in' else 'Salida'} registrada para {teacher['first_name']} {teacher['last_name']}.",
        }), 200

    return jsonify({'error': result.get('error', 'Error desconocido.')}), 500


# ============================================================
# GESTIÓN DE DISPOSITIVOS (desde el perfil)
# ============================================================

@webauthn_bp.route('/credentials', methods=['GET'])
@login_required
def list_credentials():
    """Lista los dispositivos registrados del docente actual."""
    teacher = Teacher.get_by_user_id(current_user.id)
    if not teacher:
        return jsonify([]), 200

    creds = WebAuthnCredential.get_by_teacher(teacher['id'])
    return jsonify([
        {
            'id': c['credential_id'],
            'device_name': c['device_name'] or 'Dispositivo',
            'created_at': c['created_at'].isoformat() if c['created_at'] else None,
            'last_used_at': c['last_used_at'].isoformat() if c['last_used_at'] else None,
        }
        for c in creds
    ]), 200


@webauthn_bp.route('/credentials/<path:credential_id>', methods=['DELETE'])
@login_required
def delete_credential(credential_id):
    """Elimina un dispositivo registrado."""
    teacher = Teacher.get_by_user_id(current_user.id)
    if not teacher:
        return jsonify({'error': 'No autorizado.'}), 403

    if WebAuthnCredential.delete(credential_id, teacher['id']):
        return jsonify({'success': True}), 200

    return jsonify({'error': 'No se pudo eliminar la credencial.'}), 404