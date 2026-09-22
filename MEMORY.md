# MEMORY.md — Memoria técnica del proyecto

Este archivo registra decisiones importantes y hechos que deben conservarse entre sesiones. No es un diario de cada cambio pequeño.

## Cómo registrar una decisión

Añadir una entrada con esta estructura:

```text
### DEC-YYYY-MM-DD: Título breve
- Estado: aceptada | provisional | reemplazada
- Contexto: qué problema motivó la decisión.
- Decisión: qué se decidió.
- Consecuencias: beneficios, costes y riesgos.
- Referencias: archivos, commits o issues relacionados.
```

## Hechos actuales

- Repositorio: `Eduardoezi/school_management`.
- Rama principal: `main`.
- Descripción: sistema de gestión escolar.
- La aplicación utiliza Flask con patrón de fábrica (`create_app`).
- La persistencia usa MySQL con `mysql-connector-python`; no se usa un ORM como fuente principal.
- La interfaz se sirve con plantillas Jinja2 y recursos estáticos HTML/CSS/JavaScript.
- La configuración se carga desde `.env` mediante `python-dotenv`.
- La aplicación tiene autenticación con Flask-Login, contraseñas con bcrypt, CSRF con Flask-WTF y autenticación biométrica WebAuthn.
- La configuración de producción exige `SECRET_KEY`; el modo local tiene una clave de desarrollo de respaldo.
- El servidor se inicia mediante `run.py`; HTTPS y mDNS se activan cuando existen los certificados configurados.
- Las subidas de imágenes están limitadas a 2 MB y a JPG, JPEG, PNG y WEBP.

## Decisiones aceptadas

### DEC-2026-09-22: Mantener tres documentos operativos en la raíz
- Estado: aceptada
- Contexto: se necesita conservar reglas, decisiones técnicas y procedimientos repetibles para colaboración humana y agentes.
- Decisión: usar `AGENT.md` para reglas de trabajo, `MEMORY.md` para decisiones y hechos técnicos, y `SKILLS.md` para procedimientos reutilizables.
- Consecuencias: la documentación queda visible en la raíz y puede actualizarse junto con el código; cada documento debe mantenerse enfocado para evitar duplicación.
- Referencias: `AGENT.md`, `MEMORY.md`, `SKILLS.md`.

### DEC-2026-09-22: Conservar la arquitectura Flask existente
- Estado: aceptada
- Contexto: el proyecto ya está organizado alrededor de fábrica de aplicación, blueprints, modelos y plantillas.
- Decisión: las funcionalidades nuevas deben integrarse en esa arquitectura y no introducir otra estructura paralela.
- Consecuencias: se reduce el riesgo de romper imports, endpoints, permisos y templates; los cambios deben respetar los módulos existentes.
- Referencias: `app/__init__.py`, `app/routes/`, `app/models/`.

### DEC-2026-09-22: Mantener acceso a datos con consultas parametrizadas
- Estado: aceptada
- Contexto: la aplicación usa conexiones MySQL directas.
- Decisión: continuar usando la capa de modelos/utilidades existente y parámetros SQL, sin concatenar entrada del usuario.
- Consecuencias: se mantiene la compatibilidad actual y se reduce el riesgo de inyección SQL; una migración a ORM requeriría una decisión independiente.
- Referencias: `app/models/`, `app/utils/`, `requirements.txt`.

## Registro de cambios de decisiones

Cuando una decisión sea reemplazada, no borrarla: cambiar su estado a `reemplazada`, indicar la nueva entrada y explicar la migración. Las decisiones sobre seguridad, base de datos, roles o contratos HTTP deben incluir impacto y reversión.
