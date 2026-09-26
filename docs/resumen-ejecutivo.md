# Resumen ejecutivo — Proyecto Scrum

## Proyecto

**School Management** es un sistema web de gestión escolar desarrollado con Flask, MySQL, plantillas Jinja y recursos HTML/CSS/JavaScript. El producto centraliza información institucional y procesos académicos, con autenticación y autorización diferenciada por rol.

## Propósito de la planificación

La documentación Scrum fue reorganizada para sustituir un backlog y una planificación de sprints incompletos por artefactos trazables, verificables y vinculados con la estructura funcional del repositorio. Los sprints descritos son una línea base propuesta; deben actualizarse con el estado real del equipo y la aprobación del Product Owner.

## Valor esperado

El sistema busca reducir trabajo manual y errores de administración mediante:

- Registro centralizado de estudiantes, representantes, docentes, cursos y matrículas.
- Acceso controlado para directivos, secretarios, maestros y usuarios especializados.
- Planificación docente, evaluación y asistencia diaria.
- Calendario escolar consultable y exportable.
- Documentos institucionales emitidos con permisos.
- Controles de operación, salud, backup y despliegue.

## Organización Scrum

- **Product Owner:** representante de la institución; prioriza necesidades y acepta incrementos.
- **Scrum Master:** facilita eventos, elimina impedimentos y protege el proceso.
- **Developers:** implementan, prueban, documentan y despliegan.
- **Stakeholders:** usuarios administrativos y docentes que validan el producto.

Se propone una cadencia de sprints de dos semanas, con planificación, dailies, revisión y retrospectiva. El Sprint 00 sirve como alineación y no debe confundirse con trabajo histórico ya ejecutado.

## Hoja de ruta

1. **Sprint 00 — Alineación:** validar alcance, roles, DoR, DoD, entorno y riesgos.
2. **Sprint 01 — Seguridad y acceso:** autenticación, roles, autorización y CI inicial.
3. **Sprint 02 — Gestión académica:** institución, estudiantes, docentes, cursos, matrículas, año escolar y calendario base.
4. **Sprint 03 — Operación docente:** planes, evaluaciones, asistencia y mejoras de experiencia.
5. **Sprint 04 — Operación productiva:** calendario avanzado, documentos, migraciones, backup, health checks y despliegue.
6. **Sprint 05 — Estabilización:** defectos, consistencia, seguridad final, documentación y preparación de release.

## Criterios de éxito

La release se considera exitosa cuando:

- Los flujos Must están aceptados por el Product Owner.
- Los roles solo acceden a la información y acciones que les corresponden.
- Los procesos académicos principales conservan integridad de datos.
- Las pruebas y comprobaciones de calidad son reproducibles.
- El despliegue, backup, monitoreo y rollback están documentados.
- Los riesgos residuales y la deuda técnica quedan visibles para la siguiente iteración.

## Riesgos ejecutivos

- La documentación histórica de sprints no está disponible y requiere validación del equipo.
- Las reglas reales de la institución pueden diferir de las inferidas desde el código.
- La operación depende de MySQL, variables de entorno, HTTPS y configuración de infraestructura.
- Seguridad, backups y migraciones deben verificarse en un entorno equivalente a producción.

## Próximas decisiones requeridas

1. Confirmar Product Owner, Scrum Master y capacidad del equipo.
2. Confirmar duración y fechas reales de los sprints.
3. Validar prioridades y puntos del Product Backlog.
4. Definir entorno de staging y datos de prueba.
5. Aprobar la Definition of Done y los gates de release.
6. Registrar las decisiones en el backlog y en las revisiones de sprint.

## Referencias

- `docs/README.md` — guía Scrum y convenciones.
- `docs/product-backlog.md` — backlog priorizado.
- `docs/sprint-00.md` a `docs/sprint-05.md` — objetivos y alcance de cada sprint.
- `docs/release-plan.md` — plan y puertas de salida de la release.
- `docs/checklist-cierre.md` — verificación final.
