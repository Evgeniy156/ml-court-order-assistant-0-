# Скрипт для сборки и запуска через docker build (обход проблемы с кириллицей в путях)

Write-Host "Сборка образа app..." -ForegroundColor Green
docker build -t ml-court-app -f app/Dockerfile .

Write-Host "Запуск сервисов..." -ForegroundColor Green
docker-compose up -d database rabbitmq

Write-Host "Ожидание готовности БД..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "Запуск app контейнера..." -ForegroundColor Green
docker run -d `
  --name app `
  --network ml-court-order-assistant-0--main_default `
  -e DATABASE_URL=postgresql://postgres:postgres@database:5432/ml_court `
  -e SECRET_KEY=your-secret-key-change-in-production `
  -e RABBITMQ_HOST=rabbitmq `
  -e RABBITMQ_PORT=5672 `
  -e RABBITMQ_USER=guest `
  -e RABBITMQ_PASSWORD=guest `
  -e RABBITMQ_QUEUE=ml_tasks `
  -v "${PWD}/app:/app" `
  -p 8000:8000 `
  ml-court-app

Write-Host "Запуск nginx..." -ForegroundColor Green
docker-compose up -d web-proxy

Write-Host "Готово! Сервисы запущены." -ForegroundColor Green
Write-Host "Веб-интерфейс: http://localhost" -ForegroundColor Cyan
Write-Host "API документация: http://localhost/docs" -ForegroundColor Cyan

