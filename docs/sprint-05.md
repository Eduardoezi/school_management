# Sprint 05 — Estabilización y preparación de entrega

## Objetivo

Cerrar la fase de estabilización, corregir defectos críticos, reforzar seguridad y preparar la entrega con documentación, evidencia y criterios de aceptación claros.

## Duración propuesta

2 semanas (10 días hábiles).

## Alcance

| ID | Historia | Criterios de aceptación | Puntos |
|---|---|---|---:|
| BUG-001 | Errores críticos | Los fallos que bloquean acceso, guardado o consulta quedan corregidos y probados | 8 |
| BUG-002 | Consistencia de datos | No se permiten duplicados, relaciones rotas ni estados inválidos | 8 |
| SEG-007 | Revisión final de seguridad | Se revisan permisos, CSRF, sesiones, secretos y rutas protegidas | 8 |
| UX-002 | Flujo de usuario | Se corrigen formularios, mensajes, navegación y estados vacíos | 5 |
| OPS-006 | Preparación de entrega | La configuración final, manual y evidencia de validación quedan disponibles | 8 |

**Total estimado:** 37 puntos.

## Plan de trabajo

1. Clasificar defectos por severidad y prioridad.
2. Resolver primero bloqueos y pérdida o corrupción de datos.
3. Ejecutar pruebas de regresión después de cada corrección relevante.
4. Revisar autorización RBAC + ABAC en todos los módulos principales.
5. Ejecutar pruebas de configuración y despliegue en entorno limpio.
6. Completar manual de usuario, runbook y acta de aceptación.

## Criterios de aceptación

- [ ] No quedan defectos críticos o bloqueantes abiertos para la entrega.
- [ ] Cada corrección tiene causa, solución y prueba asociada.
- [ ] Las relaciones estudiante-docente-curso-matrícula conservan integridad.
- [ ] Se validan accesos autorizados y denegados.
- [ ] No se exponen secretos, datos sensibles ni rutas protegidas.
- [ ] La aplicación inicia con la configuración documentada.
- [ ] El Product Owner acepta el incremento o registra excepciones explícitas.

## Definition of Done

- [ ] Suite de pruebas ejecutada y resultado archivado.
- [ ] Checklist de cierre completado.
- [ ] Riesgos residuales y deuda técnica registrados.
- [ ] Manual técnico y de usuario revisados.
- [ ] Revisión final de seguridad realizada.
- [ ] Acta de aceptación o lista de excepciones firmada por el responsable.

## Riesgos

- Defectos no reproducibles fuera del entorno de desarrollo.
- Cambios de reglas de negocio al final del proyecto.
- Correcciones rápidas que generen regresiones.

## Criterio de éxito

El sistema está preparado para una entrega controlada, con calidad, seguridad, documentación y riesgos residuales conocidos.
