@echo off
REM Crear tarea programada para ejecutar scraper diariamente

echo.
echo ====================================
echo   CREANDO TAREA PROGRAMADA
echo ====================================
echo.

REM Eliminar tarea existente si existe
schtasks /Delete /TN "InsiderTradingDailyScraper" /F >nul 2>&1

REM Crear nueva tarea
schtasks /Create ^
  /TN "InsiderTradingDailyScraper" ^
  /TR "\"C:\Users\MM\anaconda3\python.exe\" \"c:\Users\MM\expedientes-app\trading\Bot2\daily_scraper.py\" --no-alerts" ^
  /SC DAILY ^
  /ST 18:00 ^
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
    echo.
    echo Para verificar:
    echo   schtasks /Query /TN "InsiderTradingDailyScraper"
    echo.
    echo Para ejecutar manualmente ahora:
    echo   schtasks /Run /TN "InsiderTradingDailyScraper"
    echo.
    echo Para eliminar:
    echo   schtasks /Delete /TN "InsiderTradingDailyScraper" /F
    echo.
) else (
    echo.
    echo ERROR: No se pudo crear la tarea.
    echo.
    echo Intentando con metodo alternativo...
    echo.

    REM Crear XML para la tarea
    echo ^<?xml version="1.0" encoding="UTF-16"?^> > task.xml
    echo ^<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"^> >> task.xml
    echo   ^<Triggers^> >> task.xml
    echo     ^<CalendarTrigger^> >> task.xml
    echo       ^<StartBoundary^>2025-01-01T18:00:00^</StartBoundary^> >> task.xml
    echo       ^<ScheduleByDay^> >> task.xml
    echo         ^<DaysInterval^>1^</DaysInterval^> >> task.xml
    echo       ^</ScheduleByDay^> >> task.xml
    echo     ^</CalendarTrigger^> >> task.xml
    echo   ^</Triggers^> >> task.xml
    echo   ^<Actions^> >> task.xml
    echo     ^<Exec^> >> task.xml
    echo       ^<Command^>C:\Users\MM\anaconda3\python.exe^</Command^> >> task.xml
    echo       ^<Arguments^>"c:\Users\MM\expedientes-app\trading\Bot2\daily_scraper.py" --no-alerts^</Arguments^> >> task.xml
    echo       ^<WorkingDirectory^>c:\Users\MM\expedientes-app\trading\Bot2^</WorkingDirectory^> >> task.xml
    echo     ^</Exec^> >> task.xml
    echo   ^</Actions^> >> task.xml
    echo ^</Task^> >> task.xml

    schtasks /Create /XML task.xml /TN "InsiderTradingDailyScraper" /F
    del task.xml

    if %ERRORLEVEL% EQU 0 (
        echo.
        echo Tarea creada con metodo alternativo!
        echo.
    ) else (
        echo.
        echo No se pudo crear la tarea automaticamente.
        echo Por favor ejecuta este archivo como ADMINISTRADOR.
        echo.
    )
)

echo.
pause
