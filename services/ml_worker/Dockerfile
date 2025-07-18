FROM python:3.9-slim

# Установка необходимых зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Создание директории для моделей
RUN mkdir -p /models

# Копирование исходного кода
COPY . .

# Команда запуска
CMD ["python", "main.py"] 