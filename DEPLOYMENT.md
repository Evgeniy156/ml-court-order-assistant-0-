# Инструкция по развертыванию веб-интерфейса

## Обзор

Проект включает:
- **Backend**: FastAPI приложение с REST API и WebSocket
- **Frontend**: React приложение на TypeScript с Vite
- **Infrastructure**: Docker Compose с PostgreSQL, RabbitMQ, Nginx

## Быстрый старт

### 1. Подготовка окружения

```bash
# Убедитесь, что установлены:
# - Docker и Docker Compose
# - Node.js 18+ (для разработки фронтенда)
# - Python 3.10+ (для разработки бэкенда)
```

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# Database
DATABASE_URL=postgresql://postgres:REPLACE_PASSWORD@database:5432/ml_court

# PostgreSQL credentials
POSTGRES_DB=ml_court
POSTGRES_USER=postgres
POSTGRES_PASSWORD=REPLACE_PASSWORD

# JWT
SECRET_KEY=REPLACE_ME_WITH_SECURE_RANDOM_STRING

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=REPLACE_PASSWORD
RABBITMQ_QUEUE=ml_tasks

# Telegram Bot
TELEGRAM_BOT_TOKEN=REPLACE_ME
```

### 3. Сборка и запуск

```bash
# Собрать фронтенд
cd frontend
npm install
npm run build
cd ..

# Запустить все сервисы
docker-compose up -d --build
```

### 4. Доступ к приложению

- **Веб-интерфейс**: http://localhost
- **API документация**: http://localhost/docs
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)

## Разработка

### Backend

```bash
cd app
pip install -r requirements.txt
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend будет доступен на http://localhost:3000

## Структура проекта

```
.
├── app/                    # FastAPI backend
│   ├── src/
│   │   ├── main.py        # Главный файл приложения
│   │   ├── routers/       # API роутеры
│   │   ├── services/     # Бизнес-логика
│   │   └── schemas/       # Pydantic схемы
│   └── Dockerfile
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/    # React компоненты
│   │   ├── pages/         # Страницы
│   │   ├── services/     # API клиенты
│   │   └── contexts/      # React контексты
│   └── Dockerfile
├── nginx/                 # Nginx конфигурация
├── storage/               # Модели БД и репозитории
├── docker-compose.yml     # Docker Compose конфигурация
└── README.md
```

## API Endpoints

### Авторизация
- `POST /auth/register` - Регистрация
- `POST /auth/login` - Вход
- `GET /auth/me` - Текущий пользователь

### Биллинг
- `GET /balance` - Баланс
- `POST /balance/deposit` - Пополнение
- `GET /transactions` - История транзакций

### Веб-интерфейс
- `GET /api/web/dashboard` - Данные дашборда
- `GET /api/web/history?page=1&limit=20` - История с пагинацией
- `POST /api/web/upload` - Загрузка CSV файла

### WebSocket
- `WS /api/ws/predictions/{task_id}?token=...` - Отслеживание задачи

## Формат CSV файла

CSV файл для загрузки должен содержать следующие колонки:

```csv
total_debt,penalty_amount,days_overdue,payments_ratio,is_physical_person
10000.50,500.25,30,0.75,true
20000.00,1000.00,60,0.50,false
```

- `total_debt` - общая задолженность (float, > 0)
- `penalty_amount` - сумма пеней (float, >= 0)
- `days_overdue` - дни просрочки (int, >= 0)
- `payments_ratio` - коэффициент платежей (float, 0-1)
- `is_physical_person` - физическое лицо (true/false)

## Мониторинг

### Логи

```bash
# Логи всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f app
docker-compose logs -f frontend
docker-compose logs -f web-proxy
```

### Проверка здоровья

```bash
# API health check
curl http://localhost/health

# Проверка БД
docker-compose exec database psql -U postgres -d ml_court -c "SELECT COUNT(*) FROM users;"
```

## Остановка

```bash
# Остановить все сервисы
docker-compose down

# Остановить и удалить volumes
docker-compose down -v
```

## Troubleshooting

### Проблемы с подключением к БД

Проверьте, что PostgreSQL запущен:
```bash
docker-compose ps database
```

### Проблемы с RabbitMQ

Проверьте логи:
```bash
docker-compose logs rabbitmq
```

### Проблемы с фронтендом

Убедитесь, что фронтенд собран:
```bash
cd frontend
npm run build
```

### Проблемы с CORS

В режиме разработки CORS настроен на разрешение всех источников. В продакшене измените настройки в `app/src/main.py`.

