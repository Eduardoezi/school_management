# Release Plan — School Management

## Release propuesta

**Versión:** 1.0.0 — Entrega inicial operativa  
**Rama de preparación:** `release/1.0.0`  
**Base documental:** Sprints 00–05  
**Responsable de aprobación:** Product Owner / representante de la institución

> Las fechas deben definirse en la planificación real. Este documento establece puertas de salida, no fechas históricas.

## Objetivo de la release

Entregar una versión utilizable del sistema de gestión escolar que cubra administración institucional, usuarios y permisos, estudiantes, docentes, cursos, matrículas, planificación, evaluación, asistencia, calendario y operación básica.

## Alcance incluido

- Autenticación, sesiones, CSRF y gestión de roles.
- Autorización RBAC + ABAC por usuario, curso y estudiante.
- Datos institucionales y dashboard.
- Estudiantes, representantes, docentes, cursos y matrículas.
- Año escolar, planes de aula, evaluaciones y asistencia.
- Calendario escolar y exportación iCalendar.
- Constancias o documentos autorizados.
- Health checks, pruebas, migraciones y procedimientos operativos.

## Fuera de alcance para 1.0.0

- Funcionalidades que no tengan criterios de aceptación aprobados.
- Integraciones externas no probadas.
- Cambios de infraestructura sin runbook y rollback.
- Requisitos nuevos introducidos después de la congelación de alcance.

## Puertas de salida

### Gate 1 — Funcional

- [ ] Historias Must aceptadas por Product Owner.
- [ ] Flujos principales demostrados con datos de prueba.
- [ ] No existen defectos críticos o bloqueantes abiertos.

### Gate 2 — Seguridad y datos

- [ ] Matriz de permisos validada.
- [ ] Casos de acceso indebido devuelven denegación correcta.
- [ ] Secretos, sesiones, CSRF y datos sensibles revisados.
- [ ] Backup y restauración probados.

### Gate 3 — Operación

- [ ] Despliegue reproducible en staging.
- [ ] Health checks, logs, monitoreo y rollback documentados.
- [ ] Migraciones ejecutadas y versión del esquema registrada.
- [ ] Manual técnico y de usuario disponibles.

### Gate 4 — Aprobación

- [ ] Demo final realizada.
- [ ] Excepciones y riesgos residuales aceptados por escrito.
- [ ] Acta de aceptación completada.
- [ ] Etiqueta `v1.0.0` creada después de aprobar la release.

## Estrategia de despliegue

1. Congelar alcance y crear rama de release.
2. Generar backup y verificar restauración.
3. Desplegar primero en staging.
4. Ejecutar smoke tests y pruebas de readiness.
5. Obtener aprobación del responsable.
6. Desplegar en producción durante una ventana acordada.
7. Monitorear logs y health checks.
8. Si falla un gate, ejecutar rollback documentado.

## Criterios de rollback

- Fallo de inicio o de health check.
- Pérdida, corrupción o inconsistencia de datos.
- Vulnerabilidad crítica detectada.
- Migración irreversible o incompatible.
- Error que impida autenticación o acceso a una función Must.

## Soporte posterior

Durante el periodo inicial posterior a la entrega se deben registrar incidentes con severidad, pasos para reproducir, evidencia, impacto y responsable. Los cambios no urgentes regresan al Product Backlog.
