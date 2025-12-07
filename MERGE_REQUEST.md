# Merge Request: ДЗ №5 - Интеграция ML сервиса через RabbitMQ

## Описание

Реализовано взаимодействие системы с ML сервисом посредством передачи сообщений через RabbitMQ в соответствии с требованиями ДЗ №5.

## Выполненные требования

✅ **Взаимодействие системы с ML сервисом посредством передачи сообщений**
- Реализован Publisher (`app/src/rabbitmq_client.py`) для отправки задач в очередь
- Реализован Consumer (`app/src/ml_worker.py`) для обработки задач из очереди

✅ **Развернуто несколько воркеров**
- 3 ML воркера запущены в Docker контейнерах: `ml-worker-1`, `ml-worker-2`, `ml-worker-3`
- Конфигурация в `docker-compose.yml`

✅ **Воркеры подключены к RabbitMQ**
- Все воркеры подключаются к очереди `ml_tasks`
- Автоматическое переподключение при ошибках

✅ **RabbitMQ настроен в режиме один издатель - несколько слушателей**
- Publisher: FastAPI (`/predict`) и Telegram Bot
- Consumers: 3 воркера слушают одну очередь `ml_tasks`
- Используется `basic_qos(prefetch_count=1)` для равномерного распределения

✅ **Воркеры получают задачу, валидируют данные, выполняют предикт, записывают результат**
- Получение задачи из очереди (callback функция)
- Валидация данных (`validate_input_data`)
- Выполнение предикта (`calculate_prediction`)
- Запись результата в БД (обновление `MLTaskDB` и создание `PredictionDB`)

## Изменения в коде

### Новые файлы:
- `app/src/rabbitmq_client.py` - Publisher для RabbitMQ
- `app/src/ml_worker.py` - ML воркер для обработки задач
- `DZ5_REPORT.md` - отчет по выполнению ДЗ
- `TEST_DZ5.md` - инструкция по тестированию

### Измененные файлы:
- `docker-compose.yml` - добавлены 3 ML воркера и Telegram бот
- `app/Dockerfile` - обновлен для поддержки воркеров
- `app/requirements.txt` - добавлен `pika` для RabbitMQ, обновлен `bcrypt`
- `app/src/routers/predict.py` - интеграция с RabbitMQ
- `app/src/telegram_bot.py` - интеграция с RabbitMQ
- `storage/repository.py` - исправлена обработка паролей (bcrypt)

## Архитектура

```
Client (REST API / Telegram Bot)
    ↓
FastAPI / Telegram Bot (Publisher)
    ↓
RabbitMQ Queue: ml_tasks
    ↓
┌──────────┬──────────┬──────────┐
│ Worker-1 │ Worker-2 │ Worker-3 │ (Consumers)
└────┬─────┴────┬─────┴────┬─────┘
     └──────────┼──────────┘
                ↓
         PostgreSQL Database
```

## Тестирование

### REST API:
1. Регистрация: `POST /auth/register`
2. Авторизация: `POST /auth/login`
3. Пополнение баланса: `POST /balance/deposit`
4. Отправка задачи: `POST /predict` (задача отправляется в RabbitMQ)
5. Проверка статуса: `GET /task/{task_id}` (повторять пока статус не станет `completed`)

### Telegram Bot:
1. Открыть бота `@AI_Court_Order_Bot`
2. Зарегистрироваться через "📝 Регистрация"
3. Пополнить баланс через "➕ Пополнить"
4. Создать предсказание через "🔮 Предсказание"
5. Задача обработается воркером через RabbitMQ

### Проверка RabbitMQ:
- UI: http://localhost:15672 (guest/guest)
- Очередь: `ml_tasks`
- Consumer connections: 3

## Запуск системы

```bash
docker-compose up -d
```

Сервисы:
- `app` - FastAPI приложение
- `telegram-bot` - Telegram бот
- `ml-worker-1`, `ml-worker-2`, `ml-worker-3` - ML воркеры
- `rabbitmq` - RabbitMQ сервер
- `database` - PostgreSQL
- `web-proxy` - Nginx

## Документация

- `DZ5_REPORT.md` - полный отчет по выполнению ДЗ
- `TEST_DZ5.md` - инструкция по тестированию
- `README.md` - общая документация проекта

## Чеклист

- [x] Взаимодействие через RabbitMQ реализовано
- [x] 3 воркера развернуты и работают
- [x] Воркеры подключены к RabbitMQ
- [x] Режим один издатель - несколько слушателей настроен
- [x] Валидация данных реализована
- [x] Выполнение предикта реализовано
- [x] Запись результата в БД реализована
- [x] Протестировано через REST API
- [x] Протестировано через Telegram Bot

## Ссылка на репозиторий

https://github.com/Evgeniy156/ml-court-order-assistant-0-

## Ветка

`dz5-rabbitmq-integration`

