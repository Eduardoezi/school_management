# AGENT.md — Reglas del proyecto

## Propósito

`school_management` es un sistema web de gestión escolar para administrar estudiantes, representantes, docentes, cursos, matrículas, asistencia, evaluaciones, horarios, documentos y perfiles.

Estas reglas son obligatorias para cualquier cambio realizado por una persona o agente automatizado.

## Tecnologías oficiales

- **Backend:** Python 3 y Flask 3.1.3.
- **Plantillas:** Jinja2 y HTML.
- **Frontend:** HTML, CSS y JavaScript vanilla. No introducir frameworks frontend sin una decisión registrada en `memory.md`.
- **Base de datos:** MySQL mediante `mysql-connector-python`.
- **Autenticación y autorización:** Flask-Login, `bcrypt`, Flask-WTF/CSRF y decoradores propios de roles.
- **Autenticación biométrica:** WebAuthn.
- **Configuración:** variables de entorno cargadas con `python-dotenv`.
- **Imágenes:** Pillow.
- **PDF:** xhtml2pdf.
- **Descubrimiento local:** zeroconf/mDNS cuando HTTPS está habilitado.
- **Servidor de entrada:** `run.py`, que crea la aplicación con `app.create_app()`.

Las versiones fijadas en `requirements.txt` son la fuente de verdad para las dependencias.

## Estructura y nombres

- `app/__init__.py`: fábrica de la aplicación, extensiones, blueprints, hooks y procesadores de contexto.
- `app/config.py`: configuración central y lectura de `.env`.
- `app/routes/`: blueprints y controladores HTTP. Usar nombres en `snake_case`, por ejemplo `students.py` y `students_bp`.
- `app/models/`: acceso a datos y lógica relacionada con entidades. Usar clases en `PascalCase`, por ejemplo `Student`, `Teacher` y `Course`.
- `app/security/`: código de seguridad y control de acceso.
- `app/utils/`: utilidades compartidas, como conexión a base de datos y decoradores.
- `app/templates/`: vistas Jinja2 organizadas por módulo funcional.
- `app/static/`: CSS, JavaScript, imágenes y uploads.
- `run.py`: arranque local/servidor; no colocar lógica de negocio aquí.

Los módulos, funciones y variables Python deben usar `snake_case`; las clases, `PascalCase`; las constantes, `UPPER_SNAKE_CASE`. Mantener los nombres funcionales existentes (`students`, `teachers`, `enrollment`, etc.) para no romper endpoints, templates ni `url_for`.

## Arquitectura obligatoria

1. Usar el patrón de fábrica mediante `create_app()`.
2. Registrar una nueva funcionalidad como blueprint en `app/routes/` y registrarla en `_register_blueprints()`.
3. Mantener las consultas y operaciones de persistencia en `app/models/` o utilidades de datos, no dentro de las plantillas.
4. Las rutas deben validar autenticación con `@login_required` y autorización con `@role_required(...)` cuando corresponda.
5. Las operaciones que modifican datos deben usar POST y protección CSRF. Las eliminaciones requieren confirmación visual y ejecución separada por POST.
6. Usar consultas parametrizadas; nunca interpolar directamente valores recibidos del usuario en SQL.
7. Cerrar cursores y conexiones, hacer `commit()` solo cuando la operación haya terminado correctamente y ejecutar `rollback()` ante errores.
8. Usar `render_template`, `redirect`, `url_for` y mensajes `flash` siguiendo las convenciones existentes.
9. Mantener los textos visibles de la aplicación en español, salvo que exista una decisión explícita de internacionalización.

## Seguridad

- Nunca guardar secretos, contraseñas, certificados, claves privadas o credenciales en el repositorio.
- No subir `.env`, dumps de la base de datos ni archivos reales de estudiantes, docentes o representantes.
- No desactivar CSRF, autenticación, autorización, validación de uploads ni controles WebAuthn para “simplificar” una funcionalidad.
- No registrar contraseñas, tokens, datos biométricos ni información personal sensible en logs.
- Respetar `MAX_CONTENT_LENGTH` (2 MB) y `ALLOWED_IMAGE_EXTENSIONS` salvo decisión registrada.
- Mantener `SECRET_KEY`, credenciales MySQL, origen WebAuthn y certificados configurables por entorno.

## Prohibido tocar sin aprobación explícita

- El esquema de base de datos, nombres de tablas, columnas, claves o relaciones existentes.
- Roles (`directivo`, `secretario`, `maestro` y otros existentes) y sus permisos.
- El contrato de endpoints, nombres de blueprints, endpoints Flask y rutas usadas por las plantillas.
- `app/config.py`, `run.py`, autenticación, sesiones, CSRF y WebAuthn.
- Certificados, dominios, configuración HTTPS y valores de producción.
- Datos reales, archivos dentro de `app/static/uploads/` y archivos ignorados por Git.
- Versiones de `requirements.txt` sin comprobar compatibilidad y registrar la decisión.

Si un cambio en esas áreas es imprescindible, documentar antes el motivo, impacto, plan de migración y forma de reversión en `memory.md`.

## Calidad antes de entregar

- Revisar que las rutas nuevas tengan autenticación y autorización adecuadas.
- Verificar validaciones, errores, permisos y mensajes para los casos normales y fallidos.
- Comprobar que las plantillas reciban todas las variables que utilizan.
- Ejecutar las pruebas disponibles y, si no existen, hacer al menos una verificación manual del flujo afectado.
- No mezclar refactorizaciones grandes con una funcionalidad no relacionada.
- Actualizar `memory.md` si se toma una decisión estructural o se cambia una convención.
