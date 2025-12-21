FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY app/src/ ./src/

# Копируем storage из корня проекта
COPY storage/ ./storage/

# Добавляем /app в PYTHONPATH для импорта storage
ENV PYTHONPATH=/app

# Порт приложения
EXPOSE 8000

# Запуск FastAPI
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
