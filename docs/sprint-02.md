# Sprint 02 — Gestión académica y operación básica

## Objetivo del sprint

Completar la base funcional del sistema escolar para que una institución pueda registrar su información académica principal con control de permisos y flujo operativo mínimo viable. Este sprint se enfoca en los procesos esenciales del ciclo educativo: estudiantes, docentes, cursos, matrículas y calendario básico.

## Duración propuesta

2 semanas (10 días hábiles). Se recomienda revisar la capacidad real del equipo después del cierre del Sprint 01.

## Alcance comprometido inicial

| ID | Historia | Criterios de aceptación resumidos | Puntos |
|---|---|---|---:|
| ADM-001 | Datos institucionales | El directivo registra nombre, dirección, códigos y RIF; la información aparece en la portada y documentos de la app | 3 |
| ACADEM-001 | Registro de estudiantes | Se pueden crear, editar y consultar estudiantes con representante y datos básicos | 8 |
| ACADEM-002 | Gestión de docentes | Se pueden registrar docentes y vincularlos a usuarios y cursos | 8 |
| ACADEM-003 | Gestión de cursos | Se crean y editan cursos, se asignan docentes y se validan campos obligatorios | 5 |
| ACADEM-004 | Matrículas | Se registra la matrícula activa, se valida duplicado y se mantiene el estado académico por curso | 8 |
| YEAR-001 | Año escolar | Se crea un año académico, se activa, y se marca el siguiente ciclo | 5 |
| CAL-001 | Calendario escolar | Se pueden crear eventos, publicarlos y distinguir origen ministerial o institucional | 8 |

Total inicial estimado: 45 puntos.

Si la capacidad del equipo es menor, se recomienda mover una de estas historias al Sprint 03, priorizando ACADEM-001, ACADEM-003 y ACADEM-004.

## Plan de trabajo por fase

### Fase 1 — Base institucional y académica

- Revisión del flujo de datos institucionales.
- Validación de campos necesarios para estudiante, representante y docente.
- Comprobación de validaciones de duplicados y estados de alta/baja.
- Confirmación de roles que pueden crear o editar cada entidad.

### Fase 2 — Cursos y matrículas

- Crear curso con código único y docente principal.
- Registrar matrículas por curso y estudiante.
- Verificar que los estudiantes no se dupliquen en el mismo curso.
- Revisar el acceso de directivo/secretario y las restricciones del maestro.

### Fase 3 — Año escolar y calendario

- Crear año escolar activo y marcado como próximo.
- Publicar calendario escolar.
- Validar eventos de ministerio, asuetos, feriados y recesos.
- Asegurar que el calendario exportable se genere sin errores.

## Criterios de aceptación por historia

### ADM-001 — Datos institucionales

- [ ] El directivo puede editar los datos generales desde la interfaz o la administración correspondiente.
- [ ] La institución queda visible en la portada del sistema.
- [ ] Los campos vacíos se muestran con valores por defecto coherentes.
- [ ] El sistema evita la exposición de datos sensibles en vistas públicas.

### ACADEM-001 — Registro de estudiantes

- [ ] Se crea un estudiante con datos básicos, representante y curso asociado si aplica.
- [ ] El sistema valida cédula/escolar y campos obligatorios.
- [ ] La edición no rompe la relación con representante ni matrículas activas.
- [ ] El estudiante puede verse con su estado y su curso actual para los roles autorizados.

### ACADEM-002 — Gestión de docentes

- [ ] Se puede registrar un docente con su usuario asociado.
- [ ] El directivo puede cambiar la vinculación docente-usuario.
- [ ] El sistema bloquea la eliminación si existirán referencias activas en cursos o planes.
- [ ] La vista de docentes refleja el rol y la asignación académica correcta.

### ACADEM-003 — Gestión de cursos

- [ ] El sistema genera un código único y verificable para cada curso.
- [ ] Se asigna un docente principal o responsable.
- [ ] El directivo/secretario puede editar la información sin romper la matrícula.
- [ ] El maestro solo ve los cursos autorizados.

### ACADEM-004 — Matrículas

- [ ] Una matrícula activa tiene curso, estudiante, fecha y estado válido.
- [ ] No se permite la inscripción duplicada en el mismo curso.
- [ ] La edición permite cambiar curso o estado, manteniendo trazabilidad.
- [ ] La matricula es visible para la consulta de estudiantes, cursos y reportes.

### YEAR-001 — Año escolar

- [ ] Solo el directivo puede crear, activar y desactivar el año escolar.
- [ ] El año activo tiene consecuencias claras sobre planes, evaluaciones y matrículas.
- [ ] Se registra el año próximo y se evita la posibilidad de haber dos activos.

### CAL-001 — Calendario escolar

- [ ] El calendario tiene eventos con fechas, descripción y categoría.
- [ ] Los eventos se distinguen por origen y afectan la lógica correcta de clases/asistencia cuando aplica.
- [ ] La versión publicada se visualiza para los roles correctos.
- [ ] El archivo exportado en .ics es válido para importar en calendarios externos.

## Reglas de negocio para este sprint

1. El directivo conserva control total sobre instituciones, años escolares y configuración general.
2. El secretario puede gestionar la matrícula, cursos y registro operativo, según la lógica de roles definida.
3. El maestro no puede crear o editar datos institucionales ni asignar roles.
4. La validación de duplicados y permisos se aplica antes de guardar.
5. Si una entidad tiene dependencias activas, la eliminación debe bloquearse con mensaje claro.

## Entregables esperados

- Estado académico y registro funcional de estudiantes, docentes y cursos.
- Creación y edición de matrículas con validación.
- Administración del calendario escolar y exportación básica.
- Documentación de la operación del sprint y evidencia de pruebas relevantes.

## Definition of Done específico del sprint

- [ ] Se validan los roles autorizados para cada acción.
- [ ] Las pruebas relevantes existen para creación, edición y error de validación.
- [ ] El flujo no rompe la lógica de los módulos ya validados en Sprint 01.
- [ ] Se revisa que no haya fugas de información sensible.
- [ ] Product Owner revisa la demostración del incremento.
- [ ] El equipo registra impedimentos, riesgos y próximos pasos.

## Riesgos principales

- Cambio de reglas de negocio por parte de la institución al momento de confirmar matrículas o calendario.
- Dependencia de datos reales del plantel que no están estandarizados.
- Cambios de permisos en módulos ya entregados durante la corrección de bugs.

## Criterio de éxito

Al final del sprint, la institución debe poder operar de forma base los procesos esenciales de gestión escolar, con acceso diferenciado por rol, validaciones de negocio y una evidencia clara de que el sistema no degrada la seguridad ni la consistencia académica.
