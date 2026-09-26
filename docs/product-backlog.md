# Product Backlog — School Management

> Estado inicial propuesto. `Pendiente` significa que debe validarse con el Product Owner; no implica que la funcionalidad no exista. Algunas historias describen consolidación, pruebas, UX o criterios de operación sobre funcionalidades que ya aparecen en el código.

## Visión del producto

Permitir que una institución educativa administre de forma segura su información institucional, usuarios, estudiantes, docentes, cursos, matrículas, planificación, asistencia, calendario y documentos, con acceso diferenciado por rol y una operación verificable.

## Personas usuarias

- **Directivo:** administración integral, configuración y supervisión.
- **Secretario:** operación administrativa delegada.
- **Maestro:** consulta de sus cursos/estudiantes, planes y reporte académico o de asistencia según autorización.
- **Especialista:** acceso ampliado a estudiantes/cursos según las reglas definidas.
- **Usuario pendiente:** cuenta registrada aún no aprobada.

## Historias priorizadas

| ID | Épica | Historia de usuario | Prioridad | Puntos | Dependencias | Estado |
|---|---|---|---|---:|---|---|
| SEG-001 | Seguridad | Como usuario quiero iniciar y cerrar sesión para acceder de forma controlada al sistema. | Must | 5 | Configuración, usuarios | Pendiente de validar |
| SEG-002 | Seguridad | Como directivo quiero aprobar usuarios y asignar roles para controlar quién puede operar el sistema. | Must | 5 | SEG-001 | Pendiente de validar |
| SEG-003 | Seguridad | Como responsable de seguridad quiero que las contraseñas, CSRF, sesiones y secretos se gestionen de forma segura. | Must | 8 | SEG-001 | Pendiente de validar |
| SEG-004 | Seguridad | Como personal autorizado quiero usar WebAuthn en el marcado de asistencia para reducir suplantaciones. | Should | 8 | SEG-001, configuración HTTPS | Pendiente de validar |
| SEG-005 | Autorización | Como maestro quiero ver únicamente estudiantes y cursos que me corresponden, mientras que directivo/secretario conservan sus permisos. | Must | 8 | SEG-002 | Pendiente de validar |
| SEG-006 | Autorización | Como institución quiero autorización RBAC + ABAC comprobada en asistencia, evaluaciones, documentos y acceso por curso. | Must | 8 | SEG-002, SEG-005 | Pendiente de validar |
| ADM-001 | Institución | Como directivo quiero administrar los datos de la institución para que aparezcan en la portada y documentos. | Must | 3 | SEG-002 | Pendiente de validar |
| ADM-002 | Usuarios | Como directivo quiero consultar usuarios conectados y gestionar roles para supervisar el acceso. | Should | 5 | SEG-002 | Pendiente de validar |
| ACADEM-001 | Estudiantes | Como secretario quiero registrar, editar, consultar y cambiar el estado de estudiantes. | Must | 8 | ADM-001 | Pendiente de validar |
| ACADEM-002 | Docentes | Como directivo quiero administrar docentes y vincularlos con usuarios/cursos. | Must | 8 | SEG-002 | Pendiente de validar |
| ACADEM-003 | Cursos | Como directivo o secretario quiero crear, editar y consultar cursos, asignando docentes cuando corresponda. | Must | 5 | ACADEM-002 | Pendiente de validar |
| ACADEM-004 | Matrículas | Como secretario quiero registrar y editar matrículas para mantener la población activa por año escolar. | Must | 8 | ACADEM-001, ACADEM-003, YEAR-001 | Pendiente de validar |
| ACADEM-005 | Horarios | Como secretario quiero gestionar horarios para que estén disponibles en los flujos de asistencia. | Should | 5 | ACADEM-003 | Pendiente de validar |
| YEAR-001 | Año escolar | Como directivo quiero crear, activar y marcar años escolares para separar la operación académica. | Must | 5 | SEG-002 | Pendiente de validar |
| PLAN-001 | Planificación | Como maestro quiero crear y gestionar mis planes de aula y actividades del año activo. | Must | 8 | YEAR-001, SEG-005 | Pendiente de validar |
| EVAL-001 | Evaluación | Como maestro quiero registrar y editar evaluaciones de mis estudiantes autorizados. | Must | 8 | ACADEM-001, ACADEM-003, SEG-006 | Pendiente de validar |
| ATT-001 | Asistencia | Como maestro quiero reportar asistencia diaria de mis cursos sin poder seleccionar fechas futuras. | Must | 5 | ACADEM-003, ACADEM-004, SEG-006 | Pendiente de validar |
| ATT-002 | Asistencia | Como directivo quiero consultar estadísticas diarias para supervisar la asistencia. | Should | 5 | ATT-001 | Pendiente de validar |
| CAL-001 | Calendario | Como directivo quiero crear/publicar el calendario escolar y sus eventos. | Must | 8 | YEAR-001 | Pendiente de validar |
| CAL-002 | Calendario | Como usuario autorizado quiero consultar el calendario publicado y exportarlo a iCalendar. | Should | 5 | CAL-001 | Pendiente de validar |
| DOC-001 | Documentos | Como usuario autorizado quiero emitir constancias con información del estudiante y permisos correctos. | Should | 8 | ACADEM-001, SEG-006 | Pendiente de validar |
| OPS-001 | Operación | Como operador quiero comprobar liveness y readiness mediante `/health` y `/health/ready`. | Must | 3 | Configuración MySQL | Pendiente de validar |
| OPS-002 | Operación | Como equipo quiero CI con lint y pruebas en cada push para evitar regresiones. | Must | 5 | Tests | Pendiente de validar |
| OPS-003 | Operación | Como administrador quiero migraciones numeradas, rollback y control de versión del esquema. | Must | 8 | Base de datos | Pendiente de validar |
| OPS-004 | Operación | Como administrador quiero backup/restauración, logs rotativos, staging y monitoreo documentados. | Must | 8 | OPS-001, despliegue | Pendiente de validar |
| OPS-005 | Operación | Como operador quiero desplegar con Waitress detrás de proxy, HTTPS y firewall configurados. | Must | 8 | OPS-001 | Pendiente de validar |
| UX-001 | Calidad | Como usuario quiero mensajes de error, estados vacíos, navegación y formularios consistentes y accesibles. | Should | 5 | Módulos funcionales | Pendiente de validar |

## Orden recomendado

1. Seguridad y autorización: SEG-001 a SEG-006.
2. Datos maestros: ADM-001, ACADEM-001 a ACADEM-005 y YEAR-001.
3. Trabajo docente: PLAN-001, EVAL-001 y ATT-001/ATT-002.
4. Calendario y documentos: CAL-001/CAL-002 y DOC-001.
5. Operación y calidad: OPS-001 a OPS-005 y UX-001.

## Refinamiento pendiente

El Product Owner debe confirmar: duración real de los sprints, capacidad del equipo, reglas de negocio venezolanas del calendario, formato de constancias, política de retención de asistencia/evaluaciones y roles definitivos. Tras esa sesión, se deben cambiar los estados de `Pendiente de validar` a `Ready`, `En progreso`, `Bloqueado` o `Hecho`.
