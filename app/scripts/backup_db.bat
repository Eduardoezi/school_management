@echo off
REM ============================================================
REM Backup de MySQL — Sistema Escolar (Windows)
REM Uso: scripts\backup_db.bat
REM ============================================================
setlocal enabledelayedexpansion

REM Cargar variables del .env
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" set "%%a=%%b"
)

if "%MYSQL_USER%"=="" (
    echo ERROR: MYSQL_USER no definido en .env
    exit /b 1
)

set BACKUP_DIR=backups
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set FECHA=%%i
set ARCHIVO=%BACKUP_DIR%\school_db_%FECHA%.sql

echo [%DATE% %TIME%] Backup -> %ARCHIVO%

"C:\xampp\mysql\bin\mysqldump.exe" ^
    -h %MYSQL_HOST% ^
    -P %MYSQL_PORT% ^
    -u %MYSQL_USER% ^
    -p%MYSQL_PASSWORD% ^
    --single-transaction ^
    --routines ^
    --triggers ^
    --events ^
    --databases %MYSQL_DB% > "%ARCHIVO%"

if errorlevel 1 (
    echo ERROR: fallo el backup
    exit /b 1
)

where gzip >nul 2>nul
if %errorlevel%==0 (
    gzip "%ARCHIVO%"
    echo Backup comprimido: %ARCHIVO%.gz
) else (
    echo Backup generado: %ARCHIVO%
)

REM Rotar: borrar backups > 30 dias
forfiles /p "%BACKUP_DIR%" /m *.sql* /d -30 /c "cmd /c del @path" 2>nul

echo [%DATE% %TIME%] OK
endlocal