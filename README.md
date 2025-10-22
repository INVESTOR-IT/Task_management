<h1 align="center">Aсинхронный сервис управления задачами (в разработке)</h1>

---

### О проекте (легким зяыком)
Задача написать приложение (из 4-х контейнеров), которое принимает задачи имеющие
статус и приоритеты.<br>
1-й контейнер (api) принимает задачу и отправляет в 2-й контейнер (RabbitMQ)<br>
3-й контейнер (worker) получает задачу с брокера сообщений и выполняет её (работа логики имитирована)<br>
4-й контейнер (PostgreSQL), куда записываются задачи с момента получения и до момента выполнения задачи<br>

</br>

### ТЗ к приложению:
Основные возможности:
-	Создание задач через REST API
-	Асинхронная обработка задач в фоновом режиме
-	Возможность параллельной обработки нескольких задач
-	Система приоритетов для задач

Статусная модель задач:
-	NEW - новая задача
-	PENDING - ожидает обработки
-	IN_PROGRESS - в процессе выполнения
-	COMPLETED - завершено успешно
-	FAILED - завершено с ошибкой
-	CANCELLED – отменено

Требования к задачам:
-	Каждая задача должна иметь уникальный идентификатор
-	Задачи должны содержать:
	-	Название
	-	Описание
    -	Приоритет (LOW, MEDIUM, HIGH)
    -	Cтатус
    -	Время создания
    -	Время начала выполнения
    -	Время завершения
    -	Результат выполнения
    -	Информация об ошибках (если есть)

Эндпоинты:
-	POST /api/v1/tasks - создание задачи
-	GET /api/v1/tasks - получение списка задач с фильтрацией и пагинацией
-	GET /api/v1/tasks/{task_id} - получение информации о задаче
-	DELETE /api/v1/tasks/{task_id} - отмена задачи
-	GET /api/v1/tasks/{task_id}/status - получение статуса задачи

---

### Реализация проекта
Я разделил задачу на два основных сервиса:<br>
1. API Service (FastAPI): Обрабатывает входящие HTTP-запросы (создание, получение, отмена задач). Он записывает начальное состояние задачи в базу данных и отправляет сообщение в RabbitMQ для асинхронной обработки.
2. Worker Service (Python Consumer): Постоянно слушает RabbitMQ, забирает сообщения о задачах, обрабатывает их (имитируем работу) и обновляет статус и результат задачи в базе данных.


### Тех стек
`Python, FastAPI, Uvicorn, PostgreSQL, SQLAlchemy, Alembic, RabbitMQ, Aio_pika, Pytest, Docker и Docker Compose`

</br>

### Структура проекта
```
├── app
│   ├── api
│   │   └── v1
│   │       └── tasks.py             # API-эндпоинты для задач
│   ├── core
│   │   └── config.py                # Конфигурация приложения
│   ├── db
│   │   ├── database.py              # Инициализация БД
│   │   └── base.py                  # Базовый класс для моделей SQLAlchemy
│   ├── models
│   │   └── task.py                  # Модель задачи SQLAlchemy
│   ├── queue
│   │   └── producer.py              # Отправка сообщений в RabbitMQ
│   ├── schemas
│   │   └── task.py                  # Pydantic схемы 
│   ├── worker
│   │   ├── consumer.py              # Приемка сообщений из RabbitMQ
│   │   ├── processor.py             # Логика обработки задачи
│   │   └── worker.py                # Главный файл workerа
│   └── main.py                      # Главный файл
├── migrations                       # Каталог Alembic для миграций
│   ├── versions
│   └── env.py                       # Основные настройки Alembic
├── tests
│   ├── unit                         # Юнит-тесты
│   └── integration                  # Интеграционные тесты
│       └── test_tasks_api.py        # Тесты 
├── .env.example                     # Пример файла переменных окружения
├── docker-compose.yml               # Описание сервисов Docker Compose
├── Dockerfile.api                   # Dockerfile для API сервиса
├── Dockerfile.worker                # Dockerfile для Worker сервиса
├── requirements.txt                 # Зависимости Python
├── alembic.ini                      # Конфигурация Alembic
├── .gitignore                       # Игнорирование для git
├── .dockerignore                    # Игнорирование для Docker
└── README.md                        # Документация проекта
```

---

## Развертывание 

1. Клонирование приложения
```
git clone https://github.com/INVESTOR-IT/Task_management
```

2. Создание и инициализация .env (замените параметры на свои, __обязательно__)
```
cp .env.example .env
```

3. Развертывание
```
docker-compose up --build
```
Последним развернется workeк, после приложением можно будет пользоваться 
___

## Эндпоинты 

__Документация__ (GET)
```
http://localhost:8000
```
Произойдет редирект (307) на OpenAPI

</br>

__Создание задачи__ (POST)
```
http://localhost/api/v1/tasks
```
Ожидает Json тело, пример
```
{
    "title": "Тренировка",
    "description": "Сделать пробежку",
    "priority": "HIGH"      # варианты: (LOW, MEDIUM, HIGH),  опционально
}
```

Пример ответа
```
{
    "title": "Тренировка",
    "description": "Сделать пробежку",
    "priority": "HIGH",
    "id": "626b4ee0-bd98-4029-a10d-c3d3394209e3",
    "status": "PENDING",
    "created_at": "2025-10-22T15:24:06.753500",
    "started_at": null,
    "completed_at": null,
    "result": null,
    "error_info": null
}
```

</br>

__Список задач с пагинацией__ (GET)
```
http://localhost/api/v1/tasks
```
Из Query параметров для филтрации:
- status: статус задачи (NEW, PENDING, IN_PROGRESS, COMPLETED, FAILED, CANCELLED)
- priority: приоритет задачи (LOW, MEDIUM, HIGH)
- page: n >= 1, нужная нам страница
- page_size: 100 >= n >= 1, количество задач на странице

Пример ответа
```
{
    "total": 0,
    "page": 1,
    "page_size": 10,
    "items": [
        # задачи
    ]
}
```

</br>

__Информация о задаче__ (GET)
```
http://localhost:8000/api/v1/tasks/{task_id}
```

Пример ответа:
```
{
    "title": "Тренировка",
    "description": "Сделать пробежку",
    "priority": "HIGH",
    "id": "626b4ee0-bd98-4029-a10d-c3d3394209e3",
    "status": "COMPLETED",
    "created_at": "2025-10-22T15:24:06.753500",
    "started_at": "2025-10-22T15:24:06.933436",
    "completed_at": "2025-10-22T15:24:12.955402",
    "result": "Задача завершена за 6 сек.",
    "error_info": null
}
```

</br>

__Отмена задачи__ (DELETE)
```
http://localhost:8000/api/v1/tasks/{task_id}
```
Пример ответа, если задаче не в статусе NEW или PENDING
```
{
    "detail": "Задача со статусом COMPLETED не может быть отменена"
}
```

</br>

__Информация о статусе задачи__ (GET)
```
http://localhost:8000/api/v1/tasks/{task_id}/status
```
Пример ответа
```
{
    "id": "626b4ee0-bd98-4029-a10d-c3d3394209e3",
    "status": "COMPLETED"
}
```

</br>

## Тесты

---

<h3 align="center">Документация в разработке</h3>