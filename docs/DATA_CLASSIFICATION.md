# Clasificación de datos personales

**Sistema Escolar IEE Villa de Cura**
**Última actualización:** 2026-09-25

Este documento clasifica los datos personales que maneja el sistema,
define el nivel de protección de cada uno y las reglas de acceso.

Cumple con:
- **LOPNNA** (Venezuela) — protección de datos de niños, niñas y adolescentes.
- **OWASP ASVS 1.8** — clasificación de datos.
- **Buenas prácticas GDPR art. 30** — registro de actividades de tratamiento.

---

## Niveles de clasificación

| Nivel | Definición | Ejemplos |
|-------|-----------|----------|
| **PÚBLICO** | Visible sin autenticación. Sin riesgo. | Nombre de la institución, logo, dirección |
| **INTERNO** | Requiere login. Riesgo bajo. | Nombre de docentes, cursos, calendario escolar |
| **CONFIDENCIAL** | Requiere rol específico. Riesgo medio. | Notas, asistencia, matrícula |
| **RESTRINGIDO** | Requiere permiso explícito + cifrado. Riesgo alto. | Datos médicos, psicológicos, bancarios |

---

## Registro de datos por tabla

### `users` — Cuentas del personal

| Campo | Nivel | Cifrado | Roles autorizados |
|-------|-------|---------|-------------------|
| `username` | INTERNO | No | Director, Secretario, el propio usuario |
| `email` | INTERNO | No | Director, Secretario, el propio usuario |
| `password_hash` | RESTRINGIDO | bcrypt | Nadie lo lee en claro. Solo sistema |
| `avatar` | INTERNO | No | Cualquier autenticado |
| `teacher_id` | INTERNO | No | Director, Secretario |
| `role` | INTERNO | No | Director, Secretario |

### `teachers` y `staff_details` — Personal

| Campo | Nivel | Cifrado | Roles autorizados |
|-------|-------|---------|-------------------|
| `first_name`, `last_name` | INTERNO | No | Cualquier autenticado |
| `email`, `hire_date` | INTERNO | No | Director, Secretario |
| `cedula` (`id`) | INTERNO | No | Director, Secretario |
| `bank_name`, `bank_account_type` | CONFIDENCIAL | No | Director, Secretario |
| `bank_account_number_encrypted` | RESTRINGIDO | **Fernet (AES-128 + HMAC)** | Director (cifrado en BD) |
| `bank_account_last6` | CONFIDENCIAL | No | Director, Secretario |
| `observations` (laborales) | CONFIDENCIAL | No | Director, Secretario |

### `students` y `student_details` — Estudiantes

| Campo | Nivel | Cifrado | Roles autorizados |
|-------|-------|---------|-------------------|
| `first_name`, `last_name` | INTERNO | No | Docentes de sus cursos, Director, Secretario |
| `school_id` (cédula escolar) | INTERNO | No | Director, Secretario |
| `birth_date`, `enrollment_date` | CONFIDENCIAL | No | Director, Secretario |
| `disability` | **RESTRINGIDO** | **Pendiente (SEC-09)** | Director, Secretario |
| `address`, `contact_phone` | CONFIDENCIAL | No | Director, Secretario |
| `photo` | INTERNO | No | Cualquier autenticado |

### `student_medical` — Ficha médica 🚨

**Datos sensibles de menores. Clasificación RESTRINGIDO. Cifrado pendiente (SEC-09).**

| Campo | Nivel | Cifrado actual | Cifrado objetivo |
|-------|-------|----------------|-------------------|
| `vaccine_*` (fechas) | CONFIDENCIAL | No | No (fechas no son texto libre) |
| `allergies` | **RESTRINGIDO** | ❌ Texto plano | ✅ Fernet |
| `chronic_conditions` | **RESTRINGIDO** | ❌ Texto plano | ✅ Fernet |
| `convulsions` | **RESTRINGIDO** | ❌ Texto plano | ✅ Fernet |
| `current_medication` | **RESTRINGIDO** | ❌ Texto plano | ✅ Fernet |
| `medical_attention` | **RESTRINGIDO** | ❌ Texto plano | ✅ Fernet |
| `upen_attention` | **RESTRINGIDO** | ❌ Texto plano | ✅ Fernet |
| `report_medical` | **RESTRINGIDO** | ❌ Texto plano | ✅ Fernet |
| `report_psychological` | **RESTRINGIDO** | ❌ Texto plano | ✅ Fernet |
| `report_neurological` | **RESTRINGIDO** | ❌ Texto plano | ✅ Fernet |

**Roles autorizados:** solo `directivo` y `secretario`. Los docentes **NO** ven la ficha médica.

### `student_socioeconomic` — Estudio socioeconómico 🚨

**Datos sensibles de la familia. Clasificación RESTRINGIDO. Cifrado pendiente (SEC-09).**

| Campo | Nivel | Cifrado actual | Cifrado objetivo |
|-------|-------|----------------|-------------------|
| `lives_with` | CONFIDENCIAL | No | No |
| `other_family_members` | **RESTRINGIDO** | ❌ Texto plano | ✅ Fernet |
| `working_members`, `household_members` | CONFIDENCIAL | No | No |
| `monthly_income` | **RESTRINGIDO** | ❌ Texto plano | ✅ Fernet |
| `housing_type`, `housing_condition` | CONFIDENCIAL | No | No |
| `housing_infrastructure` | **RESTRINGIDO** | ❌ Texto plano | ✅ Fernet |

**Roles autorizados:** solo `directivo` y `secretario`.

### `student_family` — Familiares

| Campo | Nivel | Cifrado | Roles autorizados |
|-------|-------|---------|-------------------|
| `first_name`, `last_name` | CONFIDENCIAL | No | Director, Secretario |
| `cedula_id` | CONFIDENCIAL | No | Director, Secretario |
| `address`, `phone`, `email` | CONFIDENCIAL | No | Director, Secretario |
| `photo` | INTERNO | No | Director, Secretario |

### `representatives` — Representantes

| Campo | Nivel | Cifrado | Roles autorizados |
|-------|-------|---------|-------------------|
| `cedula_id` | INTERNO | No | Director, Secretario |
| `first_name`, `last_name` | INTERNO | No | Director, Secretario |
| `email`, `phone`, `address` | CONFIDENCIAL | No | Director, Secretario |

### `login_attempts` — Auditoría de accesos (SEC-01)

| Campo | Nivel | Cifrado | Roles autorizados |
|-------|-------|---------|-------------------|
| `username`, `ip_address` | INTERNO | No | Sistema (para throttling) |
| `attempted_at`, `success` | INTERNO | No | Auditoría |

**Retención:** 30 días. Después se eliminan con `throttle.cleanup_old_attempts()`.

### `user_sessions` — Sesiones activas

| Campo | Nivel | Cifrado | Roles autorizados |
|-------|-------|---------|-------------------|
| `session_id` | RESTRINGIDO | No | Sistema |
| `ip_address`, `user_agent` | INTERNO | No | Sistema, Director (panel "usuarios en línea") |

**Retención:** 90 días de histórico, luego se cierran automáticamente.

---

## Métodos de cifrado en reposo

### Datos bancarios (implementado, SEC-06)

- **Algoritmo:** Fernet = AES-128-CBC + HMAC-SHA256.
- **Clave:** `BANK_ENCRYPTION_KEY` en `.env`.
- **Ubicación:** `staff_details.bank_account_number_encrypted` (`VARBINARY(255)`).
- **Descifrado:** solo con `StaffDetail.get_bank_account(teacher_id)`, que la ruta restringe a `directivo`.

### Datos médicos y socioeconómicos (pendiente, SEC-09)

- **Algoritmo:** mismo (Fernet).
- **Clave:** `DATA_ENCRYPTION_KEY` en `.env` (separada de la bancaria para poder rotar).
- **Ubicación:** migración 005 convertirá los campos a `VARBINARY` y re-cifrará el contenido.

---

## Reglas de retención

| Tipo de dato | Retención | Método de borrado |
|--------------|-----------|-------------------|
| Cuentas inactivas | 5 años tras último login | `users.active = 0` + purga manual |
| Ficha médica | 10 años tras egreso | Borrado físico con `DELETE` |
| Datos socioeconómicos | 10 años tras egreso | Borrado físico con `DELETE` |
| Matrículas | Permanente (historial académico) | Nunca se borra, se marca `status` |
| Logs de login | 30 días | Cron diario `cleanup_old_attempts()` |
| Sesiones cerradas | 90 días | Cron semanal |

---

## Reglas de acceso

### Principio de menor privilegio

Cada rol ve **solo lo que necesita**:

| Rol | Puede ver |
|-----|-----------|
| `directivo` | Todo |
| `secretario` | Todo excepto eliminar estudiantes y configurar evaluaciones |
| `maestro` | Solo estudiantes de sus cursos. **NUNCA** datos médicos ni socioeconómicos |

### Auditoría

Toda modificación de datos sensibles debe registrar `user_id` y `timestamp`.
Actualmente implementado en:
- `classroom_plans` → `plan_reviews` (histórico de cambios).
- `school_calendars` → `calendar_audit_log`.

**Pendiente (SEC-10 propuesto):** auditoría de accesos a fichas médicas y socioeconómicas.

---

## Referencias

- **LOPNNA** (Venezuela) — Ley Orgánica para la Protección de Niños, Niñas y Adolescentes. Arts. 57-58 (derecho a la privacidad).
- **OWASP ASVS 1.8** — Data Protection.
- **NIST SP 800-122** — Guide to Protecting the Confidentiality of PII.
- **GDPR art. 30** — Records of Processing Activities.