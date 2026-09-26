# Sprint 04 — Calendario, documentos y operación productiva

## Objetivo

Fortalecer la operación institucional mediante calendario publicado, exportación de eventos, emisión controlada de documentos y procedimientos básicos de operación en producción.

## Duración propuesta

2 semanas (10 días hábiles).

## Alcance

| ID | Historia | Criterios de aceptación | Puntos |
|---|---|---|---:|
| CAL-002 | Calendario publicado e iCalendar | Los eventos se visualizan y se exportan en un `.ics` válido | 5 |
| DOC-001 | Emisión de constancias | Se generan documentos con datos autorizados y completos | 8 |
| OPS-001 | Health checks | `/health` y `/health/ready` distinguen proceso disponible de BD disponible | 3 |
| OPS-003 | Migraciones | Los cambios de esquema son numerados, reproducibles y versionados | 8 |
| OPS-004 | Backup y monitoreo | Backup, restauración, logs y alertas quedan documentados | 8 |
| OPS-005 | Despliegue seguro | HTTPS, proxy, secretos y servidor de aplicación se configuran de forma segura | 8 |

**Total estimado:** 40 puntos. Validar capacidad antes de comprometerlo completo.

## Plan de trabajo

1. Verificar calendario, categorías, origen y publicación.
2. Validar exportación iCalendar conforme al flujo existente.
3. Confirmar permisos y plantilla de constancias.
4. Automatizar o documentar pruebas de liveness/readiness.
5. Definir migraciones, control de esquema y rollback.
6. Completar procedimientos de backup, restauración, logs y monitoreo.
7. Revisar despliegue con Waitress detrás de proxy y HTTPS.

## Criterios de aceptación

- [ ] Los eventos publicados se muestran a los roles previstos.
- [ ] El archivo `.ics` puede importarse en un cliente externo.
- [ ] Solo permisos autorizados emiten constancias.
- [ ] `/health` no depende de MySQL; `/health/ready` informa indisponibilidad de MySQL con estado 503.
- [ ] Cada cambio de esquema tiene migración y procedimiento de reversión.
- [ ] Los backups se prueban mediante una restauración documentada.
- [ ] No existen secretos en el repositorio ni en logs.
- [ ] El servidor interno no queda expuesto directamente a Internet.

## Definition of Done

- [ ] Evidencia de pruebas funcionales y operativas.
- [ ] Procedimientos documentados y probados en un entorno no productivo.
- [ ] Product Owner acepta calendario y documentos.
- [ ] Operaciones aprueba el runbook de despliegue.

## Riesgos

- Configuración productiva diferente del entorno de pruebas.
- Dependencia de proxy, SSL o servicios externos.
- Cambios de requisitos en documentos institucionales.

## Criterio de éxito

Existe un flujo verificable para publicar calendario, emitir documentos autorizados y operar la aplicación con controles mínimos de disponibilidad, datos y despliegue.
