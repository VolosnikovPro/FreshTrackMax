# FreshTrack Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` (recommended) or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Устранить блокирующие дефекты аудита FreshTrack, привести роли, импорт, учет остатков, себестоимость, миграции и уведомления к согласованному ТЗ.

**Architecture:** Источник прав объекта должен быть единым (`resolve_site_id`) и использоваться каждым endpoint. Складские изменения выполняются только как транзакционные движения с блокировкой партий; отмена импорта является компенсирующей транзакцией с проверкой зависимостей. Frontend использует те же права, что API, но не заменяет серверную авторизацию.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, PostgreSQL production / SQLite tests, React, TypeScript, Vite, pytest, openpyxl.

## Global Constraints

- Не откатывать и не удалять существующие пользовательские изменения.
- Роли: `superadmin` (Главный администратор), `admin` (Администратор), `storekeeper` (Кладовщик), `manager` (УПП), `nutrition_manager` (УОП).
- Переключать объекты могут только `superadmin` и `admin`; остальные всегда работают только со своим `site_id`.
- Продукты и партии после создания неизменяемы. Корректировка выполняется новым документом, импортом или аудируемой отменой.
- Все денежные расчеты выполняются через `Decimal`; результат округляется до двух знаков `ROUND_HALF_UP`.
- Не использовать `Base.metadata.create_all()` для production-обновлений.
- Нельзя деплоить до успешного выполнения всех приемочных тестов из раздела «Итоговая приемка».

## Ролевая матрица

| Модуль | superadmin | admin | storekeeper | manager (УПП) | nutrition_manager (УОП) |
| --- | --- | --- | --- | --- | --- |
| Dashboard | выбранный объект | выбранный объект | нет | нет | свой объект |
| Products | view/create | view/create | view/create/search | нет | view |
| Batches | view/create/search/delete | view/create/search/delete | view/create/search | нет | view |
| Consumption | view | view | импорт расхода | нет | view |
| Financial expense + headcount | view | view | нет | ввод одной формой | view |
| Daily cost | view | view | нет | view | view |
| Risk report | import/cancel | import/cancel | import only | нет | нет |
| Notifications | send | send | send | send | send |
| Sites/users | full management | нет | нет | нет | нет |

---

### Task 1: Исправить Alembic и безопасный путь миграции

**Files:**
- Modify: `backend/alembic/env.py`
- Modify: `backend/alembic.ini`
- Modify: `backend/alembic/versions/20260830_01_freshtrack_consistency.py`
- Modify: `docs/deployment/freshtrack-migration.md`
- Create: `backend/tests/test_migrations.py`

**Interfaces:**
- Alembic получает URL из `settings.DATABASE_URL` или переменной `DATABASE_URL`; значение `sqlalchemy.url` в ini используется только как безопасный локальный fallback.
- Миграция создает все FK, уникальные ограничения и индексы, отраженные в SQLAlchemy-моделях.

- [ ] **Step 1: Написать падающие проверки конфигурации и схемы**

```python
def test_alembic_uses_database_url_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://db.example/freshtrack")
    assert migration_url() == "postgresql+psycopg://db.example/freshtrack"

def test_migration_defines_batch_and_import_foreign_keys():
    sql = generate_upgrade_sql()
    assert "uq_batch_site_product_upd_expiry" in sql
    assert "FOREIGN KEY(site_id) REFERENCES sites" in sql
```

- [ ] **Step 2: Исправить `env.py`**

В начале после `config = context.config` установить URL из settings:

```python
from app.core.config import settings

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```

Обе ветки (`run_migrations_offline`, `run_migrations_online`) должны использовать уже обновленный `config`. В `alembic.ini` оставить нейтральный placeholder, не `test.db`.

- [ ] **Step 3: Дополнить миграцию**

- Добавить FK для `daily_financial_expenses`, `import_fingerprints`, `import_runs`, `import_changes`, `consumption_allocations`, `audit_logs`.
- Создать `uq_batch_site_product_upd_expiry` и индексы, определенные моделями.
- Пометить уже нулевые партии как `archived`.
- Добавить недостающие таблицы/поля уведомлений из Task 6.
- Задать корректную цепочку `down_revision`: если в production нет прежних ревизий, сохранить baseline-подход, но проверить его на копии непустой старой БД.

- [ ] **Step 4: Обновить инструкцию деплоя**

Добавить обязательные команды: backup, вывод фактического URL без пароля/хоста, `alembic current`, `alembic upgrade head`, smoke-check таблиц, и запрет применения миграции при URL, содержащем `test.db`.

- [ ] **Step 5: Проверить**

Run: `backend/.venv/Scripts/python.exe -m pytest tests/test_migrations.py -q`

Expected: PASS. Затем выполнить `alembic upgrade head --sql` с явно заданным PostgreSQL URL и убедиться, что SQL соответствует PostgreSQL, а не SQLite.

### Task 2: Сделать FEFO и отмену импорта учетно корректными

**Files:**
- Modify: `backend/app/services/consumption_service.py`
- Modify: `backend/app/services/import_service.py`
- Modify: `backend/app/api/routes/sheets.py`
- Modify: `backend/app/models/import_history.py`
- Modify: `backend/tests/test_fefo.py`
- Modify: `backend/tests/test_import.py`

**Interfaces:**
- `write_off_consumption_fefo(...)` блокирует строки партий в порядке FEFO и возвращает точные allocations.
- `cancel_import(import_id, ...)` выполняет компенсирующую транзакцию и возвращает `409` с зависимостями, если отмена небезопасна.

- [ ] **Step 1: Добавить тесты инвариантов**

```python
def test_cancel_consumption_import_removes_consumption_and_restores_batch(...):
    run = import_consumption_file(...)
    cancel(run.id)
    assert batch.quantity == original_quantity
    assert daily_consumptions_for_run(run.id) == []

def test_newer_dependent_import_blocks_cancel(...):
    older, newer = import_two_dependent_files(...)
    response = cancel(older.id)
    assert response.status_code == 409
    assert response.json()["detail"]["dependent_import_ids"] == [newer.id]
```

- [ ] **Step 2: Заблокировать конкурентное списание**

В `write_off_consumption_fefo` выбрать партии через `select(Batch)...with_for_update()` (для SQLite тестов допустима эквивалентная сериализация). Проверять `status == "active"`, `quantity > 0`, сортировать по `expiry_date`, затем `id`.

- [ ] **Step 3: Сохранить полную историю изменений импорта**

При каждом создании/пополнении продукта, партии, legacy-cost и записи расхода создавать `ImportChange` с последовательностью, состоянием до/после и версией. Для расхода сохранять связь `DailyConsumption.import_run_id` либо отдельную обязательную связь, чтобы отмена не полагалась только на заметки.

- [ ] **Step 4: Реализовать компенсирующую отмену**

В одной транзакции:

1. Заблокировать `ImportRun` и связанные allocations/изменения.
2. Найти более новые активные импорты, затрагивающие те же партии/сущности; при наличии вернуть `409` с ID и рекомендуемым порядком.
3. Удалить или компенсировать только записи, созданные отменяемым импортом; для пополнений восстановить значение `before_value`.
4. Восстановить партии из `batch_before`, включая `status`.
5. Изменить `ImportRun.status` на `cancelled`, заполнить автора, время и причину, создать `AuditLog`.
6. Не очищать SHA-фингерпринт для обычного повторного импорта. Разрешить отдельный endpoint подтвержденного replay только admin/superadmin, который создает новую `attempt` и `replay_of`.

- [ ] **Step 5: Запретить ручное изменение расхода**

Убрать `PUT /consumption/{id}` и обычное физическое удаление либо вернуть `409` с кодом `CONSUMPTION_IMMUTABLE`. Административная корректировка проводится только отменой соответствующего импорта.

- [ ] **Step 6: Проверить**

Run: `backend/.venv/Scripts/python.exe -m pytest tests/test_fefo.py tests/test_import.py -q`

Expected: PASS, включая параллельный тест, где два одновременных списания не дают отрицательный остаток.

### Task 3: Привести API к пяти ролям и изоляции объектов

**Files:**
- Modify: `backend/app/api/routes/sheets.py`
- Modify: `backend/app/api/routes/consumption.py`
- Modify: `backend/app/api/routes/costs.py`
- Modify: `backend/app/api/routes/headcount.py`
- Modify: `backend/app/api/routes/batches.py`
- Modify: `backend/app/api/routes/admin.py`
- Create: `backend/tests/test_role_matrix.py`

**Interfaces:**
- Каждый endpoint принимает необязательный `site_id` только там, где admin/superadmin должны работать с выбранным объектом; lower roles получают `403` для чужого объекта.

- [ ] **Step 1: Создать параметризованный тест ролей**

```python
@pytest.mark.parametrize("role,path,method,expected", [
    (UserRole.storekeeper, "/api/sheets/import/file?import_type=consumption_file", "POST", 200),
    (UserRole.storekeeper, "/api/sheets/import/file?import_type=cost_sheet", "POST", 403),
    (UserRole.manager, "/api/costs/financial", "POST", 201),
    (UserRole.admin, "/api/costs/financial", "POST", 403),
    (UserRole.nutrition_manager, "/api/consumption/", "POST", 403),
])
def test_role_matrix(...): ...
```

- [ ] **Step 2: Ограничить импорт по типу**

- `risk_report`: `superadmin`, `admin`, `storekeeper`.
- `consumption_file`: только `storekeeper`.
- `cost_sheet`: только legacy-режим admin/superadmin, не использовать в договорной себестоимости.
- История и отмена: `superadmin`, `admin`.
- Google Sheets принимает и проверяет `site_id`; при ошибке импорт откатывается, а не коммитит частичные данные.

- [ ] **Step 3: Ограничить финансовый ввод**

- `POST /costs/financial`: только `manager`.
- `GET /costs/financial`: `superadmin`, `admin`, `manager`, `nutrition_manager`.
- `POST/PUT /headcount`: только `manager`; admin/superadmin/УОП только читают.
- Для создания legacy `RawMaterialCost` и `DailyHeadcount` использовать `data.model_dump(exclude={"site_id"})`, чтобы исключить двойной аргумент `site_id`.

- [ ] **Step 4: Привести объекты к выбранному site**

Добавить `site_id` в detail/delete endpoints партий и продуктов, endpoint `headcount/today`, urgent/planned batch endpoints, stock check и ручные notifications. Все вызовы выполняют `resolve_site_id(db, current_user, site_id)`.

- [ ] **Step 5: Аудировать административные действия**

Удаление партии выполняет проверку зависимостей, пишет `AuditLog` с before-value и не допускает удаления, если имеются allocations/импорты, требующие сохранения партии.

- [ ] **Step 6: Проверить**

Run: `backend/.venv/Scripts/python.exe -m pytest tests/test_role_matrix.py tests/test_auth.py -q`

Expected: PASS. Для каждой lower role запрос с чужим `site_id` возвращает 403, а не данные другого объекта.

### Task 4: Реализовать договорную себестоимость и ее интерфейс

**Files:**
- Modify: `backend/app/api/routes/costs.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `frontend/src/api/index.ts`
- Modify: `frontend/src/routes/index.tsx`
- Rewrite: `frontend/src/pages/CostsPage.tsx`
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Modify: `frontend/src/pages/HeadcountPage.tsx`
- Modify: `backend/tests/test_import.py`

**Interfaces:**
- `financialApi.upsert({site_id?, date, invoice_amount_net, headcount})` доступен УПП.
- `financialApi.list({site_id?, month})` возвращает `rows: [{date, invoice_amount_net, headcount, daily_cost}]` и `average`.

- [ ] **Step 1: Написать тесты расчета**

```python
def test_financial_entry_is_atomic_and_uses_decimal(...):
    result = post_financial(date="2026-08-30", invoice_amount_net="100.00", headcount=3)
    assert result["daily_cost"] == "33.33"

def test_zero_headcount_returns_null_cost_without_division_error(...):
    result = post_financial(..., headcount=0)
    assert result["daily_cost"] is None
```

- [ ] **Step 2: Серверная реализация**

Одна форма УПП должна создавать/обновлять `DailyFinancialExpense` и `DailyHeadcount` в одной транзакции. Для исправления сохранять аудируемую версию `AuditLog` с before/after, не изменяя партии и расход.

- [ ] **Step 3: Frontend**

- Добавить УПП маршрут `/costs` и убрать у него legacy CRUD цен.
- На странице УПП показать форму `дата + сумма без НДС + количество питающихся`.
- Для superadmin/admin/УОП показать read-only таблицу `Дата | Себестоимость дня` и среднее за месяц.
- На dashboard УОП заменить заглушку фактическими значениями API.
- `headcount/today` и список должны передавать выбранный `site_id` для admin/superadmin.

- [ ] **Step 4: Проверить**

Run: `cd frontend && node_modules/.bin/tsc --noEmit && npm run build`

Expected: обе команды завершаются с кодом 0. Проверить в браузере пять ролей и два объекта.

### Task 5: Завершить импорт и интерфейс истории

**Files:**
- Modify: `backend/app/services/import_service.py`
- Modify: `backend/app/api/routes/sheets.py`
- Modify: `frontend/src/api/index.ts`
- Modify: `frontend/src/pages/AdminPage.tsx`
- Create: `frontend/src/pages/ImportPage.tsx` (если отдельный рабочий экран нужен для админа и кладовщика)
- Modify: `backend/tests/test_import.py`

**Interfaces:**
- Ответ импорта содержит `site_id`, название объекта, тип, число строк/товаров/партий/операций, ошибки без traceback.
- `POST /sheets/import/sheets` принимает `site_id`.

- [ ] **Step 1: Зафиксировать поддерживаемые форматы тестами**

Покрыть canonical `Дата | Товар | Ед. изм. | Количество`; если клиентский файл действительно использует матрицу дней `1..31`, добавить обязательные `month` и `year` и тесты дат/нулей/пустых ячеек.

- [ ] **Step 2: Сделать валидацию строгой**

Проверять дату, положительность, единицу измерения, продукт по SKU при наличии, иначе по нормализованному имени. Недостаточный остаток или ошибка любой строки откатывает весь файл и возвращает 400 с номером строки.

- [ ] **Step 3: Реализовать UI по ролям**

- Отдельно открыть импорт Кладовщику только для `consumption_file` и только своего объекта.
- Дать admin/superadmin импорт риск-отчета, выбранный объект, историю, причину отмены, список зависимостей и кнопку подтвержденного replay.
- Не показывать УПП и УОП импорт или административное управление.

- [ ] **Step 4: Проверить**

Run: `backend/.venv/Scripts/python.exe -m pytest tests/test_import.py -q`

Expected: PASS для SHA-409, атомарности, FEFO, отмены, replay и двух объектов.

### Task 6: Доработать уведомления и аудит

**Files:**
- Modify: `backend/app/models/notification.py`
- Modify: `backend/app/api/routes/notifications.py`
- Create: `backend/app/services/notification_scheduler.py`
- Modify: `backend/main.py`
- Modify: `backend/app/api/routes/admin.py`
- Modify: `frontend/src/api/index.ts`
- Modify: `frontend/src/pages/NotificationsPage.tsx`
- Modify: `frontend/src/pages/AdminPage.tsx`
- Create: `backend/tests/test_notifications_idempotency.py`

**Interfaces:**
- Уведомление имеет `period_key`; уникальный ключ `(site_id, notification_type, period_key)`.
- Журнал хранит запуск и результат каждого получателя: `sent`, `failed`, `skipped`, reason, timestamp.

- [ ] **Step 1: Добавить тесты диапазонов и идемпотентности**

```python
def test_urgent_is_le_15_and_planned_is_16_to_45(...): ...

def test_two_scheduler_instances_create_one_period_notification(...): ...
```

- [ ] **Step 2: Реализовать планировщик**

Срочные уведомления запускать ежедневно, плановые еженедельно. Использовать БД-уникальность и обработку `IntegrityError`, а не только память процесса. Ручный запуск неуспешной отправки разрешать повторно и логировать отдельно.

- [ ] **Step 3: Привести frontend к выбранному объекту**

`triggerUrgent(siteId)` и `triggerPlanned(siteId)` передают `site_id`; lower roles не передают чужой объект. Убрать текст «менее N дней» и заменить на точные диапазоны `<=15` и `16-45`.

- [ ] **Step 4: Исправить экспорт аудита**

Перед записью CSV/XLSX сериализовать JSON поля через `json.dumps(value, ensure_ascii=False, default=str)`. Добавить фильтры: объект, период, действие, сущность/тип, статус и пользователь. Не экспортировать пароли, токены и хэши.

- [ ] **Step 5: Проверить**

Run: `backend/.venv/Scripts/python.exe -m pytest tests/test_notifications.py tests/test_notifications_idempotency.py -q`

Expected: PASS. Открытие XLSX с JSON-полями не вызывает `ValueError`.

### Task 7: Финальная приемка и деплой-гейт

**Files:**
- Modify: `docs/deployment/freshtrack-migration.md`
- Create: `docs/deployment/freshtrack-release-checklist.md`

- [ ] **Step 1: Выполнить полный backend-прогон**

Run: `backend/.venv/Scripts/python.exe -m pytest -q`

Expected: PASS без предупреждений о неразрешенном цикле внешних ключей.

- [ ] **Step 2: Выполнить frontend-проверки**

Run: `cd frontend && node_modules/.bin/tsc --noEmit`

Run: `cd frontend && npm run build`

Expected: обе команды завершаются с кодом 0.

- [ ] **Step 3: Провести приемку пяти ролей на двух объектах**

Проверить навигацию, прямые URL и API: переключение только superadmin/admin; Кладовщик импортирует расход только своего объекта; УПП вводит финансовую форму; УОП видит read-only dashboard/себестоимость; админ импортирует/отменяет риск-отчет на выбранном объекте.

- [ ] **Step 4: Проверить migration rehearsal**

Применить миграцию к резервной копии production-схемы, проверить FK/unique/indexes, выполнить `alembic downgrade -1` на копии и зафиксировать результат в release checklist.

- [ ] **Step 5: Commit**

```bash
git add backend frontend docs
git commit -m "fix: complete FreshTrack audit remediation"
```

## Итоговая приемка

- [ ] Миграция использует реальный `DATABASE_URL`, а не `test.db`.
- [ ] Ни один endpoint не нарушает ролевую матрицу или изоляцию объектов.
- [ ] Расход, FEFO, отмена и повторный импорт не создают расхождения между остатком и журналом расхода.
- [ ] Параллельное списание не дает отрицательный остаток.
- [ ] УПП вводит сумму и питающихся одной операцией; все разрешенные роли видят расчетную себестоимость.
- [ ] Номер УПД уникально идентифицирует партию вместе с объектом, продуктом и сроком.
- [ ] Уведомления имеют точные диапазоны, автоматический запуск и защиту от дублей.
- [ ] CSV и XLSX журналы экспортируются с JSON-значениями и фильтрами.
- [ ] Backend tests, TypeScript и Vite build проходят.

## Self-Review

План покрывает все выявленные P0/P1: неправильную миграцию, неполную отмену, конкурентный FEFO, ролевые расхождения, недоступную себестоимость, `500` в формах, неполную историю импорта, уведомления и XLSX-аудит. Матрица ролей, требования ТЗ и тестовые гейты встроены в отдельные задачи. В документе нет намеренных заглушек; матричный формат расхода включается только после подтверждения, что именно такой файл использует клиент.
