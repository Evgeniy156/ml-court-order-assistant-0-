FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY src/ ./src/

# Копируем storage (должен быть в контексте билда)
COPY storage/ ./storage/

# Порт приложения
EXPOSE 8000

# Запуск FastAPI
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
