# Инструкция по настройке GitHub remote и push

## ✅ Текущий статус

Коммит успешно создан! Теперь нужно:
1. Проверить, что в `app/.env.example` нет реального токена
2. Создать репозиторий на GitHub
3. Настроить remote
4. Запушить код

## 🔍 Шаг 1: Проверка app/.env.example

**ВАЖНО:** Перед пушем проверьте, что в `app/.env.example` нет реального токена!

```powershell
# Проверьте содержимое файла
Get-Content "app\.env.example"

# Если видите реальный токен (7919252620:AAH...), замените его на REPLACE_ME
# Затем сделайте новый коммит:
git add app/.env.example
git commit -m "Fix: Remove real token from app/.env.example"
```

## 📦 Шаг 2: Создание репозитория на GitHub

1. Перейдите на https://github.com
2. Нажмите кнопку **"+"** в правом верхнем углу → **"New repository"**
3. Заполните форму:
   - **Repository name:** `ml-court-order-assistant` (или другое имя)
   - **Description:** `ML-сервис для определения пригодности дел для судебного приказа`
   - **Visibility:** Public или Private (на ваше усмотрение)
   - **НЕ** ставьте галочки на:
     - ❌ Add a README file (у вас уже есть)
     - ❌ Add .gitignore (у вас уже есть)
     - ❌ Choose a license (опционально)
4. Нажмите **"Create repository"**

## 🔗 Шаг 3: Настройка remote

После создания репозитория GitHub покажет инструкции. Выполните:

```powershell
# Замените YOUR_USERNAME на ваш реальный GitHub username
# Например, если ваш username "john-doe", команда будет:
git remote add origin https://github.com/john-doe/ml-court-order-assistant.git

# Проверьте, что remote добавлен
git remote -v
```

## 🚀 Шаг 4: Переименование ветки и push

```powershell
# Переименуйте ветку master в main (если нужно)
git branch -M main

# Запушьте код
git push -u origin main
```

Если GitHub требует аутентификацию:
- Используйте **Personal Access Token** вместо пароля
- Или настройте SSH ключи

## 🔒 Финальная проверка безопасности

После пуша проверьте на GitHub:

1. Перейдите в ваш репозиторий
2. Убедитесь, что:
   - ✅ Файл `.env` отсутствует
   - ✅ Файл `testbot.py` отсутствует
   - ✅ В `app/.env.example` нет реальных токенов (только `REPLACE_ME`)
   - ✅ В коде нет захардкоженных паролей

3. Включите Secret Scanning:
   - Settings → Security → Secret scanning
   - Включите "Secret scanning alerts"

## ⚠️ Если случайно закоммитили секреты

Если вы обнаружили, что в коммите есть реальные секреты:

```powershell
# 1. Удалите секреты из файла
# 2. Сделайте новый коммит с исправлением
git add .
git commit -m "Fix: Remove secrets"

# 3. Если уже запушили - нужно переписать историю (ОСТОРОЖНО!)
git push --force
```

**Внимание:** `git push --force` перезаписывает историю на GitHub. Используйте только если уверены!

## 📝 Пример полной последовательности команд

```powershell
# 1. Проверка app/.env.example
Get-Content "app\.env.example"

# 2. Если нужно исправить - отредактируйте файл, затем:
git add app/.env.example
git commit -m "Fix: Remove real token from app/.env.example"

# 3. Настройка remote (замените YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/ml-court-order-assistant.git

# 4. Переименование ветки
git branch -M main

# 5. Push
git push -u origin main
```

## ✅ Готово!

После успешного пуша ваш код будет на GitHub, и вы сможете:
- Поделиться репозиторием
- Настроить CI/CD
- Пригласить соавторов
- Отслеживать изменения

