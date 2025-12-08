# ml-court-order-assistant-0-
Система «ИИ-помощник по судебному приказу» автоматизирует полный цикл работы по взысканию бесспорной задолженности за ЖКУ от момента получения данных из бухгалтерии до передачи исполнительного документа в ФССП.

## 🚀 Быстрый старт

### Установка зависимостей
```bash
cd app
pip install -r requirements.txt
```

### Запуск REST API

#### Windows (PowerShell)

**Важно:** При установке переменных окружения в PowerShell убедитесь, что используете обычные кавычки и нет невидимых символов:

```powershell
# Правильный способ установки переменных окружения
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ml_court"
$env:RABBITMQ_HOST = "localhost"
$env:RABBITMQ_PORT = "5672"
$env:SECRET_KEY = "your-secret-key"

# Запустить сервер
cd app
uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

**Если возникают ошибки с кодировкой:**
1. Убедитесь, что используете обычные двойные кавычки `"`, а не специальные символы
2. Скопируйте команду целиком, не редактируйте вручную
3. Или используйте файл `.env` (см. раздел Docker)

#### Linux/Mac

```bash
# Установить переменные окружения
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/ml_court"
export RABBITMQ_HOST="localhost"
export RABBITMQ_PORT="5672"
export SECRET_KEY="your-secret-key"

# Запустить сервер
cd app
uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

# API документация доступна по адресу: http://localhost:8001/docs

### Запуск Telegram бота
```bash
# Получите токен у @BotFather в Telegram
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
export DATABASE_URL="sqlite:///./dev.db"

python -m app.src.telegram_bot
```

## 📋 REST API Эндпоинты

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/` | GET | Главная страница с описанием сервиса |
| `/health` | GET | Проверка состояния сервиса |
| `/docs` | GET | Swagger UI документация |
| `/auth/register` | POST | Регистрация пользователя |
| `/auth/login` | POST | Авторизация (получение JWT токена) |
| `/auth/me` | GET | Информация о текущем пользователе |
| `/balance` | GET | Просмотр баланса |
| `/balance/deposit` | POST | Пополнение баланса |
| `/transactions` | GET | История транзакций |
| `/predict` | POST | ML-предсказание (списывает кредиты) |
| `/models` | GET | Список доступных ML моделей |
| `/admin/users` | GET | Список пользователей (только админ) |
| `/admin/deposit/{user_id}` | POST | Пополнение баланса пользователю (админ) |

## 🤖 Telegram Bot Команды

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/help` | Справка |
| `/register` | Регистрация |
| `/login` | Вход в аккаунт |
| `/balance` | Просмотр баланса |
| `/deposit` | Пополнение баланса |
| `/predict` | ML-предсказание |
| `/history` | История транзакций |
| `/logout` | Выход из аккаунта |

## 🐳 Docker

### Настройка окружения

1. Создайте файл `.env` в корне проекта на основе `.env.example`:

```bash
cp .env.example .env
```

2. Отредактируйте `.env` и укажите реальный токен Telegram бота:

```env
TELEGRAM_BOT_TOKEN=your-actual-bot-token-from-botfather
```

3. Для Docker-окружения убедитесь, что используются правильные хосты:
   - `DATABASE_URL=postgresql://postgres:postgres@database:5432/ml_court` (имя сервиса `database`)
   - `RABBITMQ_HOST=rabbitmq` (имя сервиса `rabbitmq`)

### Запуск всех сервисов

```bash
# Из корня проекта
docker-compose up --build -d
```

### Сервисы

- `app` - FastAPI приложение (порт 8000)
- `web-proxy` - Nginx reverse proxy (порт 80)
- `database` - PostgreSQL (порт 5432)
- `rabbitmq` - RabbitMQ (порт 5672, UI: 15672)
- `telegram-bot` - Telegram бот

### Проверка работы

```bash
# Проверить статус всех сервисов
docker-compose ps

# Просмотр логов бота
docker-compose logs -f telegram-bot

# Просмотр логов API
docker-compose logs -f app
```

---

📌 Описание проекта

Этот репозиторий представляет объектную модель, разработанную для задания №1 курса
«Практическая ML-инженерия: MLOps и разработка проектов. 3 поток».

Модель отражает архитектуру реального ML-сервиса, где:

пользователи — только профили,

деньги и транзакции — в биллинг-подсистеме,

ML-задачи — отдельный вычислительный слой,

юридические процессы — самостоятельный домен.

Проект готовится как основа для следующих этапов: ORM, REST API, Telegram-бот, RabbitMQ, Docker.

🏛️ Архитектура проекта

Основные подсистемы:

👤 Пользователи и роли

Роли вынесены в отдельную иерархию:

User
 ├── Manager
 └── Admin


Каждая роль переопределяет доступ через полиморфные методы:

can_view_all_cases()

can_approve_topups()

Это позволяет строить гибкую RBAC-модель.

Пользователь не содержит баланс, только ссылки:

billing_account

transaction_history

prediction_history

💰 Билинг: баланс и транзакции

В новой архитектуре баланс — зона ответственности отдельной подсистемы.

🔸 BillingAccount

принимает операции deposit() и withdraw()

хранит фактический баланс

привязан к user_id

🔸 BillingService

Содержит бизнес-логику денег:

списание средств с записью транзакции

пополнение баланса

генерация Transaction-объектов

🔸 UserTransactionHistory

Контейнер всех финансовых операций пользователя.

Структура:

UserTransactionHistory
 └── List[Transaction]

🤖 ML-подсистема

Представлена двумя блоками:

🔹 MLModel (абстракция)

Определяет интерфейс:

predict(payload)

🔹 CourtOrderSuitabilityModel

Модель, анализирующая пригодность дела к судебному приказу.

🔹 MLTask

Хранит:

входные данные,

статус (PENDING, RUNNING, FAILED, DONE),

результат,

списанные кредиты,

ссылку на модель,

user_id.

🔹 UserPredictionHistory

Контейнер всех ML-предсказаний пользователя:

UserPredictionHistory
 └── List[MLTask]


Позволяет вести историю обращений к ML.

⚖️ Юридический домен «Судебный приказ»

Модель охватывает полный жизненный цикл:

долг → расчёт → претензия → суд → исполнительное производство

Основные сущности:

🔸 DebtCase

основная юридическая карточка

содержит данные должника, суммы, период

имеет метод:

is_eligible_for_court_order()

🔸 Calculation / CalculationItem

Расчёт задолженности и пеней по месяцам.

🔸 PretrialNotice

Досудебное уведомление (дата отправки, трек-номер, шаблон).

🔸 CourtOrder

Судебный приказ: подача, номер, выдача, отмена.

🔸 Enforcement

Исполнительное производство (этап ФССП).

🧩 Принципы ООП
🔒 Инкапсуляция

Баланс скрыт внутри BillingAccount,
а пользователь не имеет прямого доступа к деньгам.

Контролируемые методы:

deposit()

withdraw()

вызов транзакций только через BillingService

Поля _password_hash также скрыты.

🧬 Наследование

Ролевая модель реализована через наследование:

Admin → расширяет User дополнительными правами

Manager → расширяет User доступом к чужим делам

ML-модель наследует поведение от MLModel (Protocol).

🌀 Полиморфизм

Методы доступа:

can_view_all_cases()

can_approve_topups()

определяются в зависимости от роли:

Роль	Просмотр всех дел	Модерация баланса
User	❌	❌
Manager	✔️	❌
Admin	✔️	✔️

📂 Структура репозитория
📦 ml-court-order-assistant
 ├── domain_model.py        # основная объектная модель
 ├── README.md              # документация (этот файл)

🚀 План дальнейшей разработки

Эта модель станет базой для:

ORM-схемы (SQLAlchemy / Django ORM)

REST API на FastAPI

Telegram-бота

Очередей RabbitMQ + воркеры ML

Docker-инфраструктуры

Метрик и мониторинга


🧱 Автор модели

Студент курса «Практическая ML-инженерия: MLOps и разработка проектов. 3 поток» Калинин Евгений Владимирович.

Проект создан в рамках ДЗ №1:
«Спроектировать объектную модель сервиса»
