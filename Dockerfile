# 1. Используем официальный Python образ
FROM python:3.11-slim

# 2. Устанавливаем рабочую директорию
WORKDIR /app

# 3. Копируем зависимости
COPY requirements.txt .

# 4. Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копируем весь проект
COPY . .

# 6. Устанавливаем переменные окружения
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=development

# 7. Открываем порт
EXPOSE 5000

# 8. Запускаем приложение
CMD ["flask", "run"]

