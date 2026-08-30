# FreshTrack: безопасная миграция

Перед миграцией сделайте проверенный backup и выполните команды отдельно от запуска приложения:

```powershell
cd backend
$env:DATABASE_URL = "<production sqlalchemy URL>"
alembic current
alembic upgrade head
```

URL проверяется оператором без вывода пароля (допустимы только production-хост и схема; URL с `test.db` запрещён). После upgrade выполните smoke-check таблиц `alembic_version`, `import_runs`, `daily_financial_expenses`, `audit_logs`, `batches.status/upd_number` и проверьте уникальные индексы.

После проверки бэкапа назначьте `superadmin` только явной командой для согласованной учетной записи (не по имени и не по первому ID):

```sql
UPDATE users SET role = 'superadmin' WHERE id = <ЯВНО СОГЛАСОВАННЫЙ_ID>;
```

ID подставляется оператором из защищенной инвентаризации учетных записей; он не хранится в коде, миграции, тестах или `.env`. Production-база не меняется автоматически при старте backend. Перед деплоем выполните backend-тесты, typecheck и production build, затем перезапустите backend с теми же секретами, не включая их в логи.
