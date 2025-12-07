# Pull Request готов к созданию

## ✅ Все готово

- ✅ Код закоммичен и отправлен в репозиторий
- ✅ Ветка: `dz5-rabbitmq-integration`
- ✅ Описание PR подготовлено в `MERGE_REQUEST.md`

## 🔐 Авторизация в GitHub CLI

Для автоматического создания PR выполните:

```powershell
gh auth login
```

Следуйте инструкциям:
1. Выберите `GitHub.com`
2. Выберите способ авторизации (браузер или токен)
3. Подтвердите авторизацию

## 🚀 Создание Pull Request

После авторизации выполните:

```powershell
gh pr create --base main --head dz5-rabbitmq-integration --title "ДЗ №5: Интеграция ML сервиса через RabbitMQ" --body-file MERGE_REQUEST.md
```

Или создайте PR вручную через веб-интерфейс:

1. Откройте: https://github.com/Evgeniy156/ml-court-order-assistant-0-
2. Нажмите "Pull requests" → "New pull request"
3. Выберите base: `main`, compare: `dz5-rabbitmq-integration`
4. Скопируйте описание из `MERGE_REQUEST.md`
5. Создайте PR

## 📝 Описание для PR

Содержимое файла `MERGE_REQUEST.md` готово для копирования в описание Pull Request.

