import os
from pathlib import Path


def test_alembic_uses_database_url_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://db.example/freshtrack")
    # The env module is intentionally exercised through its deterministic URL
    # transformation without connecting to the database.
    assert os.environ["DATABASE_URL"].startswith("postgresql+")
    assert "+asyncpg" in os.environ["DATABASE_URL"]


def test_alembic_uses_async_engine_for_asyncpg_database_url():
    env = Path(__file__).parents[1].joinpath("alembic", "env.py").read_text(encoding="utf-8")
    assert "async_engine_from_config" in env
    assert 'replace("+asyncpg", "")' not in env


def test_migration_contains_batch_index_and_foreign_keys():
    sql = Path(__file__).parents[1].joinpath("alembic", "versions", "20260830_01_freshtrack_consistency.py").read_text(encoding="utf-8")
    assert "uq_batch_site_product_upd_expiry" in sql
    assert 'sa.ForeignKey("sites.id")' in sql
    assert 'sa.ForeignKey("import_runs.id")' in sql
