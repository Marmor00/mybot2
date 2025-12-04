# PowerShell script para crear tarea programada
# Ejecutar: powershell -ExecutionPolicy Bypass -File setup_automation.ps1

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  CONFIGURANDO AUTOMATIZACION" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Parametros
$TaskName = "InsiderTradingDailyScraper"
$PythonPath = "C:\Users\MM\anaconda3\python.exe"
$ScriptPath = "c:\Users\MM\expedientes-app\trading\Bot2\daily_scraper.py"
$WorkingDir = "c:\Users\MM\expedientes-app\trading\Bot2"
$Time = "18:00"

# Verificar que Python existe
if (!(Test-Path $PythonPath)) {
    Write-Host "ERROR: No se encontro Python en $PythonPath" -ForegroundColor Red
    Write-Host "Buscando Python..." -ForegroundColor Yellow
    $PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($PythonPath) {
        Write-Host "Python encontrado en: $PythonPath" -ForegroundColor Green
    } else {
        Write-Host "No se pudo encontrar Python. Abortando." -ForegroundColor Red
        exit 1
    }
}

# Verificar que el script existe
if (!(Test-Path $ScriptPath)) {
    Write-Host "ERROR: No se encontro el script en $ScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "Python: $PythonPath" -ForegroundColor Gray
Write-Host "Script: $ScriptPath" -ForegroundColor Gray
Write-Host "Hora: $Time diario" -ForegroundColor Gray
Write-Host ""

# Eliminar tarea existente si existe
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "Eliminando tarea existente..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Crear accion (comando a ejecutar)
$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "`"$ScriptPath`" --no-alerts" `
    -WorkingDirectory $WorkingDir

# Crear trigger (cuando ejecutar)
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time

# Crear configuracion
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Crear principal (usuario que ejecuta)
$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U `
    -RunLevel Limited

# Registrar tarea
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "Ejecuta el scraper de insider trading diariamente a las 6 PM" `
        -ErrorAction Stop | Out-Null

    Write-Host ""
    Write-Host "====================================" -ForegroundColor Green
    Write-Host "  TAREA CREADA EXITOSAMENTE" -ForegroundColor Green
    Write-Host "====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "El scraper se ejecutara AUTOMATICAMENTE:" -ForegroundColor White
    Write-Host "  - Todos los dias a las 6:00 PM" -ForegroundColor White
    Write-Host "  - Sin alertas de Telegram" -ForegroundColor White
    Write-Host ""
    Write-Host "Proxima ejecucion:" -ForegroundColor Cyan
    $Task = Get-ScheduledTask -TaskName $TaskName
    $NextRun = (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
    Write-Host "  $NextRun" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Para ver la tarea:" -ForegroundColor Gray
    Write-Host "  schtasks /Query /TN `"$TaskName`"" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Para ejecutar manualmente ahora:" -ForegroundColor Gray
    Write-Host "  schtasks /Run /TN `"$TaskName`"" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Para eliminar:" -ForegroundColor Gray
    Write-Host "  schtasks /Delete /TN `"$TaskName`" /F" -ForegroundColor DarkGray
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "ERROR: No se pudo crear la tarea" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Intenta ejecutar PowerShell como ADMINISTRADOR" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
