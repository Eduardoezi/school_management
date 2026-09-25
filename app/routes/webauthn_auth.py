# app/routes/webauthn_auth.py
"""
WebAuthn para marcado de entrada/salida del personal.

REGLA DE ORO:
    El RP ID y el Origin que el servidor declara al navegador
    vienen SIEMPRE de la configuración (.env), NUNCA del Host
    que manda el cliente. Derivarlos del request permite
    Host-spoofing / DNS-rebinding contra el kiosco.
"""
import base64

from flask import (
    Blueprint, request, jsonify,
    session, current_app, abort,
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
    AuthenticatorAttachment,
)

from app.models.teacher import Teacher
from app.models.webauthn_credential import WebAuthnCredential
from app.models.teacher_attendance import TeacherAttendance

webauthn_bp = Blueprint('webauthn_auth', __name__, url_prefix='/webauthn')


# ============================================================
# CONFIGURACIÓN — siempre desde .env, nunca desde el request
# ============================================================
def _is_production() -> bool:
    return bool(current_app.config.get('IS_PRODUCTION'))


def _rp_name() -> str:
    return current_app.config.get('WEBAUTHN_RP_NAME', 'Sistema Escolar')


def _rp_id() -> str:
    """
    RP ID autorizado.
    - Producción: obligatorio en .env (config.py ya lo valida al arrancar).
    - Desarrollo: si no está configurado, se cae al host del request
      para no romper el flujo local. En producción NO hay fallback.
    """
    configured = current_app.config.get('WEBAUTHN_RP_ID')
    if configured:
        return configured
    if _is_production():
        raise RuntimeError(
            "WEBAUTHN_RP_ID no está configurado. La app no debería "
            "haber arrancado en producción sin esta variable."
        )
    # Solo en dev:
    return request.host.split(':', 1)[0]


def _origin() -> str:
    """
    Origin autorizado.
    - Producción: obligatorio en .env.
    - Desarrollo: fallback al request.
    """
    configured = current_app.config.get('WEBAUTHN_ORIGIN')
    if configured:
        return configured
    if _is_production():
        raise RuntimeError(
            "WEBAUTHN_ORIGIN no está configurado en producción."
        )
    # Solo en dev:
    scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
    return f"{scheme}://{request.host}"


def _check_host() -> None:
    """
    Rechaza peticiones cuyo Host no coincida con WEBAUTHN_RP_ID.

    En producción esto evita que un cliente con acceso directo al
    puerto interno del servidor (LAN, kiosco comprometido) fuerce
    un RP ID falso manipulando el header Host.

    En desarrollo, si WEBAUTHN_RP_ID no está definido, no aplica.
    """
    allowed = current_app.config.get('WEBAUTHN_RP_ID')
    if not allowed:
        return  # modo dev sin configuración explícita
    host = request.host.split(':', 1)[0]
    if host != allowed:
        current_app.logger.warning(
            "[webauthn] Host no autorizado: %r (esperado %r)",
            host, allowed,
        )
        abort(400, description='Host no autorizado para WebAuthn.')


# ============================================================
# HELPERS base64url
# ============================================================
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


# ============================================================
# DIAGNÓSTICO
# ============================================================
@webauthn_bp.route('/diagnostics', methods=['GET'])
def diagnostics():
    """
    Endpoint informativo. NO valida Host a propósito: sirve para
    diagnosticar problemas desde cualquier equipo de la LAN.
    """
    try:
        rp_id = _rp_id()
        origin = _origin()
        config_error = None
    except RuntimeError as exc:
        rp_id = None
        origin = None
        config_error = str(exc)

    host = request.host.split(':', 1)[0]
    is_localhost = host in ('localhost', '127.0.0.1', '::1')
    is_https = request.scheme == 'https'
    secure = is_https or is_localhost

    return jsonify({
        'secure_context': secure,
        'scheme': request.scheme,
        'host': host,
        'rp_id': rp_id,
        'origin': origin,
        'config_error': config_error,
        'message': (
            'Contexto seguro: WebAuthn disponible.' if secure
            else 'WebAuthn requiere HTTPS. Accede por https:// o usa localhost.'
        ),
    })


# ============================================================
# REGISTRO DE DISPOSITIVO
# ============================================================
@webauthn_bp.route('/register/begin', methods=['POST'])
@login_required
def register_begin():
    _check_host()

    teacher = Teacher.get_by_user_id(current_user.id)
    if not teacher:
        return jsonify({'error': 'Usuario no vinculado a un docente.'}), 400

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
            authenticator_attachment=AuthenticatorAttachment.CROSS_PLATFORM,
        ),
    )

    session['webauthn_register_challenge'] = _b64url_encode(options.challenge)
    session['webauthn_register_teacher_id'] = teacher['id']

    return options_to_json(options), 200, {'Content-Type': 'application/json'}


@webauthn_bp.route('/register/complete', methods=['POST'])
@login_required
def register_complete():
    _check_host()

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
        current_app.logger.exception("[register_complete] Error: %s", e)
        return jsonify({'error': 'No se pudo verificar el registro biométrico.'}), 400

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
# AUTENTICACIÓN BIOMÉTRICA — SOLO PARA ENTRADA
# ============================================================
@webauthn_bp.route('/authenticate/begin', methods=['POST'])
def auth_begin():
    """Paso 1: el kiosco pide la cédula, el servidor busca sus credenciales."""
    _check_host()

    cedula = (request.get_json() or {}).get('cedula', '').strip()

    if not cedula or not cedula.isdigit():
        return jsonify({'error': 'Cédula inválida.'}), 400

    teacher = Teacher.get_by_id(int(cedula))
    if not teacher:
        return jsonify({'error': 'Credenciales no válidas.'}), 401

    record = TeacherAttendance.get_today(teacher['id'])
    if record and record.get('check_in'):
        return jsonify({
            'error': 'Ya registraste tu entrada hoy.',
            'already': True,
            'check_in': TeacherAttendance.format_time(record.get('check_in')),
        }), 409

    credentials = WebAuthnCredential.get_by_teacher(teacher['id'])
    if not credentials:
        return jsonify({
            'error': 'No tienes un dispositivo registrado. '
                     'Regístralo desde tu perfil antes de marcar asistencia.'
        }), 400

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
    """
    Paso 2: verifica la firma y marca ENTRADA.
    Endpoint exclusivo del flujo de entrada; la salida no usa biometría.
    """
    _check_host()

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
        current_app.logger.exception("[auth_complete] Error: %s", e)
        return jsonify({'error': 'Verificación biométrica fallida.'}), 401

    WebAuthnCredential.update_sign_count(credential_id, verification.new_sign_count)

    existing = TeacherAttendance.get_today(teacher_id)
    if existing and existing.get('check_in'):
        return jsonify({
            'success': True,
            'already': True,
            'message': 'Ya registraste tu entrada hoy.',
            'check_in':  TeacherAttendance.format_time(existing.get('check_in')),
            'check_out': TeacherAttendance.format_time(existing.get('check_out')),
        }), 200

    result = TeacherAttendance.check_in(teacher_id)
    if not result.get('success'):
        return jsonify({'error': result.get('error', 'Error desconocido.')}), 500

    teacher = Teacher.get_by_id(teacher_id)
    new_record = TeacherAttendance.get_today(teacher_id)
    return jsonify({
        'success': True,
        'action': 'in',
        'message': f"Entrada registrada para {teacher['first_name']} {teacher['last_name']}.",
        'check_in':  TeacherAttendance.format_time(new_record.get('check_in'))  if new_record else None,
        'check_out': TeacherAttendance.format_time(new_record.get('check_out')) if new_record else None,
    }), 200


# ============================================================
# GESTIÓN DE DISPOSITIVOS
# ============================================================
@webauthn_bp.route('/credentials', methods=['GET'])
@login_required
def list_credentials():
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
    teacher = Teacher.get_by_user_id(current_user.id)
    if not teacher:
        return jsonify({'error': 'No autorizado.'}), 403

    if WebAuthnCredential.delete(credential_id, teacher['id']):
        return jsonify({'success': True}), 200

    return jsonify({'error': 'No se pudo eliminar la credencial.'}), 404