# Скрипт для запуска всех сервисов проекта

Write-Host "Проверка конфликтующих контейнеров..." -ForegroundColor Yellow

# Удаляем старые контейнеры проекта, если они есть
$containers = @("rabbitmq", "database", "app", "web-proxy")
foreach ($container in $containers) {
    $exists = docker ps -a --filter "name=^${container}$" --format "{{.Names}}" 2>$null
    if ($exists -eq $container) {
        Write-Host "Удаление контейнера $container..." -ForegroundColor Yellow
        docker rm -f $container 2>$null
    }
}

Write-Host "Запуск docker-compose..." -ForegroundColor Green
docker-compose up -d

Write-Host "Ожидание инициализации сервисов..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "`nСтатус контейнеров:" -ForegroundColor Cyan
docker-compose ps

Write-Host "`nПроверка логов app..." -ForegroundColor Cyan
docker-compose logs app --tail 20

Write-Host "`nПроверка логов web-proxy..." -ForegroundColor Cyan
docker-compose logs web-proxy --tail 10

Write-Host "`nГотово! Сервисы должны быть доступны на:" -ForegroundColor Green
Write-Host "  - API: http://localhost:80" -ForegroundColor Cyan
Write-Host "  - Health: http://localhost:80/health" -ForegroundColor Cyan
Write-Host "  - Docs: http://localhost:80/docs" -ForegroundColor Cyan

