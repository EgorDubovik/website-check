# Используем легкий образ Python
FROM python:3.10-alpine

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем основной скрипт
COPY monitor.py .

# Бот токен
ENV BOT_TOKEN="8444195814:AAEB5WrubcIlPYJUmREp414Gaa6N44BmntY"

# Запускаем скрипт при старте контейнера
CMD ["python", "monitor.py"]