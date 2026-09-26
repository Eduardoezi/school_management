# SKILLS.md — Procedimientos repetibles

Este archivo reúne procedimientos que se deben aplicar de la misma manera cada vez. Si un procedimiento cambia, actualizarlo aquí y registrar la decisión relevante en `MEMORY.md`.

## Skill: crear un endpoint Flask

1. Identificar el módulo funcional y revisar rutas, modelo y template relacionados.
2. Crear o modificar el blueprint correspondiente en `app/routes/<modulo>.py`.
3. Usar un nombre de función descriptivo en `snake_case` y conservar el nombre del blueprint existente.
4. Definir el método HTTP explícitamente (`GET`, `POST` u otro necesario). Las operaciones de escritura deben usar `POST`.
5. Añadir `@login_required` y, cuando corresponda, `@role_required('rol1', 'rol2')`.
6. Leer y validar entradas desde `request.args`, `request.form` o JSON; no confiar en datos del navegador.
7. Delegar persistencia al modelo correspondiente usando consultas parametrizadas.
8. Gestionar éxito y error con `flash`, `redirect` y `url_for`, o devolver JSON coherente si el endpoint es una API.
9. Para una vista HTML, usar `render_template` y pasar explícitamente todas las variables necesarias.
10. Registrar el blueprint en `app/__init__.py` si es nuevo.
11. Añadir el formulario con token CSRF cuando sea un POST desde HTML.
12. Probar autenticación, permisos, validación, caso exitoso y error de base de datos.

Ejemplo de estructura:

```python
@students_bp.route('/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('directivo', 'secretario')
def edit_view(student_id):
    student = Student.get_by_id(student_id)
    if not student:
        abort(404)

    if request.method == 'POST':
        data = build_validated_data(request.form)
        if Student.update_full(student_id, data):
            flash('Registro actualizado exitosamente.', 'success')
            return redirect(url_for('students.detail_view', student_id=student_id))
        flash('Error al actualizar el registro.', 'danger')

    return render_template('students/edit.html', student=student)
```

## Skill: añadir un modelo o acceso a datos

1. Confirmar primero las tablas y columnas existentes; no inventar cambios de esquema.
2. Crear `app/models/<entidad>.py` con una clase `PascalCase`.
3. Reutilizar `get_db_connection` y el estilo de manejo de conexiones del proyecto.
4. Usar SQL parametrizado con placeholders `%s`.
5. Validar y normalizar los datos antes de ejecutar la consulta.
6. Hacer `commit()` en escrituras exitosas y `rollback()` en excepciones.
7. Cerrar cursor y conexión en `finally`.
8. Devolver una forma consistente con el módulo: diccionario, lista de diccionarios, identificador o booleano.
9. No exponer contraseñas, hashes, tokens ni datos sensibles innecesarios.
10. Probar duplicados, registro inexistente, error de conexión y transacciones parciales.

## Skill: crear o modificar una plantilla

1. Ubicar la plantilla dentro de `app/templates/<modulo>/`.
2. Reutilizar el layout, macros, clases CSS y componentes ya existentes.
3. Mantener textos de usuario en español y etiquetas accesibles (`label`, `alt`, mensajes de error).
4. Escapar contenido por defecto; no usar `|safe` salvo que el origen y la necesidad estén justificados.
5. Incluir CSRF en todo formulario que modifique datos.
6. No poner consultas SQL ni lógica de negocio en Jinja2.
7. Confirmar que cada variable usada sea enviada por la ruta.
8. Comprobar roles y estados vacíos, errores y confirmaciones.

## Skill: añadir JavaScript o CSS

1. Revisar primero los archivos estáticos existentes y reutilizar sus patrones.
2. Usar JavaScript vanilla salvo decisión documentada.
3. Mantener el código específico de una pantalla separado del código compartido.
4. No insertar secretos, credenciales ni decisiones de autorización en el navegador.
5. Validar siempre también en el servidor; la validación cliente solo mejora la experiencia.
6. Considerar teclado, foco, contraste, mensajes de error y diseño responsive.
7. Evitar cambios globales que puedan alterar otras pantallas sin comprobarlas.

## Skill: gestionar autenticación y permisos

1. Identificar el rol requerido y aplicar `@login_required` y `@role_required` en la ruta.
2. Verificar permisos en el servidor, incluso si la interfaz oculta botones.
3. Usar Flask-Login para la sesión y los helpers existentes para el usuario actual.
4. Mantener CSRF activo en formularios mutables.
5. No crear una segunda implementación de login, sesiones o contraseñas.
6. Para cambios WebAuthn, revisar simultáneamente dominio, origen, RP ID, HTTPS y credenciales registradas.
7. No registrar secretos ni información biométrica en logs.

## Skill: registrar una decisión técnica

1. Confirmar que afecta arquitectura, seguridad, datos, dependencias, roles, endpoints o una convención futura.
2. Añadir una entrada fechada a `MEMORY.md` con contexto, decisión, consecuencias y referencias.
3. Si reemplaza una decisión anterior, conservar el registro antiguo y enlazarlo con la nueva entrada.
4. Actualizar `AGENT.md` o `SKILLS.md` si la decisión cambia una regla o procedimiento.
5. Incluir plan de migración y reversión cuando el cambio sea riesgoso.

## Skill: revisar un cambio antes de entregarlo

- Confirmar archivos modificados y ausencia de secretos o datos reales.
- Revisar permisos, CSRF, validación de entradas y consultas parametrizadas.
- Verificar que no se rompan nombres de endpoints, blueprints, templates o roles.
- Ejecutar pruebas disponibles y una comprobación manual del flujo afectado.
- Revisar errores de conexión, transacciones, archivos inexistentes y registros duplicados.
- Actualizar la documentación si se introdujo una nueva convención.
