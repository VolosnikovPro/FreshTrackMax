# FreshTrack MVP

Система контроля сроков годности и учёта расхода сырья.

## Стек

| Слой | Технология |
|------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2 (async), SQLite → PostgreSQL |
| Frontend | React 18, TypeScript, Vite, React Router 6 |
| Авторизация | JWT Bearer + MAX OAuth (placeholder) |
| Уведомления | MAX Bot API (placeholder) |
| Импорт данных | CSV upload / Google Sheets (placeholder) |

---

## Быстрый старт

### Backend

```bash
cd backend

# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Скопировать конфиг
cp .env.example .env
# Отредактировать .env при необходимости

# Запустить
uvicorn main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

**Первый запуск — создать admin:**
```bash
curl -X POST http://localhost:8000/api/auth/seed-admin
# -> admin / admin123
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# -> http://localhost:5173
```

---

## Роли пользователей

| Роль | Права |
|------|-------|
| `admin` | Полный доступ, управление пользователями |
| `manager` | Просмотр всего, ввод питающихся, запуск уведомлений |
| `storekeeper` | Управление партиями / сроками годности |
| `nutrition_manager` | Себестоимость, ежедневный расход |

---

## API эндпоинты

```
POST   /api/auth/login              Локальный вход
POST   /api/auth/max                Вход через MAX
POST   /api/auth/seed-admin         Создать первого admin (dev only)

GET    /api/products/               Список продуктов
POST   /api/products/               Создать продукт
PUT    /api/products/{id}           Обновить продукт
DELETE /api/products/{id}           Деактивировать продукт

GET    /api/batches/                Все партии
GET    /api/batches/expiring/urgent Срочно истекающие (< 16 дн.)
GET    /api/batches/expiring/planned Планово истекающие (< 46 дн.)
POST   /api/batches/                Создать партию
PUT    /api/batches/{id}            Обновить партию
DELETE /api/batches/{id}            Удалить партию

GET    /api/costs/                  Себестоимость
POST   /api/costs/                  Создать запись
PUT    /api/costs/{id}              Обновить запись

GET    /api/consumption/            Расход (с фильтром по дате)
POST   /api/consumption/            Внести расход
PUT    /api/consumption/{id}        Обновить запись

GET    /api/headcount/              Список записей о питающихся
GET    /api/headcount/today         Сегодняшняя запись
POST   /api/headcount/              Внести (upsert по дате)

POST   /api/notifications/trigger/urgent   Запустить срочные уведомления
POST   /api/notifications/trigger/planned  Запустить плановые уведомления
GET    /api/notifications/config           Настройки уведомлений

GET    /api/admin/summary           Сводная статистика
GET    /api/admin/users             Список пользователей
POST   /api/admin/users             Создать пользователя
PUT    /api/admin/users/{id}        Обновить пользователя
GET    /api/admin/me                Текущий пользователь

POST   /api/sheets/import/csv       Импорт из CSV
POST   /api/sheets/import/sheets    Импорт из Google Sheets (placeholder)
```

---

## Структура проекта

```
freshtrack/
├── backend/
│   ├── main.py                    Точка входа FastAPI
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── api/routes/            Маршруты API
│       │   ├── auth.py
│       │   ├── products.py
│       │   ├── batches.py
│       │   ├── costs.py
│       │   ├── consumption.py
│       │   ├── headcount.py
│       │   ├── notifications.py
│       │   ├── admin.py
│       │   └── sheets.py
│       ├── core/
│       │   ├── config.py          Настройки (pydantic-settings)
│       │   └── security.py        JWT, роли, зависимости
│       ├── db/
│       │   └── database.py        SQLAlchemy async engine
│       ├── models/                ORM модели
│       └── schemas/               Pydantic схемы
└── frontend/
    ├── index.html
    ├── vite.config.ts
    ├── package.json
    └── src/
        ├── main.tsx
        ├── App.tsx                Роутинг
        ├── api/index.ts           Axios клиент + все API-функции
        ├── hooks/useAuth.tsx      Auth context
        ├── types/index.ts         TypeScript типы
        ├── components/common/
        │   ├── Layout.tsx         Сайдбар + основной layout
        │   └── UI.tsx             Переиспользуемые компоненты
        └── pages/
            ├── LoginPage.tsx
            ├── DashboardPage.tsx
            ├── ProductsPage.tsx
            ├── BatchesPage.tsx
            ├── CostsPage.tsx
            ├── ConsumptionPage.tsx
            ├── HeadcountPage.tsx
            ├── NotificationsPage.tsx
            └── AdminPage.tsx
```

---

## Плейсхолдеры (требуют доработки для production)

### MAX авторизация
Файл: `backend/app/api/routes/auth.py` → `max_auth()`
Нужно: валидировать `max_token` через MAX OAuth API перед выдачей JWT.

### MAX уведомления
Файл: `backend/app/api/routes/notifications.py` → `_send_max_message()`
Нужно: настроить `MAX_BOT_TOKEN` в `.env`. Сейчас в dev-режиме сообщения выводятся в консоль.

### Google Sheets
Файл: `backend/app/api/routes/sheets.py` → `import_from_google_sheets()`
Нужно: добавить `gspread` в requirements, настроить `GOOGLE_SERVICE_ACCOUNT_JSON` и раскомментировать код.

### Автоматический планировщик уведомлений
Не реализован в MVP. Для production добавить APScheduler или celery-beat:
```python
# Пример с APScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler()
scheduler.add_job(trigger_planned_notifications, 'cron', day_of_week='sun', hour=9)
```

### PostgreSQL (для production)
Заменить в `.env`:
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost/freshtrack
```
И добавить `asyncpg` в requirements.txt.

---

## Переключение на PostgreSQL

1. `pip install asyncpg`
2. В `.env`: `DATABASE_URL=postgresql+asyncpg://user:pass@localhost/freshtrack`
3. Применить миграции через Alembic или пересоздать таблицы при запуске
