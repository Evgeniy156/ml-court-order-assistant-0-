# 🚀 Быстрый старт - ML Court Order Assistant

## ✅ Текущий статус

Все сервисы запущены и работают:
- ✅ **Backend API** - http://localhost:8000
- ✅ **Веб-интерфейс** - http://localhost
- ✅ **API документация** - http://localhost/docs
- ✅ **RabbitMQ Management** - http://localhost:15672 (guest/guest)
- ✅ **PostgreSQL** - localhost:5432

## 📝 Следующие шаги

### 1. Вход в систему

В API документации (http://localhost/docs):

**POST /auth/login**
```json
{
  "username": "test@example.com",
  "password": "test1234"
}
```

Ответ:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### 2. Использование токена

1. Нажмите кнопку **"Authorize"** в правом верхнем углу
2. Введите: `Bearer <ваш_токен>`
3. Теперь все запросы будут авторизованы

### 3. Пополнение баланса

**POST /balance/deposit**
```json
{
  "amount": 100
}
```

### 4. Просмотр баланса

**GET /balance**

### 5. Загрузка CSV для ML-предсказаний

**POST /api/web/upload**

Загрузите CSV файл со следующими колонками:
- `total_debt` - общая задолженность
- `penalty_amount` - сумма пеней
- `days_overdue` - дни просрочки
- `payments_ratio` - коэффициент платежей (0-1)
- `is_physical_person` - true/false

Пример CSV:
```csv
total_debt,penalty_amount,days_overdue,payments_ratio,is_physical_person
10000.50,500.25,30,0.75,true
20000.00,1000.00,60,0.50,false
```

### 6. Просмотр истории транзакций

**GET /api/web/history?page=1&limit=20**

### 7. Дашборд

**GET /api/web/dashboard**

## 🌐 Веб-интерфейс

Откройте в браузере: **http://localhost**

### Страницы:
- `/login` - Авторизация/регистрация
- `/dashboard` - Главная страница с балансом
- `/payment` - Пополнение баланса
- `/upload` - Загрузка CSV файлов
- `/history` - История транзакций

## 🔧 Полезные команды

### Проверка статуса
```powershell
docker ps
```

### Просмотр логов
```powershell
docker logs app --tail 50
docker logs web-proxy --tail 20
```

### Перезапуск сервисов
```powershell
docker restart app
docker restart web-proxy
```

### Остановка всех сервисов
```powershell
docker stop app database rabbitmq web-proxy
```

### Запуск всех сервисов
```powershell
docker start database rabbitmq app web-proxy
```

## 🐛 Решение проблем

### Если веб-интерфейс не открывается

1. Проверьте, что nginx запущен:
   ```powershell
   docker ps | Select-String "web-proxy"
   ```

2. Проверьте логи:
   ```powershell
   docker logs web-proxy
   ```

3. Убедитесь, что фронтенд собран:
   ```powershell
   Test-Path frontend/dist/index.html
   ```

### Если API не отвечает

1. Проверьте логи приложения:
   ```powershell
   docker logs app --tail 50
   ```

2. Проверьте подключение к БД:
   ```powershell
   docker exec database psql -U postgres -d ml_court -c "SELECT COUNT(*) FROM users;"
   ```

### Если регистрация не работает

Проверьте, что все исправления применены:
```powershell
docker exec app cat /app/storage/repository.py | Select-String "bcrypt_lib"
```

## 📊 Проверка работоспособности

### Тест 1: Регистрация
```bash
curl -X POST http://localhost/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test2@example.com","password":"test1234"}'
```

### Тест 2: Вход
```bash
curl -X POST http://localhost/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test1234"
```

### Тест 3: Баланс (нужен токен)
```bash
curl -X GET http://localhost/balance \
  -H "Authorization: Bearer <ваш_токен>"
```

## 🎯 Готово к использованию!

Теперь вы можете:
1. ✅ Регистрировать пользователей
2. ✅ Входить в систему
3. ✅ Пополнять баланс
4. ✅ Загружать CSV файлы для ML-предсказаний
5. ✅ Просматривать историю транзакций
6. ✅ Использовать веб-интерфейс

**Удачи! 🚀**

