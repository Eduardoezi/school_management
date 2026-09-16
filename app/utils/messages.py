"""
Mensajes centralizados del sistema.
Usa las constantes en las rutas: flash(MSG.CEDULA_DUPLICADA, 'danger')
"""

# ============================================================
# CÉDULAS
# ============================================================
CEDULA_VACIA = "Debe ingresar la cédula."
CEDULA_INVALIDA = "La cédula debe contener solo números (6 a 10 dígitos)."
CEDULA_MUY_CORTA = "La cédula es demasiado corta."
CEDULA_MUY_LARGA = "La cédula es demasiado larga."
CEDULA_DUPLICADA = "La cédula {cedula} ya está registrada en el sistema."
CEDULA_NO_ENCONTRADA = "La cédula {cedula} no está registrada como personal de la escuela."
CEDULA_YA_VINCULADA = "El personal con cédula {cedula} ya tiene un usuario registrado."
CEDULA_NO_ES_PERSONAL = "No puede registrarse si no es personal de la escuela."

# ============================================================
# CÉDULA ESCOLAR
# ============================================================
SCHOOL_ID_DUPLICADO = "La cédula escolar {school_id} ya existe. Verifique el orden de parto o la cédula del representante."
SCHOOL_ID_NO_GENERADO = "No se pudo generar la cédula escolar. Verifique la fecha de nacimiento y el representante."
SCHOOL_ID_INVALIDO = "La cédula escolar no tiene el formato correcto."

# ============================================================
# FECHAS Y AÑOS
# ============================================================
FECHA_VACIA = "Debe indicar la fecha."
FECHA_FUTURA = "No puede seleccionar fechas futuras."
FECHA_ANTIGUA = "La fecha es demasiado antigua. Verifique el año."
AÑO_NACIMIENTO_INVALIDO = "El año de nacimiento no es válido."
EDAD_FUERA_RANGO = "La edad del estudiante no corresponde al grado asignado."
FECHA_EGRESO_INVALIDA = "La fecha de egreso debe ser posterior a la de inscripción."

# ============================================================
# ASISTENCIA
# ============================================================
ENTRADA_YA_REGISTRADA = "Ya registró su entrada hoy a las {hora}."
SALIDA_YA_REGISTRADA = "Ya registró su salida hoy a las {hora}."
SALIDA_SIN_ENTRADA = "Debe registrar su entrada antes de marcar la salida."
ASISTENCIA_EXCEDE_MATRICULA = "La suma de presentes y ausentes ({total}) supera la matrícula ({matricula})."
ASISTENCIA_VALORES_NEGATIVOS = "No puede ingresar valores negativos."
ASISTENCIA_CURSO_VACIO = "El curso no tiene estudiantes inscritos."
ASISTENCIA_YA_EXISTE = "Ya existe un reporte para este curso en esta fecha."

# ============================================================
# USUARIOS
# ============================================================
USUARIO_DUPLICADO = "El nombre de usuario ya está en uso."
EMAIL_DUPLICADO = "El correo electrónico ya está en uso."
EMAIL_INVALIDO = "El formato del correo electrónico no es válido."
PASSWORD_CORTA = "La contraseña debe tener al menos 6 caracteres."
PASSWORD_NO_COINCIDE = "Las contraseñas no coinciden."
CAMPOS_OBLIGATORIOS = "Todos los campos obligatorios deben estar llenos."
LOGIN_INCORRECTO = "Usuario o contraseña incorrectos."

# ============================================================
# INSCRIPCIONES
# ============================================================
INSCRIPCION_DUPLICADA = "El estudiante ya está inscrito en este curso."
INSCRIPCION_OTRO_CURSO = "El estudiante ya tiene una inscripción activa en otro curso."
INSCRIPCION_SIN_ESTUDIANTE = "Debe seleccionar un estudiante."
INSCRIPCION_SIN_CURSO = "Debe seleccionar un curso."

# ============================================================
# CURSOS
# ============================================================
CURSO_CODIGO_DUPLICADO = "El código {code} ya está en uso."
CURSO_CODIGO_INVALIDO = "El código solo puede contener letras, números y guiones."
CURSO_CON_ESTUDIANTES = "No se puede eliminar el curso: tiene estudiantes inscritos."
CURSO_SIN_DOCENTE = "El curso no tiene un docente asignado."
AÑO_ACADEMICO_INVALIDO = "El año académico debe tener el formato AAAA-AAAA (ej: 2026-2027)."

# ============================================================
# ARCHIVOS
# ============================================================
ARCHIVO_MUY_GRANDE = "El archivo supera el tamaño máximo permitido (2 MB)."
ARCHIVO_FORMATO_INVALIDO = "Solo se permiten imágenes JPG, PNG o WEBP."
ARCHIVO_NO_ES_IMAGEN = "El archivo no es una imagen válida."
ARCHIVO_MUY_PEQUEÑO = "La imagen debe tener al menos 100x100 píxeles."

# ============================================================
# PERMISOS
# ============================================================
ACCESO_DENEGADO = "No tiene permisos para realizar esta acción."
SESION_EXPIRADA = "Su sesión ha expirado. Por favor inicie sesión nuevamente."

# ============================================================
# GENÉRICOS
# ============================================================
ERROR_INTERNO = "Ocurrió un error inesperado. Intente de nuevo."
ERROR_BD = "Error al conectar con la base de datos."
OPERACION_EXITOSA = "Operación realizada correctamente."