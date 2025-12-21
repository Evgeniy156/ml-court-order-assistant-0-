# Скрипт для запуска FastAPI сервера
# Использование: .\run-server.ps1

# Установить переменные окружения
$env:DATABASE_URL = "sqlite:///./dev.db"
$env:SECRET_KEY = "c995a7f66246b6026ffdab5275ba3f79ede6aed139193740178c89200eeacf09"

# Проверить, что мы в правильной директории
if (-not (Test-Path "app\src\main.py")) {
    Write-Host "ОШИБКА: Файл app\src\main.py не найден!" -ForegroundColor Red
    Write-Host "Убедитесь, что вы запускаете скрипт из корневой директории проекта" -ForegroundColor Yellow
    Write-Host "Текущая директория: $(Get-Location)" -ForegroundColor Yellow
    exit 1
}

Write-Host "Запуск FastAPI сервера..." -ForegroundColor Green
Write-Host "API документация будет доступна по адресу: http://localhost:8000/docs" -ForegroundColor Cyan

# Запустить сервер
uvicorn app.src.main:app --host 0.0.0.0 --port 8000

