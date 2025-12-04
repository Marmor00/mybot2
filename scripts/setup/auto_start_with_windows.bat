@echo off
REM ====================================
REM  AUTO START CON WINDOWS
REM  Inicia el scheduler cuando prendes la PC
REM ====================================

echo.
echo ====================================
echo   CONFIGURAR AUTO-START CON WINDOWS
echo ====================================
echo.
echo Este script agregara el scheduler al inicio de Windows
echo para que se ejecute automaticamente cuando prendas tu PC.
echo.
pause

REM Obtener ruta actual
set SCRIPT_DIR=%~dp0
set PYTHON_EXE=python
set SCHEDULER_SCRIPT=%SCRIPT_DIR%auto_scheduler.py
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

echo.
echo Creando acceso directo en carpeta de inicio...
echo.

REM Crear VBS script para crear shortcut (porque batch no puede)
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%STARTUP_FOLDER%\InsiderTradingScheduler.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%PYTHON_EXE%" >> CreateShortcut.vbs
echo oLink.Arguments = """%SCHEDULER_SCRIPT%""" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%SCRIPT_DIR%" >> CreateShortcut.vbs
echo oLink.Description = "Insider Trading Auto Scheduler" >> CreateShortcut.vbs
echo oLink.WindowStyle = 7 >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs

REM Ejecutar VBS
cscript CreateShortcut.vbs >nul

REM Limpiar VBS temporal
del CreateShortcut.vbs

echo.
echo ====================================
echo   CONFIGURACION COMPLETADA
echo ====================================
echo.
echo El scheduler ahora se iniciara automaticamente cuando prendas tu PC.
echo.
echo Ubicacion del acceso directo:
echo   %STARTUP_FOLDER%\InsiderTradingScheduler.lnk
echo.
echo Para desactivar:
echo   1. Ve a la carpeta de inicio (Win+R -> shell:startup)
echo   2. Elimina el acceso directo "InsiderTradingScheduler"
echo.
echo Para probarlo ahora:
echo   python auto_scheduler.py
echo.
pause
