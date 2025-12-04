@echo off
REM Instalar auto-inicio sin permisos de administrador

echo.
echo ====================================
echo   INSTALANDO AUTO-INICIO
echo ====================================
echo.
echo Este script configurara el scheduler para que se inicie
echo automaticamente cuando prendas tu PC.
echo.
echo NO requiere permisos de administrador.
echo.
pause

REM Obtener carpeta de inicio
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

REM Crear acceso directo usando VBScript
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%STARTUP%\InsiderTradingScheduler.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "C:\Users\MM\anaconda3\pythonw.exe" >> CreateShortcut.vbs
echo oLink.Arguments = """%~dp0auto_scheduler.py""" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%~dp0" >> CreateShortcut.vbs
echo oLink.Description = "Insider Trading Auto Scheduler" >> CreateShortcut.vbs
echo oLink.WindowStyle = 7 >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs

REM Ejecutar VBScript
cscript //Nologo CreateShortcut.vbs

REM Limpiar
del CreateShortcut.vbs

echo.
echo ====================================
echo   INSTALACION COMPLETADA
echo ====================================
echo.
echo El scheduler se iniciara automaticamente cuando prendas tu PC.
echo.
echo Ubicacion:
echo   %STARTUP%\InsiderTradingScheduler.lnk
echo.
echo Para iniciarlo ahora sin reiniciar:
echo   pythonw auto_scheduler.py
echo.
echo Para desinstalarlo:
echo   Del "%STARTUP%\InsiderTradingScheduler.lnk"
echo.
echo IMPORTANTE:
echo   - El scheduler se ejecutara en segundo plano (sin ventana)
echo   - Logs en: logs\auto_scraper_YYYYMMDD.log
echo   - Ejecutara el scraper diariamente a las 6 PM
echo.
pause
