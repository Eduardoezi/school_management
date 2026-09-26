# Documentación Scrum — School Management

## Propósito

Este directorio contiene una línea base de gestión ágil para `Eduardoezi/school_management`, un sistema Flask de gestión escolar con MySQL, interfaz Jinja/Bootstrap, autenticación, RBAC/ABAC, asistencia, calendario y operación.

La documentación se reconstruyó a partir de la estructura y funcionalidades visibles del repositorio. Como no se dispone de actas históricas de planificación, los sprints se presentan como **plan propuesto y trazable**, no como una afirmación de trabajo ya realizado.

## Roles Scrum propuestos

- **Product Owner:** representante de la institución educativa; prioriza valor y valida aceptación.
- **Scrum Master:** facilita el proceso, elimina impedimentos y mantiene actualizados los artefactos.
- **Developers:** equipo que implementa, prueba, documenta y despliega.
- **Stakeholders:** directivo, secretario, maestros y personal administrativo.

## Cadencia sugerida

- Sprint de 2 semanas.
- Planificación: 2 horas.
- Daily: 15 minutos por día hábil.
- Revisión: 1 hora con usuarios representantes.
- Retrospectiva: 45 minutos.
- Refinamiento: 1 hora semanal.

## Artefactos y reglas

- El **Product Backlog** está en `product-backlog.md`.
- Los objetivos y tareas de cada iteración están en `sprint-00.md` y `sprint-01.md`.
- Una historia no entra al sprint sin criterios de aceptación verificables y dependencias conocidas.
- La estimación usa puntos Fibonacci: 1, 2, 3, 5, 8 y 13.
- La prioridad usa MoSCoW: Must, Should, Could, Won't (por ahora).
- Los puntos son estimaciones iniciales y deben recalibrarse tras el primer sprint.

## Definition of Ready (DoR)

Una historia está lista para planificarse cuando:

1. Tiene persona, necesidad y valor.
2. Tiene criterios de aceptación comprobables.
3. Se conocen dependencias, riesgos y datos necesarios.
4. Puede completarse dentro de un sprint o dividirse.
5. Product Owner y equipo entienden el alcance.

## Definition of Done (DoD)

Una historia se considera terminada cuando:

1. El código está integrado en la rama acordada y revisado.
2. Las pruebas automatizadas relevantes pasan.
3. Se verifican permisos por rol y, cuando aplica, por recurso/curso.
4. Se validan errores, estados vacíos y entradas inválidas.
5. Se actualiza la documentación técnica o funcional.
6. Se ejecutan comprobaciones de seguridad y no se exponen secretos.
7. Product Owner acepta los criterios de aceptación en la revisión.

## Riesgos iniciales

- La documentación histórica de backlog y sprints no está disponible; las fechas y compromisos anteriores deben confirmarse con el equipo.
- El proyecto depende de MySQL y configuración `.env`; las pruebas locales necesitan datos y credenciales de prueba.
- Hay obligaciones operativas pendientes en `CHECKLIST.md`: despliegue con Waitress, migraciones, hashes de dependencias, backups, logs, staging, CI y monitoreo.
- Los módulos de autenticación, WebAuthn y autorización requieren pruebas de regresión antes de cambios funcionales.

## Trazabilidad

Los IDs del backlog deben usarse en ramas, commits y pull requests, por ejemplo: `feat/SEG-001-login` o `fix/OPS-003-health-check`. Esta convención permite relacionar trabajo, pruebas y aceptación.
