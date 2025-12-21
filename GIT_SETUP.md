# Инструкция по настройке Git и публикации на GitHub

## Шаг 1: Проверка перед коммитом

Убедитесь, что вы находитесь в директории проекта:
```powershell
cd "C:\Users\III\Desktop\ИТМО\2. Практикум по разработке ML сервисов на Python\Урок 7. Тестирование ПО\ml-court-order-assistant-0--dz7-tests"
```

Проверьте, что `.env` файл не существует или не будет закоммичен:
```powershell
# Проверка наличия .env
if (Test-Path .env) { Write-Host "WARNING: .env exists!" -ForegroundColor Red } else { Write-Host "OK: .env does not exist" -ForegroundColor Green }

# Проверка, что .env не отслеживается git
git ls-files | Select-String "\.env$"
# Должно быть пусто
```

## Шаг 2: Инициализация Git (если еще не сделано)

```powershell
# Инициализация репозитория
git init

# Проверка статуса
git status
```

## Шаг 3: Добавление файлов (исключая секреты)

```powershell
# Добавить все файлы (gitignore автоматически исключит секреты)
git add .

# Проверить, что секреты не добавлены
git status --short | Select-String -Pattern "\.env$|pgdata|rabbitmq_data|__pycache__|\.pyc|dev\.db"
# Должно быть пусто или только игнорируемые файлы

# Проверить, что нет захардкоженных секретов
git diff --cached | Select-String -Pattern "TELEGRAM_BOT_TOKEN|API_KEY|SECRET|PASSWORD" | Select-String -NotMatch "REPLACE_ME|your-telegram-bot-token|your-secret-key|REPLACE_PASSWORD"
# Должно быть пусто
```

## Шаг 4: Первый коммит

```powershell
git commit -m "Initial commit: ML court order assistant (no secrets)"
```

## Шаг 5: Создание репозитория на GitHub

1. Перейдите на https://github.com
2. Нажмите "New repository"
3. Заполните:
   - Repository name: `ml-court-order-assistant`
   - Description: `ML-сервис для определения пригодности дел для судебного приказа`
   - Visibility: Public или Private (на ваше усмотрение)
4. НЕ добавляйте README, .gitignore или license (они уже есть)
5. Нажмите "Create repository"

## Шаг 6: Подключение remote и push

```powershell
# Замените YOUR_USERNAME на ваш GitHub username
git remote add origin https://github.com/YOUR_USERNAME/ml-court-order-assistant.git

# Переименовать ветку в main (если нужно)
git branch -M main

# Запушить код
git push -u origin main
```

## Шаг 7: Проверка безопасности

После пуша проверьте на GitHub:
1. Перейдите в репозиторий
2. Убедитесь, что файл `.env` отсутствует
3. Проверьте, что нет реальных токенов/паролей в коде
4. Включите "Secret scanning" в настройках репозитория (Settings → Security → Secret scanning)

## Дополнительные проверки

### Проверка секретов в коде:
```powershell
# Поиск потенциальных секретов
git grep -n "TELEGRAM_BOT_TOKEN\|API_KEY\|SECRET\|PASSWORD" | Select-String -NotMatch "REPLACE_ME|your-telegram-bot-token|your-secret-key|REPLACE_PASSWORD|os\.getenv|getenv"
```

### Проверка .gitignore:
```powershell
# Убедитесь, что .gitignore содержит нужные паттерны
Get-Content .gitignore | Select-String "\.env|pgdata|rabbitmq_data"
```

## Если что-то пошло не так

Если случайно закоммитили `.env`:
```powershell
# Удалить из индекса (но оставить локально)
git rm --cached .env

# Добавить в .gitignore (если еще нет)
echo ".env" >> .gitignore

# Закоммитить исправление
git add .gitignore
git commit -m "Remove .env from tracking"

# Принудительно обновить remote (ОСТОРОЖНО!)
git push --force
```

## Защита от утечек в будущем

1. **Pre-commit hooks** (опционально):
   ```powershell
   # Установить pre-commit
   pip install pre-commit
   
   # Создать .pre-commit-config.yaml
   # Добавить проверки на секреты
   ```

2. **GitHub Secret Scanning**: Автоматически включено для публичных репозиториев

3. **Правила для команды**:
   - Никогда не коммитить `.env`
   - Всегда использовать `.env.example` как шаблон
   - Проверять `git status` перед коммитом
   - Использовать `git diff` для проверки изменений

