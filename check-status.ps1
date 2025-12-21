# Скрипт для проверки статуса всех компонентов системы
# Использование: .\check-status.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  System Status Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Проверка Docker контейнеров
Write-Host "1. Docker Containers Status:" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Gray
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $containers = docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>$null
    if ($containers) {
        Write-Host $containers
    } else {
        Write-Host "No Docker containers found" -ForegroundColor Gray
    }
    Write-Host ""
    
    # Проверка конкретных контейнеров проекта
    $projectContainers = @("app", "database", "rabbitmq", "web-proxy")
    Write-Host "Project containers:" -ForegroundColor Cyan
    foreach ($container in $projectContainers) {
        $status = docker ps -a --filter "name=^${container}$" --format "{{.Status}}" 2>$null
        if ($status) {
            $isRunning = docker ps --filter "name=^${container}$" --format "{{.Names}}" 2>$null
            if ($isRunning) {
                Write-Host "  $container : RUNNING - $status" -ForegroundColor Green
            } else {
                Write-Host "  $container : STOPPED - $status" -ForegroundColor Red
            }
        } else {
            Write-Host "  $container : NOT FOUND" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "Docker is not installed or not in PATH" -ForegroundColor Red
}
Write-Host ""

# 2. Проверка Telegram бота
Write-Host "2. Telegram Bot Status:" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Gray
$botProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
    $cmdLine -and $cmdLine -like "*telegram_bot*"
}
if ($botProcess) {
    Write-Host "Bot is RUNNING" -ForegroundColor Green
    Write-Host "  PID: $($botProcess.Id)" -ForegroundColor Cyan
    Write-Host "  Start Time: $($botProcess.StartTime)" -ForegroundColor Cyan
} else {
    Write-Host "Bot is NOT RUNNING" -ForegroundColor Red
    Write-Host "  To start: .\scripts\run_telegram_bot.ps1" -ForegroundColor Yellow
}
Write-Host ""

# 3. Проверка локального сервера (FastAPI)
Write-Host "3. Localhost Server Status:" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Gray

# Проверка процесса uvicorn
$serverProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
    $cmdLine -and ($cmdLine -like "*uvicorn*" -or $cmdLine -like "*app.src.main*")
}
if ($serverProcess) {
    Write-Host "Server process is RUNNING" -ForegroundColor Green
    Write-Host "  PID: $($serverProcess.Id)" -ForegroundColor Cyan
    Write-Host "  Start Time: $($serverProcess.StartTime)" -ForegroundColor Cyan
} else {
    Write-Host "Server process is NOT RUNNING" -ForegroundColor Red
}

# Проверка доступности эндпоинтов
Write-Host ""
Write-Host "Checking endpoints:" -ForegroundColor Cyan

$endpoints = @(
    @{Url="http://localhost:8000/health"; Name="Health Check (8000)"},
    @{Url="http://localhost:80/health"; Name="Health Check (80)"},
    @{Url="http://localhost:8000/docs"; Name="API Docs (8000)"},
    @{Url="http://localhost:80/docs"; Name="API Docs (80)"}
)

foreach ($endpoint in $endpoints) {
    try {
        $response = Invoke-WebRequest -Uri $endpoint.Url -Method Get -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  $($endpoint.Name) : OK (Status: $($response.StatusCode))" -ForegroundColor Green
    } catch {
        $status = if ($_.Exception.Response) { $_.Exception.Response.StatusCode } else { "Connection failed" }
        Write-Host "  $($endpoint.Name) : FAILED - $status" -ForegroundColor Red
    }
}

Write-Host ""

# 4. Проверка переменных окружения
Write-Host "4. Environment Variables:" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Gray
$envVars = @("TELEGRAM_BOT_TOKEN", "DATABASE_URL", "SECRET_KEY")
foreach ($var in $envVars) {
    $value = [Environment]::GetEnvironmentVariable($var, "Process")
    if ($value) {
        if ($var -eq "TELEGRAM_BOT_TOKEN") {
            $displayValue = if ($value.Length -gt 20) { $value.Substring(0, 20) + "..." } else { $value }
            Write-Host "  $var : SET ($displayValue)" -ForegroundColor Green
        } elseif ($var -eq "SECRET_KEY") {
            $displayValue = if ($value.Length -gt 20) { $value.Substring(0, 20) + "..." } else { $value }
            Write-Host "  $var : SET ($displayValue)" -ForegroundColor Green
        } else {
            Write-Host "  $var : SET ($value)" -ForegroundColor Green
        }
    } else {
        Write-Host "  $var : NOT SET" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Status Check Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

