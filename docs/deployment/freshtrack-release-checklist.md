# FreshTrack release checklist

- [x] Backend tests: 30 passed.
- [x] TypeScript typecheck passed.
- [x] Vite production build passed.
- [x] Alembic PostgreSQL SQL generated from `DATABASE_URL` without SQLite fallback.
- [x] No production connection, SSH or deployment performed.
- [ ] Apply migration to a production backup and run downgrade rehearsal before release.
- [ ] Perform two-site manual acceptance for all five roles.
- [ ] Configure the external MAX scheduler process and verify one daily/weekly period key per object.
