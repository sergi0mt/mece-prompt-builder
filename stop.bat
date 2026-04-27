@echo off
REM Detiene el backend (8000) y frontend (3000)

echo Deteniendo backend y frontend...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

REM Tambien matar ventanas por titulo
taskkill /FI "WINDOWTITLE eq MECE Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq MECE Frontend*" /F >nul 2>&1

echo [OK] Servidores detenidos.
timeout /t 2 /nobreak >nul
