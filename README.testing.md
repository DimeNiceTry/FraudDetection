# Тестирование ML Service
  
Данная инструкция содержит набор команд для проверки работоспособности микросервисной системы ML Service.

## Подготовка к тестированию

Перед началом тестирования убедитесь, что:
1. Docker и Docker Compose установлены на вашей системе
2. Все порты (80, 8000, 5672, 15672, 5432) свободны
3. У вас есть доступ к интернету (для загрузки образов)

## Запуск системы

Для запуска всей системы выполните:

```bash
# Запуск системы с 3 ML воркерами (по умолчанию)
python start.py --start

# ИЛИ напрямую через Docker Compose
docker-compose up -d
```

## Проверка статуса сервисов

Проверьте, что все сервисы успешно запущены:

```bash
python start.py --status

# ИЛИ
docker-compose ps
```

Все сервисы должны иметь статус "Up" и "healthy" (для тех, где настроены healthcheck).

## Тестирование REST API

### 1. Проверка доступности API

```bash
# Проверка базового эндпоинта
curl http://localhost/

# Проверка healthcheck
curl http://localhost/health
```

Ожидаемый ответ от `/health`: `{"status":"healthy"}`

### 2. Создание пользователя и получение токена

```bash
# Создание нового пользователя
curl -X POST http://localhost/users \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpassword","email":"test@example.com"}'

# Получение токена
curl -X POST http://localhost/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword"
```

Сохраните полученный токен для дальнейших запросов.

### 3. Отправка запроса на предсказание

```bash
# Замените YOUR_TOKEN на полученный токен
curl -X POST http://localhost/predictions/predict \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"text":"Это положительный текст для анализа настроения"}}'
```

В ответе вы получите `prediction_id`, сохраните его для следующего шага.

### 4. Проверка статуса предсказания

```bash
# Замените YOUR_TOKEN и PREDICTION_ID на соответствующие значения
curl -X GET http://localhost/predictions/PREDICTION_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Изначально статус будет "pending", через несколько секунд выполните запрос снова чтобы увидеть результат.

### 5. Проверка баланса пользователя

```bash
# Замените YOUR_TOKEN на полученный токен
curl -X GET http://localhost/balance \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. Получение истории предсказаний

```bash
# Замените YOUR_TOKEN на полученный токен
curl -X GET http://localhost/predictions \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Тестирование через Swagger UI

Для более удобного тестирования API можно использовать Swagger UI:

1. Откройте в браузере http://localhost/docs
2. Выполните авторизацию через кнопку "Authorize" (используйте test/test или созданного пользователя)
3. Протестируйте эндпоинты через UI

## Тестирование RabbitMQ

1. Откройте в браузере http://localhost:15672/
2. Войдите с учетными данными (guest/guest)
3. Проверьте очереди ml_tasks и ml_results
4. Проверьте подключения (Connections) - должно быть видно подключения от ML Worker и других сервисов

## Проверка работы ML Worker

Просмотр логов ML Worker:

```bash
python start.py --logs ml-worker

# ИЛИ
docker-compose logs ml-worker
```

В логах должны быть видны сообщения о подключении к RabbitMQ и обработке заданий.

## Проверка обработки заданий ML Worker

1. Отправьте новое предсказание через API
2. Просмотрите логи ML Worker для подтверждения обработки:

```bash
docker-compose logs --follow ml-worker
```

Вы должны увидеть сообщения о получении задания, его обработке и отправке результата.

## Комплексный тест системы

Выполните следующую последовательность действий для проверки полного цикла работы системы:

1. Получите токен авторизации для тестового пользователя:
```bash
curl -X POST http://localhost/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test&password=test"
```

2. Отправьте запрос на предсказание:
```bash
curl -X POST http://localhost/predictions/predict \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"text":"пример текста для анализа"}}'
```

3. Откройте мониторинг RabbitMQ (http://localhost:15672/) и убедитесь, что сообщение прошло через очередь ml_tasks

4. Проверьте логи ML Worker, чтобы убедиться, что один из воркеров обработал задание:
```bash
docker-compose logs --tail=50 ml-worker
```

5. Проверьте результат предсказания через API:
```bash
curl -X GET http://localhost/predictions/PREDICTION_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Проверка масштабирования ML Worker

1. Увеличьте количество ML Worker:
```bash
docker-compose up -d --scale ml-worker=5
```

2. Проверьте, что новые воркеры запустились:
```bash
docker-compose ps
```

3. Отправьте несколько запросов на предсказание:
```bash
# Отправьте 5-10 запросов
curl -X POST http://localhost/predictions/predict \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"text":"текст для анализа"}}'
```

4. Проверьте логи ML Worker:
```bash
docker-compose logs ml-worker | grep "начинаем обработку предсказания"
```

Вы должны увидеть, что предсказания распределены между разными воркерами.

## Остановка системы

Для остановки системы:

```bash
python start.py --stop

# ИЛИ
docker-compose down
```

## Устранение неполадок

### RabbitMQ недоступен
```bash
# Проверка статуса
docker-compose logs rabbitmq

# Перезапуск сервиса
docker-compose restart rabbitmq
```

### Ошибки в ML Worker
```bash
# Проверка логов
docker-compose logs ml-worker

# Перезапуск сервиса
docker-compose restart ml-worker
```

### База данных недоступна
```bash
# Проверка статуса
docker-compose logs database

# Перезапуск сервиса
docker-compose restart database
```

### Проверка сети между контейнерами
```bash
# Войдите в контейнер ML Worker
docker exec -it $(docker ps -q -f name=ml-worker) /bin/bash

# Проверьте доступность других сервисов
ping rabbitmq
ping database
``` 