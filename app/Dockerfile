FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Копируем ВЕСЬ проект в контейнер
COPY . .

# как у тебя было (если было другое — верни свою команду)
CMD ["python", "-m", "app.main"]