# CHECKLIST manual — items no automatizables

## INF-02 — Despliegue en producción
- [ ] El servicio systemd / Apache usa `serve.py` (Waitress), no `run.py`.
- [ ] Apache/Nginx hace SSL y Waitress escucha solo en 127.0.0.1.
- [ ] `ProxyFix` está aplicado en el servidor real (verificado con `X-Forwarded-Proto`).
- [ ] Firewall bloquea el puerto interno de Waitress desde fuera de la máquina.

## INF-05 — Migraciones
- [ ] Cada cambio de esquema tiene su archivo numerado en `migrations/`.
- [ ] Existe un `README.md` explicando cómo aplicar migraciones.
- [ ] Existe script de rollback probado al menos una vez.
- [ ] La BD de producción tiene tabla de control (`schema_version` o similar).

## INF-06 — Dependencias
- [ ] `pip-compile --generate-hashes` genera hashes en requirements.txt.
- [ ] Se hace `pip install --require-hashes -r requirements.txt` en el server.
- [ ] `requirements-dev.txt` no se instala en producción.

## INF-07 — Operación
- [ ] GitHub Actions corre lint + tests en cada push.
- [ ] Existe `docker-compose.yml` probado en limpio.
- [ ] Backup automático diario (cron / Task Scheduler) y verificado.
- [ ] Restauración de backup probada al menos una vez (documentada con fecha).
- [ ] Logs rotativos configurados (logrotate o similar).
- [ ] Monitoreo de `/health` con alerta (UptimeRobot, systemd, etc.).
- [ ] Existe entorno de staging separado de producción.