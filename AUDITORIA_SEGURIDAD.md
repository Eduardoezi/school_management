# Auditoría de seguridad y trazabilidad del sistema de gestión escolar

**Repositorio revisado:** `Eduardoezi/school_management`
**Commit base:** `520424dec9fe2ab39a64a7634da22129664f949c`
**Rama de auditoría:** `Version_IA`
**Fecha:** 18 de septiembre de 2026
**Destinatario:** Equipo responsable del sistema

## Resumen ejecutivo

La aplicación no debe exponerse a Internet en su estado actual. La revisión identificó 28 oportunidades de mejora: 2 críticas, 10 altas, 13 medias y 3 bajas. La ruta pública de registro permite solicitar el rol `directivo`, y las rutas públicas de asistencia permiten descubrir cédulas y nombres del personal. En conjunto, una persona no autorizada podría identificar una cédula sin usuario, crear una cuenta privilegiada y obtener acceso administrativo.

La protección contra falsificación de solicitudes está ausente en los 46 formularios encontrados. También existen acciones destructivas por GET, depuración activa en todas las interfaces, una clave de sesión predecible cuando falta la variable de entorno, permisos por objeto insuficientes, revocación de sesiones no aplicada, XSS potencial en el kiosco y ausencia de una bitácora general. El sistema almacena datos de menores, familiares, salud y situación socioeconómica, por lo que estos problemas tienen un impacto mayor que en una aplicación administrativa ordinaria.

La prioridad inmediata es cerrar el autorregistro privilegiado, asegurar el arranque, introducir CSRF, corregir el kiosco y aplicar autorización por objeto. Después deben implantarse sesiones revocables, auditoría append-only, eliminaciones lógicas, migraciones versionadas y controles de privacidad.

## Alcance y método

La revisión cubrió los 4.330 renglones de Python contabilizados por Bandit, las plantillas Jinja, JavaScript del cliente, `requirements.txt`, ocho commits del historial Git y el archivo local `../estructura_bd.sql`. Se realizaron las siguientes comprobaciones:

- Compilación sintáctica con `compileall`: correcta.
- Bandit: cuatro candidatos, de los cuales dos son falsos positivos de cadenas de texto; se confirmaron la escucha en todas las interfaces y un `except` silencioso.
- `pip-audit`: una vulnerabilidad única reportada dos veces para `xhtml2pdf 0.2.16`, identificada como `PYSEC-2026-2056`, `GHSA-jj5c-hhrg-vv5h` y `CVE-2024-25885`; la herramienta no informó una versión corregida.
- Búsqueda de secretos en el estado actual y el historial: no se encontraron credenciales reales ni claves privadas.
- Inventario de rutas Flask, métodos HTTP y decoradores de rol.
- Comparación de tablas usadas por el código con el esquema SQL local.

No se ejecutaron pruebas dinámicas contra una base de datos porque el repositorio no incluye migraciones, datos de prueba ni un esquema completo. La severidad considera dos escenarios: intranet escolar e Internet. Los controles que protegen datos sensibles, integridad académica y trazabilidad son obligatorios en ambos.

## Matriz priorizada

| ID | Severidad | Mejora recomendada | Prioridad |
|---|---|---|---|
| SEG-001 | Crítica | Cerrar el autorregistro con elección de rol | P0 |
| SEG-002 | Crítica | Evitar suplantación y enumeración en asistencia | P0 |
| SEG-003 | Alta | Incorporar CSRF en todas las operaciones de estado | P0 |
| SEG-004 | Alta | Separar desarrollo y producción y eliminar secretos por defecto | P0 |
| SEG-005 | Alta | Aplicar autorización por estudiante y sensibilidad del dato | P0 |
| SEG-006 | Alta | Restringir evaluaciones y reportes a cursos autorizados | P0 |
| SEG-007 | Alta | Hacer efectiva la revocación y expiración de sesiones | P1 |
| SEG-008 | Alta | Eliminar el XSS almacenado del kiosco | P0 |
| SEG-009 | Alta | Sustituir borrados GET y eliminaciones físicas | P0 |
| AUD-001 | Alta | Crear una bitácora general append-only | P1 |
| DATA-001 | Alta | Versionar el esquema y corregir tablas faltantes | P1 |
| PRIV-001 | Alta | Proteger y gobernar datos de menores y salud | P1 |
| SEG-010 | Media | Validar el destino de redirección después del login | P1 |
| SEG-011 | Media | Reforzar contraseñas, MFA y limitación de intentos | P1 |
| SEG-012 | Media | Endurecer cookies, cabeceras, TLS y recursos CDN | P1 |
| SEG-013 | Media | Reducir exposición de APIs y listados de personal | P1 |
| SEG-014 | Media | Impedir lectura arbitraria mediante la ruta del logo | P1 |
| SEG-015 | Media | Neutralizar fórmulas CSV y evitar caché de exportaciones | P2 |
| SEG-016 | Media | Resolver la alerta de seguridad de `xhtml2pdf` | P1 |
| AUD-002 | Media | Hacer atómica la numeración y emisión documental | P1 |
| AUD-003 | Media | Eliminar atribuciones ficticias de docente | P1 |
| DATA-002 | Media | Endurecer la conexión y el usuario MySQL | P2 |
| ENG-001 | Media | Implantar logging estructurado y manejo seguro de errores | P2 |
| ENG-002 | Media | Centralizar validación, límites y normalización | P2 |
| SEG-017 | Baja | Endurecer el procesamiento y almacenamiento de imágenes | P2 |
| AUD-004 | Baja | Proteger la integridad y retención del registro de sesiones | P2 |
| DATA-003 | Media | Corregir restricciones, identificadores y cascadas del esquema | P2 |
| ENG-003 | Baja | Añadir pruebas, CI, documentación y retirar respaldos de código | P3 |

## Hallazgos detallados

### SEG-001 Autorregistro público con escalación de privilegios

- **Severidad:** Crítica.
- **Evidencia:** `app/routes/auth.py:55-112` acepta `role` del formulario y permite `directivo`, `secretario` o `maestro`. `app/templates/register.html:46-58` presenta esas opciones a cualquier visitante. La ruta no requiere autenticación ni invitación.
- **Impacto:** Creación de una cuenta administrativa por una persona no autorizada. El único requisito adicional es una cédula de personal existente y aún no vinculada.
- **Escenario:** Se enumera una cédula mediante la API pública de asistencia, se registra una cuenta con rol `directivo` y se administran usuarios, estudiantes y documentos.
- **Clasificación:** CWE-269, CWE-862; OWASP A01 Broken Access Control y A07 Identification and Authentication Failures.
- **Recomendación:** Deshabilitar el registro público. Crear usuarios desde una función administrativa o mediante invitaciones de un solo uso, con rol fijado en el servidor y aprobación explícita.
- **Esfuerzo:** Medio.
- **Aceptación:** Una solicitud anónima no puede crear cuentas. Ningún valor enviado por el cliente asigna un rol privilegiado. Las invitaciones expiran, se consumen una vez y quedan auditadas.

### SEG-002 Suplantación y enumeración en asistencia

- **Severidad:** Crítica.
- **Evidencia:** `app/routes/attendance.py:16-86` permite marcar entrada o salida usando únicamente una cédula. `app/routes/attendance.py:92-106` devuelve nombre, apellido y cédula sin autenticación. `app/routes/attendance.py:121-124` expone el estado diario por identificador.
- **Impacto:** Falsificación de asistencia, exposición de identidad y apoyo directo al ataque de SEG-001.
- **Escenario:** Una persona prueba números de cédula, identifica empleados y marca entradas o salidas en su nombre.
- **Clasificación:** CWE-287, CWE-359, CWE-307; OWASP A01 y A07.
- **Recomendación:** Autenticar el kiosco como dispositivo, usar un segundo factor de presencia como credencial NFC, QR rotatorio o PIN protegido, limitar intentos y devolver respuestas indistinguibles para cédulas inexistentes.
- **Esfuerzo:** Alto.
- **Aceptación:** La cédula por sí sola no autoriza marcas; el kiosco necesita una credencial de dispositivo; los intentos se limitan y registran; las APIs públicas no revelan identidad ni estado.

### SEG-003 Ausencia de protección CSRF

- **Severidad:** Alta.
- **Evidencia:** Se encontraron 46 formularios y cero referencias a CSRF, Flask-WTF o WTForms. Las operaciones incluyen roles, contraseñas, usuarios, expedientes médicos, asistencia y documentos.
- **Impacto:** Un sitio externo puede inducir a una sesión autenticada a ejecutar cambios no deseados.
- **Escenario:** Un directivo visita una página maliciosa que envía en segundo plano un cambio de rol o una eliminación.
- **Clasificación:** CWE-352; OWASP A01.
- **Recomendación:** Integrar tokens CSRF globales, comprobarlos en todos los métodos de cambio y exigir `Origin` o `Referer` válido como defensa adicional.
- **Esfuerzo:** Medio.
- **Aceptación:** Toda solicitud POST, PUT, PATCH o DELETE sin token válido recibe 400 o 403; las pruebas cubren tokens ausentes, vencidos y de otra sesión.

### SEG-004 Configuración de producción insegura

- **Severidad:** Alta.
- **Evidencia:** `run.py:12-23` escucha en `0.0.0.0`, activa `debug=True` y permite HTTP. `app/config.py:9` usa `dev-secret-key` si falta la variable. `app/config.py:11-12` usa `root` y contraseña vacía como valores por defecto.
- **Impacto:** Exposición del depurador, falsificación de cookies si se conoce la clave, tráfico en claro y privilegios excesivos en base de datos.
- **Escenario:** Un error accesible desde la red muestra el depurador; una instalación incompleta conserva valores de desarrollo en producción.
- **Clasificación:** CWE-489, CWE-798, CWE-319; OWASP A02 Cryptographic Failures y A05 Security Misconfiguration.
- **Recomendación:** Fallar al arrancar cuando falten secretos, separar configuraciones, ejecutar con un WSGI de producción detrás de TLS y eliminar valores inseguros por defecto.
- **Esfuerzo:** Medio.
- **Aceptación:** Producción no usa el servidor de desarrollo, no arranca sin secretos fuertes, redirige a HTTPS y usa una cuenta MySQL de mínimo privilegio.

### SEG-005 Falta de autorización por estudiante y tipo de dato

- **Severidad:** Alta.
- **Evidencia:** `app/routes/student_profile.py:20-45` permite a cualquier `maestro` consultar por ID un perfil con familia, datos médicos, datos socioeconómicos e historial, sin comprobar que el estudiante pertenezca a sus cursos. `app/routes/evaluations.py:101-111` presenta el mismo patrón para el historial.
- **Impacto:** Acceso horizontal a datos sensibles de menores fuera de la necesidad educativa del usuario.
- **Escenario:** Un maestro cambia el identificador de la URL y consulta expedientes médicos de estudiantes de otros cursos.
- **Clasificación:** CWE-639, CWE-862; OWASP A01.
- **Recomendación:** Implementar políticas por objeto y campo. Un maestro solo debe acceder a estudiantes asignados y los datos médicos completos deben limitarse a roles expresamente autorizados.
- **Esfuerzo:** Alto.
- **Aceptación:** Las pruebas de matriz de permisos niegan acceso cruzado entre cursos y ocultan campos sensibles aunque se conozca el ID.

### SEG-006 Modificación de evaluaciones y estadísticas sin validar pertenencia

- **Severidad:** Alta.
- **Evidencia:** `app/routes/evaluations.py:61-97` permite registrar evaluaciones de cualquier estudiante sin validar el curso. `app/routes/daily_stats.py:47-59` acepta `course_code` del formulario sin comprobarlo contra `courses`. `app/routes/student_profile.py:102-119` actualiza o elimina un familiar por `member_id` sin verificar que pertenezca al `student_id` de la ruta.
- **Impacto:** Manipulación horizontal de calificaciones, estadísticas y relaciones familiares.
- **Escenario:** Un maestro modifica el código de curso o el ID enviado y altera datos fuera de su ámbito.
- **Clasificación:** CWE-639, CWE-863; OWASP A01.
- **Recomendación:** Resolver los objetos desde el usuario actual, comprobar relaciones padre-hijo en la consulta SQL y no confiar en identificadores del formulario.
- **Esfuerzo:** Alto.
- **Aceptación:** Cada mutación valida actor, objeto, relación y permiso en una sola operación transaccional; las pruebas cubren IDOR y cambio de parámetros.

### SEG-007 Revocación y actividad de sesiones inefectivas

- **Severidad:** Alta.
- **Evidencia:** `app/routes/admin.py:100-110` y `150-160` marcan filas de `user_sessions` como inactivas, pero ninguna petición valida esa fila antes de aceptar la cookie Flask-Login. `app/__init__.py:78-82` actualiza todas las sesiones activas de un usuario, no solo la sesión actual.
- **Impacto:** Restablecer una contraseña o desactivar sesiones no expulsa de inmediato a quien conserva una cookie válida; una sesión mantiene vivas las demás.
- **Escenario:** Una cookie robada continúa funcionando después de que el administrador crea haber cerrado las sesiones.
- **Clasificación:** CWE-613, CWE-384; OWASP A07.
- **Recomendación:** Comprobar `session_id` activo en cada petición, actualizar solo esa sesión, rotar el identificador al autenticar y revocar todas las sesiones ante cambios sensibles.
- **Esfuerzo:** Medio.
- **Aceptación:** Una sesión revocada falla en la petición siguiente; las sesiones expiran independientemente; el cambio de contraseña invalida todas las cookies anteriores.

### SEG-008 XSS almacenado en el kiosco

- **Severidad:** Alta.
- **Evidencia:** `app/templates/attendance/clock.html:347-360` inserta `first_name`, `last_name` e `id` de la API mediante `innerHTML`. Esos nombres proceden de datos administrables.
- **Impacto:** Ejecución de JavaScript en el navegador público del kiosco y posible robo de información o alteración de la interfaz.
- **Escenario:** Un nombre de personal contiene marcado malicioso y se ejecuta cuando alguien introduce su cédula.
- **Clasificación:** CWE-79; OWASP A03 Injection.
- **Recomendación:** Construir el contenido con `textContent` y nodos DOM, validar nombres y adoptar una CSP sin scripts inline.
- **Esfuerzo:** Bajo.
- **Aceptación:** Cadenas con etiquetas o eventos se muestran como texto; las pruebas de XSS almacenado no ejecutan código.

### SEG-009 Operaciones destructivas por GET y borrado físico

- **Severidad:** Alta.
- **Evidencia:** Las eliminaciones de estudiantes, docentes, cursos, horarios e inscripciones usan GET en `app/routes/students.py:143`, `teachers.py:126`, `courses.py:103`, `schedule.py:54` y `enrollment.py:65`. El esquema aplica múltiples `ON DELETE CASCADE`, por ejemplo `../estructura_bd.sql:23-24`, `82-83`, `129` y `292`.
- **Impacto:** Activación por enlaces, precarga o CSRF, además de pérdida irreversible de expedientes e historial.
- **Escenario:** Un enlace incrustado elimina un registro; la cascada borra evaluaciones o información médica vinculada.
- **Clasificación:** CWE-352, CWE-650; OWASP A01.
- **Recomendación:** Usar POST o DELETE con CSRF, confirmación reforzada y borrado lógico. Conservar relaciones históricas y reservar la purga para un proceso controlado y auditado.
- **Esfuerzo:** Alto.
- **Aceptación:** GET es idempotente; los registros desactivados conservan historial; la purga requiere autorización adicional, motivo y evento de auditoría.

### AUD-001 Falta de una bitácora general de auditoría

- **Severidad:** Alta.
- **Evidencia:** El código solo registra sesiones y documentos. No existe una tabla o servicio para accesos a expedientes, cambios de rol, restablecimientos, evaluaciones, asistencia, exportaciones, modificaciones médicas o eliminaciones.
- **Impacto:** No se puede reconstruir quién vio o cambió información sensible ni demostrar integridad operativa.
- **Escenario:** Una calificación o ficha médica cambia y no existe evidencia confiable del actor, valor anterior o motivo.
- **Clasificación:** CWE-778; OWASP A09 Security Logging and Monitoring Failures.
- **Recomendación:** Crear una bitácora append-only con actor, sesión, acción, objeto, resultado, marca UTC, request ID, IP tratada según política, motivo y diferencias antes/después redactadas.
- **Esfuerzo:** Alto.
- **Aceptación:** Todas las operaciones sensibles producen eventos consultables; la aplicación no puede actualizar ni borrar eventos; el acceso a la bitácora también queda registrado.

### DATA-001 Esquema incompleto y sin migraciones

- **Severidad:** Alta.
- **Evidencia:** El código usa `documents_log` e `institution_data`, pero no aparecen entre las 20 tablas de `../estructura_bd.sql`. `report_cards` sí aparece y no es usada por el código. El repositorio no contiene migraciones ni esquema versionado.
- **Impacto:** Instalaciones no reproducibles, errores en producción y cambios manuales sin trazabilidad.
- **Escenario:** Una instalación basada en el SQL local falla al generar documentos o editar datos institucionales.
- **Clasificación:** CWE-1104 y OWASP A05.
- **Recomendación:** Adoptar Alembic o una herramienta equivalente, generar una línea base completa y aplicar cambios únicamente mediante migraciones revisadas.
- **Esfuerzo:** Alto.
- **Aceptación:** Una base vacía alcanza el esquema operativo ejecutando migraciones; CI prueba upgrade y downgrade; el estado esperado se documenta.

### PRIV-001 Gobierno insuficiente de datos sensibles

- **Severidad:** Alta.
- **Evidencia:** `../estructura_bd.sql:267-292` almacena alergias, condiciones, medicación e informes psicológicos y neurológicos. También existen datos familiares y socioeconómicos. No hay cifrado de campos, política de retención, consentimiento, registro de lectura ni clasificación de información.
- **Impacto:** Exposición desproporcionada de información de menores y salud, con consecuencias personales y regulatorias.
- **Escenario:** Una cuenta comprometida consulta o exporta expedientes completos sin generar alerta.
- **Clasificación:** CWE-359; OWASP A01 y A02.
- **Recomendación:** Clasificar datos, minimizar campos, cifrar copias y columnas de alta sensibilidad, limitar lectura, definir retención y documentar base legal, consentimiento y respuesta a incidentes.
- **Esfuerzo:** Alto.
- **Aceptación:** Existe inventario de datos, matriz de acceso, retención automatizada, cifrado gestionado y auditoría de cada lectura o exportación sensible.

### SEG-010 Redirección abierta después del login

- **Severidad:** Media.
- **Evidencia:** `app/routes/auth.py:36-37` redirige directamente al parámetro `next` sin validar host ni esquema.
- **Impacto:** Facilita phishing con una URL legítima del sistema que termina en un sitio externo.
- **Clasificación:** CWE-601; OWASP A01.
- **Recomendación:** Aceptar solo rutas relativas del mismo origen mediante una función `is_safe_url` y usar el panel como destino por defecto.
- **Esfuerzo:** Bajo.
- **Aceptación:** URLs absolutas, esquemas alternativos y formas `//host` son rechazadas en pruebas.

### SEG-011 Autenticación sin defensas suficientes

- **Severidad:** Media.
- **Evidencia:** La longitud mínima es seis en `app/routes/admin.py:96`, `profile.py:175` y `templates/register.html:38`. No hay referencias a limitación de intentos, bloqueo, MFA, recuperación segura o alertas de acceso.
- **Impacto:** Mayor probabilidad de fuerza bruta, reutilización de contraseñas y toma de cuentas privilegiadas.
- **Clasificación:** CWE-307, CWE-521; OWASP A07.
- **Recomendación:** Exigir frases largas, comprobar contraseñas comprometidas, limitar por cuenta y origen, ofrecer MFA obligatorio a directivos y definir recuperación mediante token de un solo uso.
- **Esfuerzo:** Medio.
- **Aceptación:** Las pruebas verifican 429, retrasos progresivos, MFA de administradores y tokens de recuperación expirables.

### SEG-012 Cookies, cabeceras, TLS y CDN sin endurecimiento

- **Severidad:** Media.
- **Evidencia:** No existen configuraciones explícitas `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE` ni duración de sesión. No se encontraron CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy` o `Permissions-Policy`. `base.html:8-9,213` y `base_public.html:7-8,168` cargan CDN sin SRI.
- **Impacto:** Menor aislamiento del navegador, riesgo de tráfico en claro y dependencia de terceros sin verificación de integridad.
- **Clasificación:** CWE-614, CWE-319, CWE-353; OWASP A02 y A05.
- **Recomendación:** Configurar cookies Secure, HttpOnly y SameSite; expiración absoluta e inactividad; TLS obligatorio; cabeceras defensivas y recursos locales o con SRI.
- **Esfuerzo:** Medio.
- **Aceptación:** Un escáner de cabeceras verifica la política; las cookies nunca viajan por HTTP; la aplicación funciona con una CSP restrictiva.

### SEG-013 Exposición excesiva en APIs y listados

- **Severidad:** Media.
- **Evidencia:** Las APIs públicas de asistencia revelan identidad y estado. `app/routes/students.py:154-161` devuelve todos los datos del representante a cualquier usuario autenticado que conozca la cédula. `app/routes/teachers.py:12-18` permite listar personal a cualquier usuario autenticado.
- **Impacto:** Enumeración, correlación de identidad y acceso innecesario a datos de contacto.
- **Clasificación:** CWE-200, CWE-359; OWASP A01.
- **Recomendación:** Reducir campos, aplicar permiso específico, registrar consultas y responder con datos mínimos.
- **Esfuerzo:** Medio.
- **Aceptación:** Cada endpoint tiene contrato de datos y prueba de autorización; ningún endpoint anónimo devuelve PII.

### SEG-014 Lectura de archivos mediante la ruta del logo

- **Severidad:** Media.
- **Evidencia:** `app/routes/admin.py:199-211` guarda `logo_path` del formulario. `app/routes/documents.py:27-36` lo concatena con el directorio estático y abre la ruta sin comprobar que permanezca dentro del directorio permitido.
- **Impacto:** Un directivo comprometido podría intentar incluir archivos locales legibles dentro de un PDF.
- **Clasificación:** CWE-22, CWE-73; OWASP A01.
- **Recomendación:** Gestionar el logo como carga validada, almacenar un identificador generado y verificar la ruta resuelta con `commonpath`.
- **Esfuerzo:** Bajo.
- **Aceptación:** Rutas absolutas, `..`, enlaces y extensiones no autorizadas son rechazadas; solo puede leerse el archivo administrado.

### SEG-015 Inyección de fórmulas CSV y caché de información sensible

- **Severidad:** Media.
- **Evidencia:** `app/routes/attendance.py:204-212` escribe nombres y observaciones directamente al CSV. Las respuestas CSV y PDF no establecen `Cache-Control: no-store`.
- **Impacto:** Una celda que comience por `=`, `+`, `-` o `@` puede ejecutar fórmulas al abrirse; navegadores compartidos pueden conservar documentos sensibles.
- **Clasificación:** CWE-1236, CWE-525.
- **Recomendación:** Escapar fórmulas, usar UTF-8 con formato documentado y añadir cabeceras `no-store`, `private` y `nosniff`.
- **Esfuerzo:** Bajo.
- **Aceptación:** Cargas de prueba con fórmulas se abren como texto y las respuestas sensibles no se almacenan en caché.

### SEG-016 Dependencia `xhtml2pdf` con alerta conocida

- **Severidad:** Media.
- **Evidencia:** `requirements.txt` fija `xhtml2pdf==0.2.16`. `pip-audit` reportó `PYSEC-2026-2056`, alias `CVE-2024-25885`, por ReDoS en procesamiento de colores; la salida duplicó el mismo aviso y no indicó versión corregida.
- **Impacto:** Entradas HTML o CSS especialmente construidas podrían consumir CPU durante la generación de PDF si alcanzan la función afectada.
- **Clasificación:** CWE-1333; OWASP A06 Vulnerable and Outdated Components.
- **Recomendación:** Confirmar el rango afectado con el proveedor, actualizar cuando exista solución o migrar el generador. Mientras tanto, limitar entradas, tiempo y recursos del proceso PDF.
- **Esfuerzo:** Medio.
- **Aceptación:** El escaneo deja de reportar la vulnerabilidad o existe una excepción temporal aprobada, fechada y con mitigaciones verificadas.

### AUD-002 Numeración documental no atómica y mutaciones por GET

- **Severidad:** Media.
- **Evidencia:** `app/models/document_log.py:19-31` calcula `MAX(sequence)+1` en una conexión separada de la inserción. `app/routes/documents.py:88-113` emite documentos mediante GET y `documents.py:155-174` incrementa impresiones al abrir el PDF.
- **Impacto:** Números duplicados bajo concurrencia, contadores inexactos y efectos laterales activados por navegación o precarga.
- **Clasificación:** CWE-362, CWE-352.
- **Recomendación:** Reservar números en una transacción con restricción única o secuencia, emitir solo mediante POST con CSRF y registrar eventos de generación y descarga por separado.
- **Esfuerzo:** Medio.
- **Aceptación:** Pruebas concurrentes no producen duplicados; GET no modifica datos; cada emisión y reimpresión conserva actor y motivo.

### AUD-003 Atribución ficticia de acciones

- **Severidad:** Media.
- **Evidencia:** `app/routes/evaluations.py:86-94` usa `teacher_id=1` cuando el usuario no está vinculado. `app/routes/daily_stats.py:131-141` usa el titular o el primer docente disponible como respaldo.
- **Impacto:** Los registros atribuyen una acción a una persona que no la realizó, invalidando informes y auditoría.
- **Clasificación:** CWE-345; OWASP A09.
- **Recomendación:** Separar `performed_by_user_id` de `responsible_teacher_id`, permitir valores nulos cuando corresponda y prohibir respaldos inventados.
- **Esfuerzo:** Medio.
- **Aceptación:** Cada registro identifica al usuario real y, si aplica, al docente responsable; nunca se asigna una identidad arbitraria.

### DATA-002 Conexión MySQL sin controles operativos

- **Severidad:** Media.
- **Evidencia:** `app/utils/db.py:5-16` abre conexiones sin TLS, timeout, agrupación, modo estricto ni identificación de aplicación. La configuración permite `root` y contraseña vacía.
- **Impacto:** Tráfico interno expuesto, agotamiento de conexiones y privilegios excesivos ante una inyección o cuenta comprometida.
- **Clasificación:** CWE-250, CWE-319; OWASP A02 y A05.
- **Recomendación:** Usar un usuario dedicado, TLS verificable, pool limitado, timeouts, modo SQL estricto y credenciales gestionadas fuera del proceso.
- **Esfuerzo:** Medio.
- **Aceptación:** La cuenta no puede administrar el servidor ni tablas ajenas; conexiones sin certificado válido fallan; métricas muestran uso del pool.

### ENG-001 Errores y eventos sin logging estructurado

- **Severidad:** Media.
- **Evidencia:** Hay múltiples `print(e)` y excepciones genéricas. `app/routes/admin.py:163-164` silencia por completo un fallo. `app/models/course.py:90-140` devuelve excepciones que `app/routes/courses.py:66,95,111` muestra al usuario.
- **Impacto:** Fuga de detalles internos, ausencia de correlación y fallos invisibles en operaciones sensibles.
- **Clasificación:** CWE-209, CWE-390, CWE-778; OWASP A09.
- **Recomendación:** Usar logging JSON, niveles, request ID, redacción de PII, códigos de error públicos y alertas para autenticación, permisos y fallos de auditoría.
- **Esfuerzo:** Medio.
- **Aceptación:** Ninguna excepción interna llega al usuario; todos los fallos críticos generan un evento correlacionable sin contraseñas ni datos médicos.

### ENG-002 Validación distribuida e incompleta

- **Severidad:** Media.
- **Evidencia:** Las rutas convierten directamente valores con `int()`, comparan fechas como cadenas y aceptan cantidades de asistencia sin límites. La mayor parte de la validación está duplicada en controladores.
- **Impacto:** Errores 500, datos imposibles, valores negativos y reglas inconsistentes.
- **Clasificación:** CWE-20; OWASP A04 Insecure Design.
- **Recomendación:** Definir esquemas de entrada centralizados, límites, formatos, enumeraciones, normalización y mensajes uniformes; repetir restricciones críticas en la base de datos.
- **Esfuerzo:** Medio.
- **Aceptación:** Pruebas de límites y propiedades rechazan fechas inválidas, números negativos, enumeraciones desconocidas y campos demasiado largos sin producir 500.

### SEG-017 Procesamiento y publicación de imágenes

- **Severidad:** Baja.
- **Evidencia:** `app/routes/profile.py:43-79` valida formato y vuelve a codificar la imagen, lo cual es positivo, pero no trata explícitamente bombas de descompresión. Los avatares se publican bajo `/static`.
- **Impacto:** Consumo excesivo de memoria y exposición permanente de imágenes mediante URL predecible.
- **Clasificación:** CWE-409, CWE-434.
- **Recomendación:** Limitar píxeles y dimensiones antes de decodificar, capturar `DecompressionBombError`, almacenar fuera de estáticos y servir con autorización o URLs no predecibles.
- **Esfuerzo:** Bajo.
- **Aceptación:** Imágenes comprimidas maliciosas se rechazan con consumo acotado; un usuario no autorizado no descarga avatares privados.

### AUD-004 Integridad y retención del registro de sesiones

- **Severidad:** Baja.
- **Evidencia:** `../estructura_bd.sql:368-381` no declara `UNIQUE` para `session_id`. Se almacenan IP, agente y el identificador completo sin política de retención. La limpieza solo se llama desde `app/routes/admin.py:18-19` al abrir una vista.
- **Impacto:** Duplicados, conservación indefinida de datos y sesiones obsoletas si nadie visita la administración.
- **Clasificación:** CWE-613, CWE-359.
- **Recomendación:** Índice único o hash del identificador, tarea programada de expiración y política documentada de retención y acceso.
- **Esfuerzo:** Bajo.
- **Aceptación:** No se admiten duplicados; la expiración funciona sin intervención humana; la retención se aplica y queda medida.

### DATA-003 Restricciones e identificadores del esquema

- **Severidad:** Media.
- **Evidencia:** `../estructura_bd.sql:177-178` repite el índice único de cédula. Las cédulas de docentes se modelan como enteros y numerosas relaciones sensibles usan cascada. No existe restricción que proteja explícitamente un único estado activo de inscripción o valores no negativos.
- **Impacto:** Migraciones frágiles, pérdida de ceros iniciales, borrado de historial e inconsistencias lógicas.
- **Clasificación:** CWE-20, CWE-226.
- **Recomendación:** Usar identificadores internos separados de documentos, normalizar restricciones, eliminar índices duplicados y revisar cada política `ON DELETE` según retención.
- **Esfuerzo:** Medio.
- **Aceptación:** El esquema impide estados inválidos, conserva documentos tal como fueron emitidos y las migraciones corrigen datos incompatibles de forma verificable.

### ENG-003 Falta de pruebas, CI y mantenimiento del repositorio

- **Severidad:** Baja.
- **Evidencia:** No se encontraron pruebas, CI, README, SECURITY, licencia, migraciones ni configuración de calidad. Existen `app/models/respaldouser.py`, `templates/respaldobase.html`, `respaldodashboard.html` y `attendance/2admin_view.html` como respaldos dentro del código. `requirements.txt` mezcla dependencias directas e indirectas sin hashes.
- **Impacto:** Regresiones de permisos difíciles de detectar, incorporación lenta de personal y mayor superficie de código obsoleto.
- **Clasificación:** OWASP A04, A05 y A06.
- **Recomendación:** Añadir pytest, matriz de autorización, CI con SAST, auditoría de dependencias y secretos, documentación de despliegue, política de seguridad y un lock reproducible con hashes. Retirar respaldos después de confirmar que no se usan.
- **Esfuerzo:** Medio.
- **Aceptación:** Cada cambio ejecuta pruebas y escaneos; existe cobertura de rutas sensibles; una instalación nueva sigue documentación versionada; no quedan copias muertas en producción.

## Mejores prácticas recomendadas

### Matriz de acceso

Definir permisos como política central, no como condiciones aisladas en plantillas. La matriz mínima debe cruzar rol, acción, tipo de dato, relación con el curso y estado del registro. Ocultar un botón no sustituye la autorización del servidor. Cada regla debe tener una prueba positiva y otra negativa.

### Bitácora append-only

Registrar `event_id`, fecha UTC, request ID, actor, sesión, acción, tipo e identificador del objeto, resultado, motivo y cambios relevantes. Los valores antes y después deben redactar contraseñas, tokens y contenido médico no necesario. La cuenta de aplicación debe insertar, pero no actualizar ni borrar. Para mayor garantía, encadenar hashes por lote y exportar a un almacenamiento con retención inmutable.

### Privacidad de menores y salud

Aplicar minimización, finalidad explícita, retención, acceso por necesidad y respuesta a solicitudes. Separar campos de salud del perfil académico general. Registrar lecturas y exportaciones, cifrar copias de seguridad, probar restauraciones y disponer de un procedimiento de incidentes que considere a representantes y autoridades aplicables.

### Gestión de identidades

Crear cuentas mediante invitación o administración. Exigir MFA a roles privilegiados, rotar sesiones después del login, ofrecer cierre remoto real y aplicar reautenticación antes de cambios de rol, restablecimientos y exportaciones masivas.

### Plataforma y despliegue

Usar WSGI de producción, proxy inverso, TLS, secretos gestionados, imágenes o servicios con versiones fijadas y una cuenta MySQL de mínimo privilegio. Establecer health checks que no expongan detalles, límites de recursos y alertas sobre errores, accesos denegados, intentos de login y cambios sensibles.

### Desarrollo seguro

Incluir en CI compilación, pruebas, Bandit, `pip-audit`, detección de secretos, lint y pruebas de migración. Revisar dependencias periódicamente, mantener un inventario de componentes y documentar excepciones de seguridad con responsable y fecha de caducidad.

## Hoja de ruta

### P0 Antes de cualquier exposición adicional

1. Deshabilitar el autorregistro privilegiado.
2. Desactivar depuración, exigir secretos fuertes y HTTPS.
3. Añadir CSRF y convertir toda eliminación a método de estado.
4. Corregir el kiosco, cerrar APIs de enumeración y eliminar `innerHTML` con datos.
5. Aplicar autorización por objeto a expedientes, evaluaciones y cursos.

### P1 Antes de uso operativo confiable

1. Implantar revocación real de sesiones, rate limiting y MFA administrativo.
2. Crear bitácora append-only y eliminaciones lógicas.
3. Introducir migraciones y completar `documents_log` e `institution_data`.
4. Corregir atribución de acciones, numeración documental y acceso al logo.
5. Endurecer cookies, cabeceras, TLS y recursos externos.

### P2 Protección de datos y operación

1. Definir clasificación, retención, cifrado, copias y restauración.
2. Endurecer MySQL, validación, exportaciones y cargas de archivos.
3. Resolver o mitigar la vulnerabilidad de `xhtml2pdf`.
4. Implantar logging estructurado, métricas y alertas.

### P3 Mantenibilidad

1. Añadir pruebas, CI, documentación y política de seguridad.
2. Retirar respaldos de código y generar un lock con hashes.
3. Medir cobertura de autorización y revisar la matriz en cada cambio funcional.

## Diferencias entre intranet e Internet

En intranet siguen siendo obligatorios CSRF, autorización por objeto, sesiones revocables, auditoría, protección de datos, HTTPS y eliminaciones seguras. La red escolar no debe considerarse confiable porque incluye equipos compartidos, dispositivos personales y riesgo de credenciales comprometidas.

Antes de exponer el sistema a Internet también son bloqueantes el cierre completo de APIs públicas de identidad, rate limiting distribuido, MFA para roles privilegiados, proxy de producción, gestión de secretos, monitoreo continuo, copias cifradas, respuesta a incidentes y pruebas externas de penetración.

## Controles positivos observados

- Las consultas revisadas usan parámetros `%s` en lugar de concatenar valores en SQL.
- Las contraseñas se almacenan con bcrypt.
- La carga de avatares limita tamaño, comprueba la imagen y vuelve a codificarla como JPEG.
- `.gitignore` excluye `.env`, certificados, bases de datos, SQL y archivos subidos.
- Existen decoradores de rol y separación por blueprints.
- La búsqueda del historial no encontró secretos reales.

Estos controles reducen riesgo, pero no compensan los problemas de autorización, configuración y trazabilidad descritos.

## Limitaciones

La revisión fue estática. No se validaron configuración real de MySQL, proxy, TLS, copias, permisos del sistema operativo ni datos desplegados. Tampoco se intentó explotar el sistema. Después de corregir P0 y P1 debe ejecutarse una evaluación dinámica con una base de prueba, pruebas de concurrencia documental y una revisión de privacidad según la jurisdicción aplicable.
