# Sprint 03 — Planificación docente, evaluación y asistencia

## Objetivo

Habilitar la operación docente diaria del centro educativo mediante planes de aula, evaluaciones y asistencia, aplicando autorización por rol y por curso.

## Duración propuesta

2 semanas (10 días hábiles).

## Alcance

| ID | Historia | Criterios de aceptación | Puntos |
|---|---|---|---:|
| PLAN-001 | Planes de aula | El maestro crea, edita y consulta sus planes del año activo; los roles autorizados pueden revisarlos | 8 |
| EVAL-001 | Evaluaciones | El maestro registra y modifica evaluaciones de estudiantes autorizados | 8 |
| ATT-001 | Asistencia diaria | El maestro reporta asistencia de sus cursos y no puede usar fechas futuras | 5 |
| ATT-002 | Estadísticas de asistencia | Los roles autorizados consultan totales diarios por curso | 5 |
| UX-001 | Calidad de experiencia | Formularios, mensajes y estados vacíos son consistentes | 5 |

**Total estimado:** 31 puntos.

## Plan de trabajo

1. Validar el año escolar activo y la vinculación docente-curso.
2. Implementar o verificar creación, edición y consulta de planes.
3. Probar evaluaciones con controles de estudiante, curso y calificación.
4. Probar asistencia diaria, cantidades no negativas y bloqueo de fechas futuras.
5. Mejorar mensajes de error, estados vacíos y navegación.
6. Ejecutar pruebas de regresión de seguridad y datos.

## Criterios de aceptación

- [ ] Un maestro solo opera cursos y estudiantes autorizados.
- [ ] El especialista conserva únicamente el acceso ampliado definido por negocio.
- [ ] Directivo y secretario consultan según la matriz de permisos.
- [ ] No se aceptan fechas futuras en asistencia.
- [ ] Las evaluaciones se relacionan con estudiante, curso y año activo.
- [ ] Los errores de validación son comprensibles y no revelan información sensible.
- [ ] Existen pruebas automatizadas o evidencias funcionales para los flujos principales.

## Definition of Done

- [ ] Pruebas de permisos para directivo, secretario, maestro y usuario no autorizado.
- [ ] Pruebas de datos inválidos, recursos inexistentes y fechas futuras.
- [ ] Pruebas de regresión ejecutadas sin fallos críticos.
- [ ] Product Owner acepta la demostración.
- [ ] Se documentan deuda técnica e impedimentos.

## Riesgos

- Ambigüedad en permisos de especialistas.
- Diferencias entre las reglas reales de evaluación y el modelo actual.
- Duplicidad o inconsistencia al registrar asistencia en varios cursos.

## Criterio de éxito

La institución puede realizar la operación docente básica sin acceso indebido, sin registros de asistencia futuros y con información consistente para evaluación y seguimiento.
