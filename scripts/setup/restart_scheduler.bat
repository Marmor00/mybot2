@echo off
echo.
echo ====================================
echo   REINICIANDO SCHEDULER
echo ====================================
echo.

echo Deteniendo scheduler antiguo...
taskkill /F /IM pythonw.exe >nul 2>&1

timeout /t 2 /nobreak >nul

echo Iniciando scheduler con alertas inteligentes...
start /min pythonw auto_scheduler.py

timeout /t 2 /nobreak >nul

echo.
echo Verificando...
tasklist | findstr pythonw

echo.
echo ====================================
echo   SCHEDULER REINICIADO
echo ====================================
echo.
echo Ahora el scheduler enviara alertas Telegram SOLO cuando:
echo   - Hay oportunidades Score 85+ HOT (0-3 dias)
echo   - Paper trading ejecuto auto-compras hoy
echo.
echo Esto evita spam en dias sin oportunidades importantes.
echo.
pause
