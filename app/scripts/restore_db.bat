@echo off
REM Restaurar un backup .sql
REM Uso: scripts\restore_db.bat backups\school_db_2026-01-15.sql
setlocal

if "%~1"=="" (
    echo Uso: restore_db.bat ^<archivo.sql^>
    exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" set "%%a=%%b"
)

echo Restaurando %~1 sobre %MYSQL_DB% ...
"C:\xampp\mysql\bin\mysql.exe" ^
    -h %MYSQL_HOST% -P %MYSQL_PORT% ^
    -u %MYSQL_USER% -p%MYSQL_PASSWORD% < "%~1"

if errorlevel 1 (echo ERROR & exit /b 1)
echo OK
endlocal