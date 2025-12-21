# Проверка системы распознавания СНИЛС

## ✅ Выполненные проверки кода

### 1. Requirements.txt
- ✓ `opencv-python` присутствует
- ✓ `numpy` присутствует  
- ✓ `torch==2.1.0` присутствует
- ✓ `torchvision==0.16.0` добавлен
- ✓ `scikit-learn==1.3.2` присутствует

### 2. Обработка отсутствия модели
- ✓ HTTP 503 возвращается при отсутствии `weights/snils_digits.pt`
- ✓ Сообщение ошибки: `"weights not found"`
- ✓ Код в `app/src/services/snils/pipeline.py` строки 84-90

### 3. Импорты и структура
- ✓ Все модули в `app/src/services/snils/` корректны
- ✓ Роутер `app/src/routers/snils.py` использует новый pipeline
- ✓ Telegram бот обновлен для вывода копируемых строк
- ✓ Health endpoint: `/health` возвращает `{"status": "healthy"}`

### 4. Линтер
- ✓ Нет ошибок линтера в модулях SNILS

## 📋 Инструкции для ручной проверки

### Шаг 1: Установка зависимостей

```powershell
cd app
pip install -r requirements.txt
```

### Шаг 2: Проверка модели

Модель должна находиться в `weights/snils_digits.pt`.

**Если модели нет:**
- При запросе к `/snils/recognize` должен возвращаться HTTP 503
- Сообщение: `"weights not found"`

**Если модель есть:**
- Модель загружается один раз (singleton)
- Распознавание работает

### Шаг 3: Запуск тестов

```powershell
# Из корня проекта
pytest tests/test_snils_api.py -v
```

**Ожидаемое поведение:**
- `test_snils_recognize_snils2`: HTTP 200, count >= 1 (если модель есть) или 503 (если модели нет)
- `test_snils_recognize_snils1`: HTTP 200, warnings не пустые (если count=0)
- `test_snils_recognize_schema`: Проверка структуры ответа

### Шаг 4: Запуск API

```powershell
# Из корня проекта
uvicorn app.src.main:app --host 0.0.0.0 --port 8000
```

**Проверка health:**
```powershell
curl http://localhost:8000/health
# Ожидается: {"status":"healthy"}
```

**Проверка распознавания (без модели):**
```powershell
curl -X POST http://localhost:8000/snils/recognize -F "file=@tests/assets_local/snils2.jpg"
# Ожидается: HTTP 503, {"detail":"weights not found"}
```

**Проверка распознавания (с моделью):**
```powershell
curl -X POST http://localhost:8000/snils/recognize -F "file=@tests/assets_local/snils2.jpg"
# Ожидается: HTTP 200, {"count": N, "results": [...], "warnings": [...]}
```

### Шаг 5: Проверка Telegram-бота

**В первом терминале (API):**
```powershell
uvicorn app.src.main:app --host 0.0.0.0 --port 8000
```

**Во втором терминале (бот):**
```powershell
$env:TELEGRAM_BOT_TOKEN="your-token"
$env:DATABASE_URL="sqlite:///./dev.db"
python -m app.src.telegram_bot
```

**Проверка:**
1. Откройте бота в Telegram
2. Нажмите "🧾 СНИЛС OCR"
3. Отправьте изображение как **Документ** (без сжатия)

**Ожидаемое поведение:**
- Если `count == 0`: "Не нашёл строки СНИЛС. Совет: отправьте как Документ (без сжатия) или сделайте фото ближе и резче."
- Если `count > 0`: Копируемый список СНИЛС, одна строка = один СНИЛС, формат: `000-***-*** 00 ✅ 87%`

### Шаг 6: Debug endpoint (опционально)

```powershell
$env:ENABLE_DEBUG_ENDPOINTS="true"
# Перезапустить API
```

```powershell
curl -X POST http://localhost:8000/snils/recognize/debug -F "file=@tests/assets_local/snils2.jpg"
```

**Проверка:**
- Ответ НЕ содержит цифры
- Ответ НЕ содержит исходное изображение
- Ответ содержит: `rows_count`, `rows_boxes`, `warnings`

## 🔧 Известные проблемы

1. **Модель отсутствует**: Система корректно возвращает HTTP 503
2. **Тесты требуют модель**: Для полного прохождения тестов нужна обученная модель

## 📝 Следующие шаги

1. **Обучить модель** (если нужно):
   ```powershell
   python training/train_digits.py training/data/raw weights/snils_digits.pt
   ```

2. **Проверить работу end-to-end**:
   - Запустить API
   - Запустить бота
   - Отправить тестовое изображение
   - Проверить результат

## ✅ Критерии готовности

Система считается готовой, если:
- ✓ pytest проходит (или возвращает ожидаемые ошибки при отсутствии модели)
- ✓ `/snils/recognize` на snils2.jpg → HTTP 200 с count >= 1 (если модель есть) или 503 (если модели нет)
- ✓ Бот возвращает копируемые строки
- ✓ Сервис стабильно перезапускается
- ✓ Ошибки подключения и форматирования устранены

