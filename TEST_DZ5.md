# Тестирование ДЗ №5

## ✅ Проверка выполнения требований

### 1. ✅ Взаимодействие системы с ML сервисом посредством передачи сообщений
- **Реализовано:** RabbitMQ используется для асинхронной обработки ML задач
- **Файлы:** `app/src/rabbitmq_client.py` (Publisher), `app/src/ml_worker.py` (Consumer)

### 2. ✅ Развернуто несколько воркеров
- **Реализовано:** 3 ML воркера запущены в Docker
- **Контейнеры:** `ml-worker-1`, `ml-worker-2`, `ml-worker-3`
- **Конфигурация:** `docker-compose.yml` (строки 59-129)

### 3. ✅ Воркеры подключены к RabbitMQ
- **Реализовано:** Все воркеры подключаются к очереди `ml_tasks`
- **Проверка:** `docker-compose logs ml-worker-1` показывает "Подключено к RabbitMQ"

### 4. ✅ RabbitMQ настроен в режиме один издатель - несколько слушателей
- **Реализовано:** 
  - Publisher: FastAPI (`app/src/routers/predict.py`) и Telegram Bot отправляют задачи
  - Consumers: 3 воркера слушают одну очередь `ml_tasks`
  - Используется `basic_qos(prefetch_count=1)` для равномерного распределения

### 5. ✅ Воркеры получают задачу, валидируют данные, выполняют предикт, записывают результат
- **Реализовано в `app/src/ml_worker.py`:**
  - Получение задачи из очереди (строки 191-211)
  - Валидация данных (функция `validate_input_data`, строки 45-85)
  - Выполнение предикта (строка 150: `calculate_prediction`)
  - Запись результата в БД (строки 153-174)

## 🧪 Тестирование системы

### Тест 1: REST API

#### Шаг 1: Регистрация пользователя
```bash
curl -X POST http://localhost/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123"}'
```

#### Шаг 2: Авторизация
```bash
curl -X POST http://localhost/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123"
```
Сохраните полученный `access_token`.

#### Шаг 3: Пополнение баланса
```bash
curl -X POST http://localhost/balance/deposit \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100}'
```

#### Шаг 4: Отправка ML-задачи в очередь
```bash
curl -X POST http://localhost/predict \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "total_debt": 75000,
    "penalty_amount": 7500,
    "days_overdue": 150,
    "payments_ratio": 0.2,
    "is_physical_person": true
  }'
```

**Ожидаемый результат:**
```json
{
  "task_id": 1,
  "status": "pending",
  "model_name": "court_order_suitability_v1",
  "credits_charged": 5,
  "message": "Задача отправлена на обработку..."
}
```

#### Шаг 5: Проверка статуса задачи
```bash
curl http://localhost/task/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Повторяйте команду пока статус не станет `completed`:**
- `pending` - задача в очереди
- `processing` - воркер обрабатывает
- `completed` - готово (есть поле `prediction`)
- `failed` - ошибка (есть поле `error_message`)

#### Шаг 6: Проверка истории предсказаний
```bash
curl http://localhost/predictions \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Тест 2: Telegram Bot

1. **Найдите бота в Telegram:** `@AI_Court_Order_Bot`
2. **Отправьте `/start`**
3. **Зарегистрируйтесь:**
   - Нажмите "📝 Регистрация"
   - Введите email: `test@example.com`
   - Введите пароль: `test123`
4. **Пополните баланс:**
   - Нажмите "➕ Пополнить"
   - Введите сумму: `100`
5. **Создайте предсказание:**
   - Нажмите "🔮 Предсказание"
   - Следуйте инструкциям бота
   - Задача отправится в RabbitMQ
   - Воркер обработает задачу

### Тест 3: Проверка RabbitMQ

1. **Откройте RabbitMQ Management UI:** http://localhost:15672
   - Логин: `guest`
   - Пароль: `guest`
2. **Проверьте очередь `ml_tasks`:**
   - Должна быть создана
   - При отправке задачи появляются сообщения
   - Сообщения обрабатываются воркерами

### Тест 4: Проверка логов воркеров

```bash
# Логи воркера 1
docker-compose logs ml-worker-1 --tail 50

# Логи воркера 2
docker-compose logs ml-worker-2 --tail 50

# Логи воркера 3
docker-compose logs ml-worker-3 --tail 50
```

**Ожидаемые логи:**
```
[worker-1] Получена задача 1 из очереди
[worker-1] Начало обработки задачи 1
[worker-1] Задача 1: выполнение предсказания...
[worker-1] Задача 1: результат предсказания = 0.7234
[worker-1] Задача 1 успешно обработана
```

## 📊 Проверка работы системы

### Команды для проверки статуса:

```bash
# Статус всех контейнеров
docker-compose ps

# Проверка RabbitMQ
curl http://localhost:15672/api/overview -u guest:guest

# Проверка очереди
curl http://localhost:15672/api/queues/%2F/ml_tasks -u guest:guest

# Логи приложения
docker-compose logs app --tail 20

# Логи всех воркеров
docker-compose logs ml-worker-1 ml-worker-2 ml-worker-3 --tail 20
```

## ✅ Итоговый чеклист ДЗ №5

- [x] Реализовано взаимодействие с ML сервисом через RabbitMQ
- [x] Развернуто несколько воркеров (3 шт)
- [x] Воркеры подключены к RabbitMQ
- [x] RabbitMQ настроен в режиме один издатель - несколько слушателей
- [x] Воркеры валидируют данные
- [x] Воркеры выполняют предикт
- [x] Воркеры записывают результат в БД
- [ ] Протестировано через REST API (нужно выполнить тесты выше)
- [ ] Протестировано через Telegram Bot (нужно выполнить тесты выше)






