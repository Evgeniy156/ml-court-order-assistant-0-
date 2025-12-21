# ml-court-order-assistant-0-
Система «ИИ-помощник по судебному приказу» автоматизирует полный цикл работы по взысканию бесспорной задолженности за ЖКУ от момента получения данных из бухгалтерии до передачи исполнительного документа в ФССП.

## 🚀 Быстрый старт

### Настройка переменных окружения

Проект использует переменные окружения для конфигурации. Создайте файл `.env` на основе примера:

**Windows PowerShell:**
```powershell
# Скопируйте пример файла
Copy-Item .env.example .env

# Отредактируйте .env и заполните значения
notepad .env
```

**Linux/Mac (Bash):**
```bash
# Скопируйте пример файла
cp .env.example .env

# Отредактируйте .env и заполните значения
nano .env
```

**Основные переменные:**
- `TELEGRAM_BOT_TOKEN` - токен Telegram бота (получите у @BotFather)
- `DATABASE_URL` - URL подключения к базе данных
- `SECRET_KEY` - секретный ключ для JWT токенов
- `RABBITMQ_*` - настройки RabbitMQ (для Docker)

**Примечание:** Для быстрого старта можно установить переменные окружения напрямую в терминале (см. разделы ниже).

### Установка зависимостей
```bash
cd app
pip install -r requirements.txt
```

### Запуск REST API

**Windows PowerShell:**

**Вариант 1: Запуск из корневой директории проекта (рекомендуется)**
```powershell
# Убедитесь, что вы в корневой директории проекта
# Установить переменные окружения
$env:DATABASE_URL="sqlite:///./dev.db"
$env:SECRET_KEY="your-secret-key"

# Запустить сервер
uvicorn app.src.main:app --host 0.0.0.0 --port 8000

# API документация доступна по адресу: http://localhost:8000/docs
```

**Вариант 2: Запуск из директории app**
```powershell
# Перейти в директорию app
cd app

# Установить переменные окружения
$env:DATABASE_URL="sqlite:///./dev.db"
$env:SECRET_KEY="your-secret-key"

# Запустить сервер (обратите внимание на другой путь)
uvicorn src.main:app --host 0.0.0.0 --port 8000

# API документация доступна по адресу: http://localhost:8000/docs
```

**Linux/Mac (Bash):**

**Вариант 1: Запуск из корневой директории проекта (рекомендуется)**
```bash
# Убедитесь, что вы в корневой директории проекта
# Установить переменные окружения
export DATABASE_URL="sqlite:///./dev.db"
export SECRET_KEY="your-secret-key"

# Запустить сервер
uvicorn app.src.main:app --host 0.0.0.0 --port 8000

# API документация доступна по адресу: http://localhost:8000/docs
```

**Вариант 2: Запуск из директории app**
```bash
# Перейти в директорию app
cd app

# Установить переменные окружения
export DATABASE_URL="sqlite:///./dev.db"
export SECRET_KEY="your-secret-key"

# Запустить сервер (обратите внимание на другой путь)
uvicorn src.main:app --host 0.0.0.0 --port 8000

# API документация доступна по адресу: http://localhost:8000/docs
```

### Запуск Telegram бота

**Windows PowerShell:**
```powershell
# Вариант 1: Использовать скрипт (рекомендуется)
.\scripts\run_telegram_bot.ps1

# Вариант 2: Использовать .env файл (если используете python-dotenv)
# Создайте .env файл на основе .env.example и заполните TELEGRAM_BOT_TOKEN

# Вариант 3: Вручную установить переменные
# Получите токен у @BotFather в Telegram
$env:TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
$env:DATABASE_URL="sqlite:///./dev.db"

python -m app.src.telegram_bot
```

**Linux/Mac (Bash):**
```bash
# Вариант 1: Использовать .env файл (если используете python-dotenv)
# Создайте .env файл на основе .env.example и заполните TELEGRAM_BOT_TOKEN

# Вариант 2: Вручную установить переменные
# Получите токен у @BotFather в Telegram
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
export DATABASE_URL="sqlite:///./dev.db"

python -m app.src.telegram_bot
```

**Примечание:** Для работы бота требуется:
- Токен от @BotFather в Telegram
- Доступ к базе данных (PostgreSQL или SQLite)
- Установленные зависимости из `app/requirements.txt`

## 📋 REST API Эндпоинты

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/` | GET | Редирект на `/docs` (Swagger UI документация) |
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

## 🧾 Распознавание СНИЛС

Система поддерживает распознавание рукописных СНИЛС из фиксированного трафарета (11 клеток) на сканах/фото страниц.

### Обучение модели распознавания цифр

1. **Подготовка данных:**
   ```bash
   # Нарежьте клетки из изображений
   python training/dataset_build.py <image_path> training/data/raw
   
   # Вручную отсортируйте клетки по папкам 0-9 в training/data/raw/
   ```

2. **Обучение модели:**
   ```bash
   python training/train_digits.py training/data/raw weights/snils_digits.pt 50 32
   ```
   
   Параметры:
   - `training/data/raw` - директория с отсортированными клетками (подпапки 0-9)
   - `weights/snils_digits.pt` - путь для сохранения весов
   - `50` - количество эпох (опционально)
   - `32` - размер батча (опционально)

3. **Проверка модели:**
   Модель будет сохранена в `weights/snils_digits.pt`. При запуске API модель загружается автоматически.

### Использование API

**REST API:**
```bash
# Распознавание СНИЛС
curl -X POST "http://localhost:8000/snils/recognize" \
  -F "file=@path/to/image.jpg"

# Debug эндпоинт (требует ENABLE_DEBUG_ENDPOINTS=true)
curl -X POST "http://localhost:8000/snils/recognize/debug" \
  -F "file=@path/to/image.jpg"
```

**Telegram бот:**
1. Откройте бота в Telegram
2. Нажмите "🧾 СНИЛС OCR"
3. Отправьте фото или документ (рекомендуется отправлять как **Документ** без сжатия)
4. Получите список распознанных СНИЛС (каждая строка - один СНИЛС для копирования)

**Рекомендации:**
- Отправляйте изображения как **Документ** (не фото) для лучшего качества
- Убедитесь, что поле СНИЛС четко видно и не перекрыто
- Изображение должно содержать строки из 11 квадратных клеток
- QR-коды не обязательны, но могут помочь в детекции

### Архитектура

Модульная структура в `app/src/services/snils/`:
- `preprocess.py` - multi-pass preprocessing
- `grid_detect.py` - поиск строк из 11 клеток
- `cut_cells.py` - нарезка и нормализация клеток
- `digit_model.py` - Torch CNN для распознавания цифр
- `decode.py` - beam-search декодирование с checksum
- `pipeline.py` - основной pipeline
- `legacy/` - старый код (сохранен для совместимости)

## 🐳 Docker

```bash
docker-compose up -d
```

Сервисы:
- `app` - FastAPI приложение (порт 8000)
- `web-proxy` - Nginx reverse proxy (порт 80)
- `database` - PostgreSQL (порт 5432)
- `rabbitmq` - RabbitMQ (порт 5672, UI: 15672)

## 🧪 Smoke Test

Smoke-тесты для проверки работоспособности API. Выполняют полный сценарий:
1. Проверка health endpoint
2. Регистрация нового пользователя (уникальный email)
3. Логин и получение JWT токена
4. Проверка auth/me endpoint
5. Пополнение баланса на 100 кредитов
6. Получение баланса (до predict)
7. Получение количества транзакций (до predict)
8. Создание ML предсказания
9. Проверка баланса (после predict - должен уменьшиться)
10. Проверка транзакций (после predict - должно увеличиться)

### Запуск smoke-тестов

**Windows PowerShell:**
```powershell
# Базовый запуск (использует значения по умолчанию)
python scripts/smoke_test_api.py

# С указанием BASE_URL через переменную окружения
$env:BASE_URL="http://localhost:80"; python scripts/smoke_test_api.py

# С указанием всех параметров через CLI
python scripts/smoke_test_api.py --base-url http://localhost:80 --password testpass123 --timeout 15

# Через переменные окружения (PowerShell)
$env:BASE_URL="http://localhost:80"; $env:PASSWORD="testpass123"; $env:TIMEOUT="15"; python scripts/smoke_test_api.py
```

**Linux/Mac (Bash):**
```bash
# Базовый запуск (использует значения по умолчанию)
python scripts/smoke_test_api.py

# С указанием BASE_URL через переменную окружения
BASE_URL=http://localhost:80 python scripts/smoke_test_api.py

# С указанием всех параметров через CLI
python scripts/smoke_test_api.py --base-url http://localhost:80 --password testpass123 --timeout 15

# Через переменные окружения
BASE_URL=http://localhost:80 PASSWORD=testpass123 TIMEOUT=15 python scripts/smoke_test_api.py
```

### Параметры конфигурации

- `BASE_URL` - базовый URL API (по умолчанию: `http://localhost:80`)
- `PASSWORD` - пароль для тестового пользователя (по умолчанию: `testpass123`)
- `TIMEOUT` - timeout для HTTP запросов в секундах (по умолчанию: `10`)

### Exit codes

- `0` - все тесты пройдены успешно
- `2` - ошибка health check
- `3` - ошибка регистрации
- `4` - ошибка логина
- `5` - другие ошибки

---

## 🔒 Безопасность

### Защита секретов

**ВАЖНО:** Проект не содержит реальных секретов в коде. Все секреты должны храниться в переменных окружения или файле `.env`.

#### Что НЕ должно попадать в Git:

- ✅ Файл `.env` (уже в `.gitignore`)
- ✅ Реальные токены Telegram ботов
- ✅ Пароли от баз данных
- ✅ Секретные ключи JWT
- ✅ API ключи
- ✅ Сертификаты и приватные ключи

#### Проверка перед коммитом:

```powershell
# Проверить, что .env не отслеживается
git ls-files | Select-String ".env"

# Проверить, что нет захардкоженных секретов
git grep -n "TELEGRAM_BOT_TOKEN\|API_KEY\|SECRET\|PASSWORD" | Select-String -NotMatch "REPLACE_ME\|your-telegram-bot-token\|your-secret-key"
```

#### Настройка переменных окружения:

1. Скопируйте `.env.example` в `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```

2. Заполните реальные значения в `.env`:
   - `TELEGRAM_BOT_TOKEN` - получите у @BotFather
   - `POSTGRES_PASSWORD` - придумайте надежный пароль
   - `SECRET_KEY` - сгенерируйте случайную строку (минимум 32 символа)
   - `RABBITMQ_PASSWORD` - придумайте надежный пароль

3. **Никогда не коммитьте `.env` файл!**

#### Генерация SECRET_KEY:

```powershell
# PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

```bash
# Bash
openssl rand -hex 32
```

#### Docker Compose и секреты:

Все пароли в `docker-compose.yml` используют переменные окружения с значениями по умолчанию для разработки. В продакшене обязательно установите переменные окружения:

```powershell
$env:POSTGRES_PASSWORD="secure_password_here"
$env:SECRET_KEY="secure_random_string_here"
$env:RABBITMQ_PASSWORD="secure_password_here"
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
