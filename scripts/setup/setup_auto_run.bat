@echo off
REM ====================================
REM  CONFIGURACION AUTOMATICA
REM  Crea tarea programada en Windows
REM ====================================

echo.
echo ====================================
echo   CONFIGURACION DE EJECUCION AUTOMATICA
echo ====================================
echo.
echo Este script va a crear una tarea programada en Windows
echo que ejecutara el scraper TODOS LOS DIAS a las 6:00 PM
echo (despues del cierre del mercado USA)
echo.
echo IMPORTANTE: Ejecuta este archivo como ADMINISTRADOR
echo (click derecho -> Ejecutar como administrador)
echo.
pause

REM Obtener ruta actual
set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%daily_scraper.py
set LOG_FILE=%SCRIPT_DIR%logs\auto_scraper.log

REM Crear directorio de logs si no existe
if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"

echo.
echo Creando tarea programada...
echo.

REM Eliminar tarea existente si existe
schtasks /Delete /TN "InsiderTradingDailyScraper" /F >nul 2>&1

REM Crear nueva tarea programada
REM Se ejecuta diariamente a las 18:00 (6 PM)
schtasks /Create ^
  /TN "InsiderTradingDailyScraper" ^
  /TR "python \"%PYTHON_SCRIPT%\" --no-alerts >> \"%LOG_FILE%\" 2>&1" ^
  /SC DAILY ^
  /ST 18:00 ^
  /RL HIGHEST ^
  /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================
    echo   TAREA CREADA EXITOSAMENTE
    echo ====================================
    echo.
    echo El scraper se ejecutara AUTOMATICAMENTE:
    echo   - Todos los dias a las 6:00 PM
    echo   - Sin alertas de Telegram
    echo   - Logs guardados en: logs\auto_scraper.log
    echo.
    echo Para ver la tarea:
    echo   1. Abre "Programador de tareas" en Windows
    echo   2. Busca "InsiderTradingDailyScraper"
    echo.
    echo Para cambiar la hora:
    echo   1. Abre la tarea en el Programador
    echo   2. Ve a "Desencadenadores" y edita
    echo.
    echo Para desactivar:
    echo   schtasks /Delete /TN "InsiderTradingDailyScraper" /F
    echo.
) else (
    echo.
    echo ERROR: No se pudo crear la tarea.
    echo.
    echo Posibles razones:
    echo   1. No ejecutaste como ADMINISTRADOR
    echo   2. El Programador de tareas esta deshabilitado
    echo.
    echo Solucion:
    echo   - Click derecho en este archivo
    echo   - Selecciona "Ejecutar como administrador"
    echo.
)

pause
