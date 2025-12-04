@echo off
echo ====================================
echo   Insider Trading App - Quick Start
echo ====================================
echo.

:menu
echo Selecciona una opcion:
echo.
echo 1. Configurar Bot de Telegram (primera vez)
echo 2. Probar Telegram (enviar alertas de prueba)
echo 3. Ejecutar Daily Scraper (con alertas)
echo 4. Ejecutar Daily Scraper (sin alertas)
echo 5. Abrir Dashboard
echo 6. Instalar/Actualizar dependencias
echo 7. Salir
echo.

set /p choice="Ingresa numero (1-7): "

if "%choice%"=="1" goto setup_telegram
if "%choice%"=="2" goto test_telegram
if "%choice%"=="3" goto run_scraper
if "%choice%"=="4" goto run_scraper_no_alerts
if "%choice%"=="5" goto open_dashboard
if "%choice%"=="6" goto install_deps
if "%choice%"=="7" goto exit

echo Opcion invalida. Intenta de nuevo.
echo.
goto menu

:setup_telegram
echo.
echo === Configurando Telegram Bot ===
echo.
python telegram_bot.py setup
echo.
pause
goto menu

:test_telegram
echo.
echo === Probando Telegram (enviando alertas de prueba) ===
echo.
python telegram_bot.py test
echo.
pause
goto menu

:run_scraper
echo.
echo === Ejecutando Daily Scraper con Alertas ===
echo Esto puede tomar 3-5 minutos...
echo.
python daily_scraper.py
echo.
echo Listo! Revisa tu Telegram si habia oportunidades nuevas.
echo.
pause
goto menu

:run_scraper_no_alerts
echo.
echo === Ejecutando Daily Scraper SIN Alertas ===
echo Esto puede tomar 3-5 minutos...
echo.
python daily_scraper.py --no-alerts
echo.
echo Listo!
echo.
pause
goto menu

:open_dashboard
echo.
echo === Abriendo Dashboard ===
echo.
echo Dashboard iniciado en: http://localhost:5000
echo.
echo Presiona Ctrl+C para detener el servidor cuando termines.
echo.
python app.py
pause
goto menu

:install_deps
echo.
echo === Instalando/Actualizando Dependencias ===
echo.
pip install -r requirements.txt
echo.
echo Dependencias instaladas!
echo.
pause
goto menu

:exit
echo.
echo Hasta luego!
exit
