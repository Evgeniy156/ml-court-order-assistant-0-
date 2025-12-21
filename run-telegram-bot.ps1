# Скрипт для запуска Telegram бота
# Использование: .\run-telegram-bot.ps1

Write-Host "=== Starting Telegram Bot ===" -ForegroundColor Cyan
Write-Host ""

# Проверка, что мы в правильной директории
if (-not (Test-Path "app\src\telegram_bot.py")) {
    Write-Host "ERROR: File app\src\telegram_bot.py not found!" -ForegroundColor Red
    Write-Host "Make sure you run the script from project root directory" -ForegroundColor Yellow
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    exit 1
}

# Проверка токена
$botToken = $env:TELEGRAM_BOT_TOKEN
if (-not $botToken -or $botToken -eq "" -or $botToken -eq "your-telegram-bot-token") {
    Write-Host "❌ TELEGRAM_BOT_TOKEN не установлен!" -ForegroundColor Red
    Write-Host ""
    Write-Host "To run the bot you need:" -ForegroundColor Yellow
    Write-Host "1. Open Telegram and find @BotFather" -ForegroundColor White
    Write-Host "2. Send /newbot command" -ForegroundColor White
    Write-Host "3. Follow instructions to create a bot" -ForegroundColor White
    Write-Host "4. Copy the received token" -ForegroundColor White
    Write-Host ""
    Write-Host "Then set the token:" -ForegroundColor Cyan
    Write-Host '  $env:TELEGRAM_BOT_TOKEN="your-token-here"' -ForegroundColor White
    Write-Host ""
    Write-Host "Or run the script again after setting the token" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ TELEGRAM_BOT_TOKEN установлен" -ForegroundColor Green

# Проверка DATABASE_URL
if (-not $env:DATABASE_URL) {
    Write-Host "⚠️  DATABASE_URL не установлен, используется значение по умолчанию" -ForegroundColor Yellow
    $env:DATABASE_URL = "sqlite:///./dev.db"
}

Write-Host "DATABASE_URL: $env:DATABASE_URL" -ForegroundColor Cyan
Write-Host ""

# Проверка, не запущен ли бот уже
$botProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
    $_.CommandLine -like "*telegram_bot*" 
}
if ($botProcess) {
    Write-Host "WARNING: Bot seems to be already running (PID: $($botProcess.Id))" -ForegroundColor Yellow
    Write-Host "Stop the previous process before starting a new one" -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Continue? (y/n)"
    if ($response -ne "y" -and $response -ne "Y") {
        exit 0
    }
}

Write-Host "Starting Telegram bot..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Запуск бота
try {
    python -m app.src.telegram_bot
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to start bot:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

