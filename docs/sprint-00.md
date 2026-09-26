# Sprint 00 — Alineación y línea base

## Tipo

Sprint de preparación técnica y de producto. No se debe contabilizar como evidencia de trabajo histórico; es una propuesta para corregir la documentación antes de iniciar el trabajo funcional.

## Objetivo

Dejar una base común de Scrum, validar el alcance real del sistema y preparar la trazabilidad necesaria para que el siguiente sprint produzca un incremento demostrable.

## Duración propuesta

5 días hábiles, antes del primer sprint regular.

## Historias/tareas

| ID | Trabajo | Resultado verificable | Puntos |
|---|---|---|---:|
| DOC-001 | Validar backlog con Product Owner y equipo | Prioridades, reglas y criterios confirmados; discrepancias registradas | 2 |
| DOC-002 | Inventariar módulos, rutas, roles y dependencias | Matriz funcional basada en el código y lista de dudas | 3 |
| DOC-003 | Acordar DoR, DoD, cadencia y convención de IDs | Equipo puede planificar y trazar commits/PRs | 2 |
| OPS-001 | Ejecutar instalación y pruebas en entorno limpio | Comandos, variables `.env` y resultado documentados | 3 |
| OPS-002 | Revisar `CHECKLIST.md` y clasificar pendientes operativos | Riesgos priorizados y responsables asignados | 2 |
| SEG-001 | Diseñar matriz de roles/permisos y casos negativos | Casos para directivo, secretario, maestro, especialista y pendiente | 3 |

**Total estimado:** 15 puntos.

## Checklist de aceptación del sprint

- [ ] Product Owner valida visión y personas.
- [ ] Se confirma qué funcionalidades existentes están aceptadas y cuáles requieren pruebas/refactor.
- [ ] Se dispone de datos de prueba no sensibles.
- [ ] Se ejecutan tests actuales y se registra el resultado.
- [ ] Se acuerdan responsables y capacidad del Sprint 01.
- [ ] Todo impedimento tiene responsable y próxima acción.

## Entregable

Este conjunto de documentos más un acta breve de refinamiento. El incremento no es una funcionalidad de usuario; habilita una planificación fiable.

## Riesgos/impedimentos a registrar

- Falta de evidencia histórica de sprints.
- Configuración MySQL/HTTPS/WebAuthn no disponible localmente.
- Inconsistencias entre `run.py`, `serve.py` y el procedimiento de despliegue deben confirmarse contra el entorno objetivo.
