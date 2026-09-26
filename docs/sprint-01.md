# Sprint 01 — Seguridad, acceso y calidad de datos

## Objetivo del sprint

Entregar un flujo de acceso y autorización verificable, con una base de pruebas que proteja los módulos académicos antes de ampliar funcionalidades.

## Duración propuesta

2 semanas (10 días hábiles). Ajustar los puntos a la capacidad real del equipo tras Sprint 00.

## Alcance comprometido inicial

| ID | Historia | Criterios de aceptación resumidos | Puntos |
|---|---|---|---:|
| SEG-001 | Inicio/cierre de sesión | Usuario válido entra; inválido recibe error no revelador; cierre invalida la sesión; rutas protegidas exigen autenticación | 5 |
| SEG-002 | Roles y aprobación | Directivo puede gestionar roles; usuario pendiente no opera módulos protegidos; cambios de rol se reflejan en permisos | 5 |
| SEG-005 | Alcance por estudiante/curso | Maestro solo ve y opera sus recursos; especialista aplica la regla definida; directivo/secretario conservan acceso esperado; acceso indebido devuelve 403 | 8 |
| OPS-001 | Health checks | `/health` responde sin BD; `/health/ready` responde 200 solo con MySQL disponible y 503 cuando no está disponible | 3 |
| OPS-002 | CI básico | Cada push ejecuta pruebas y lint configurados; el fallo bloquea la calidad del incremento | 5 |
| DOC-004 | Guía local de ejecución | README/documentación indica instalación, `.env`, base de datos, tests y comandos de verificación | 2 |

**Total inicial:** 28 puntos. Si la capacidad histórica es menor, mover OPS-002 o dividir SEG-005.

## Plan de tareas

### Día 1 — Planificación

- Confirmar objetivo, capacidad y criterios.
- Preparar datos de prueba para cada rol.
- Ejecutar línea base de tests.

### Días 2–4 — Acceso y roles

- Cubrir login, logout y rutas protegidas.
- Verificar aprobación/roles.
- Añadir pruebas de errores y sesiones.

### Días 5–7 — RBAC + ABAC

- Probar acceso a estudiantes, cursos, asistencia y evaluaciones.
- Comprobar que las validaciones ocurren antes de lectura/escritura.
- Revisar casos de usuario sin docente vinculado y fecha futura.

### Días 8–9 — Operación y documentación

- Automatizar health checks y pruebas en CI.
- Documentar configuración local y secretos de prueba.

### Día 10 — Revisión y retrospectiva

- Demostrar escenarios exitosos y denegados.
- Registrar deuda, defectos y decisiones.
- Actualizar backlog con lo aprendido.

## Definition of Done específica

- [ ] Cada historia tiene pruebas automatizadas o una justificación documentada.
- [ ] Se prueban al menos los roles `directivo`, `secretario`, `maestro` y `pendiente`.
- [ ] Se prueban respuestas 401/403 y errores de datos inválidos.
- [ ] No se usan credenciales reales en tests o documentación.
- [ ] CI reproduce el resultado local.
- [ ] Product Owner acepta la demostración.

## No incluido

No se comprometen en este sprint nuevas pantallas de matrículas, calendario o planificación. Podrán entrar mediante refinamiento después de estabilizar seguridad y calidad.

## Métricas

Registrar al cierre: puntos comprometidos/completados, tests añadidos, defectos encontrados, tiempo bloqueado, cobertura si está configurada y decisiones de aceptación.

## Criterio de éxito

Un usuario autorizado puede entrar y consultar/operar exclusivamente los recursos que le corresponden; un usuario no autorizado no puede hacerlo; el sistema tiene checks de salud, pruebas ejecutables y una guía local reproducible.
