# Инструкция по созданию Merge Request для ДЗ №7

## Шаги для создания MR:

### 1. Проверьте, что вы находитесь в правильной директории проекта

### 2. Создайте/переключитесь на ветку `6-web-interface`:
```bash
git checkout -b 6-web-interface
# или если ветка уже существует:
git checkout 6-web-interface
```

### 3. Добавьте изменения:
```bash
git add tests/conftest.py
git add tests/test_api.py
git add .github/workflows/tests.yml
```

### 4. Создайте коммит:
```bash
git commit -m "ДЗ №7: Добавлены автоматические тесты (pytest) для ключевых сценариев

- Добавлен conftest.py с фикстурами для чистой БД, client, helpers
- Реализованы тесты для аутентификации (register, login, JWT)
- Реализованы тесты для баланса (deposit, validation)
- Реализованы тесты для предсказаний (списание кредитов, недостаточно средств)
- Реализованы тесты для транзакций (история, сортировка)
- Реализованы тесты для админ-функций (список пользователей, пополнение баланса)
- Добавлен мок для RabbitMQ
- Добавлена CI конфигурация для GitHub Actions
- Все 20 тестов проходят успешно"
```

### 5. Если у вас есть remote репозиторий, настройте его:
```bash
# Для GitLab:
git remote add origin <URL_вашего_репозитория>

# Для GitHub:
git remote add origin <URL_вашего_репозитория>
```

### 6. Запушьте ветку:
```bash
git push -u origin 6-web-interface
```

### 7. Создайте Merge Request:

**Для GitLab:**
1. Перейдите на страницу проекта в GitLab
2. Нажмите "Merge Requests" → "New merge request"
3. Выберите source branch: `6-web-interface`
4. Выберите target branch: `main` (или `master`)
5. Заполните описание (см. шаблон ниже)
6. Нажмите "Create merge request"

**Для GitHub:**
1. Перейдите на страницу проекта в GitHub
2. Нажмите "Pull requests" → "New pull request"
3. Выберите base: `main` (или `master`)
4. Выберите compare: `6-web-interface`
5. Заполните описание (см. шаблон ниже)
6. Нажмите "Create pull request"

## Шаблон описания Merge Request:

```markdown
## ДЗ №7: Тестирование работоспособности системы

### Что сделано:

✅ Добавлены автоматические тесты (pytest) для ключевых сценариев:
- **Аутентификация**: регистрация, логин, JWT валидация, защита эндпоинтов
- **Баланс**: начальное значение, пополнение, валидация сумм
- **Предсказания**: списание кредитов, создание транзакций, недостаток средств
- **Транзакции**: история, типы (deposit/withdraw), сортировка по дате
- **Админ-функции**: проверка прав, пополнение баланса пользователям

### Технические детали:

- **Фикстуры**: `conftest.py` с изоляцией БД для каждого теста (SQLite)
- **Моки**: RabbitMQ замокан на уровне `get_rabbitmq_publisher()`
- **CI**: Добавлена конфигурация GitHub Actions для автоматического запуска тестов
- **Воспроизводимость**: Каждый тест работает на чистой базе данных

### Результаты тестирования:

```
20 passed, 11 warnings in 8.48s
```

### Покрытые HTTP статусы:

- ✅ 200 (OK)
- ✅ 400 (Bad Request) - дублирующийся email
- ✅ 401 (Unauthorized) - отсутствие токена, неверный пароль
- ✅ 403 (Forbidden) - отсутствие админ-прав
- ✅ 404 (Not Found) - пользователь не найден
- ✅ 422 (Unprocessable Entity) - невалидные данные
- ✅ 402 (Payment Required) - недостаточно средств

### Файлы:

- `tests/conftest.py` - общие фикстуры и helpers
- `tests/test_api.py` - набор тестов (20 тестов)
- `.github/workflows/tests.yml` - CI конфигурация

### Команды запуска:

```bash
# Все тесты
python -m pytest tests/test_api.py -v

# С кратким выводом
python -m pytest tests/test_api.py -v --tb=short -q
```
```

## Ссылка на MR:

После создания MR, ссылка будет выглядеть примерно так:

**GitLab:**
```
https://gitlab.com/<username>/<project>/-/merge_requests/<MR_ID>
```

**GitHub:**
```
https://github.com/<username>/<project>/pull/<PR_ID>
```

