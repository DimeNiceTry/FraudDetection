FROM python:3.9-slim

WORKDIR /bot

# Установка инструментов для диагностики
RUN apt-get update && apt-get install -y \
    curl \
    dnsutils \
    iputils-ping \
    net-tools \
    telnet \
    traceroute \
    ca-certificates \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Создание скрипта для настройки DNS и проверки доступности API
RUN echo '#!/bin/bash\n\
echo "=== Проверка конфигурации DNS ==="\n\
cat /etc/resolv.conf\n\
echo -e "\n=== Добавление IP адресов Telegram API в /etc/hosts ==="\n\
echo "149.154.167.99 api.telegram.org" >> /etc/hosts\n\
echo "149.154.167.220 api.telegram.org" >> /etc/hosts\n\
cat /etc/hosts\n\
echo -e "\n=== Проверка доступности API Telegram ==="\n\
python /bot/check_api.py || echo "API проверка не прошла, но продолжаем запуск"\n\
echo -e "\n=== Проверка завершена, запускаем бота ==="\n\
' > /bot/start.sh && chmod +x /bot/start.sh

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY . .

# Отключаем проверку SSL сертификатов
ENV PYTHONWARNINGS="ignore:Unverified HTTPS request"
ENV PYTHONHTTPSVERIFY=0

# Устанавливаем переменные окружения для контейнера
ENV PYTHONUNBUFFERED=1
ENV DB_HOST=database
ENV DB_PORT=5432
ENV RABBITMQ_HOST=rabbitmq
ENV RABBITMQ_PORT=5672

# Запуск Telegram бота
CMD ["/bin/bash", "-c", "./start.sh && python bot.py"] 