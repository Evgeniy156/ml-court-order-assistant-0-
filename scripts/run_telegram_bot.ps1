# Скрипт для запуска Telegram бота

Write-Host "Проверка переменных окружения..." -ForegroundColor Yellow

$botToken = $env:TELEGRAM_BOT_TOKEN
if (-not $botToken -or $botToken -eq "your-telegram-bot-token") {
    Write-Host "❌ TELEGRAM_BOT_TOKEN не установлен!" -ForegroundColor Red
    Write-Host "Получите токен у @BotFather в Telegram" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Установите токен:" -ForegroundColor Cyan
    Write-Host '  $env:TELEGRAM_BOT_TOKEN="your-token-here"' -ForegroundColor White
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
Write-Host "Запуск Telegram бота..." -ForegroundColor Green
Write-Host "Для остановки нажмите Ctrl+C" -ForegroundColor Yellow
Write-Host ""

# Запуск бота
python -m app.src.telegram_bot

