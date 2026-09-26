# Checklist de cierre del proyecto

## 1. Producto y aceptación

- [ ] Product Owner validó el alcance de la release.
- [ ] Las historias Must tienen criterios de aceptación satisfechos.
- [ ] Se realizó la demostración final con escenarios reales o datos de prueba.
- [ ] Las excepciones y funcionalidades pendientes están registradas.
- [ ] Se dispone de acta de aceptación o aprobación equivalente.

## 2. Calidad y pruebas

- [ ] Tests automatizados ejecutados en limpio.
- [ ] Lint y comprobaciones estáticas ejecutados.
- [ ] Flujos de login, logout y rutas protegidas validados.
- [ ] Casos de permisos por directivo, secretario, maestro, especialista y pendiente validados.
- [ ] Casos de datos inválidos, duplicados, inexistentes y fechas futuras validados.
- [ ] Pruebas de regresión ejecutadas después de las correcciones.
- [ ] No hay defectos críticos o bloqueantes abiertos.

## 3. Seguridad

- [ ] Secretos fuera del repositorio y configurados mediante variables seguras.
- [ ] `SECRET_KEY` de producción es fuerte y no es la clave de desarrollo.
- [ ] CSRF, sesiones, cookies y contraseñas revisados.
- [ ] WebAuthn usa RP ID y Origin definidos por configuración segura.
- [ ] No se exponen datos sensibles en errores, logs o vistas públicas.
- [ ] RBAC + ABAC fue revisado en estudiantes, cursos, asistencia, evaluaciones y documentos.

## 4. Base de datos

- [ ] Backup previo a la release generado.
- [ ] Restauración del backup probada y documentada.
- [ ] Migraciones numeradas y revisadas.
- [ ] Versión del esquema registrada.
- [ ] Rollback de migración probado o limitación documentada.
- [ ] No existen datos de prueba o credenciales reales en scripts compartidos.

## 5. Despliegue y operación

- [ ] Staging ejecutado con configuración equivalente a producción.
- [ ] Producción usa servidor WSGI apropiado detrás de proxy.
- [ ] HTTPS y cabeceras proxy verificados.
- [ ] El puerto interno no está expuesto externamente.
- [ ] `/health` y `/health/ready` están monitorizados.
- [ ] Logs rotativos y procedimiento de consulta disponibles.
- [ ] Alertas y responsables de incidentes definidos.
- [ ] Procedimiento de rollback disponible y probado.

## 6. Documentación

- [ ] README de instalación y ejecución actualizado.
- [ ] Manual de usuario disponible.
- [ ] Runbook operativo disponible.
- [ ] Backlog y sprints actualizados con el estado real.
- [ ] Deuda técnica y backlog posterior a la release registrados.
- [ ] Cambios relevantes y versión publicados.

## 7. Cierre Scrum

- [ ] Sprint 05 revisado con stakeholders.
- [ ] Retrospectiva realizada.
- [ ] Acciones de mejora asignadas con responsable y fecha.
- [ ] Métricas de puntos, defectos, pruebas e impedimentos archivadas.
- [ ] Product Backlog reordenado para mantenimiento y siguiente release.

## Resultado final

La release solo debe marcarse como cerrada cuando las secciones anteriores estén verificadas o cuando cada excepción tenga responsable, impacto y aprobación explícita.
