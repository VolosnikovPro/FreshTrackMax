"""
Shared pytest fixtures.

Builds a fresh in-memory SQLite database for every test and overrides the
FastAPI `get_db` dependency so the TestClient talks to it. A default site and
an admin user are created; the admin token is available for authenticated calls.
"""
import asyncio
import os
import uuid

# Provide required settings BEFORE importing the app (Settings() reads env at import time).
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("MAX_BOT_TOKEN", "test-max-token")

from datetime import date, timedelta  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession  # noqa: E402

from app.db.database import Base, get_db  # noqa: E402
from app.core.security import hash_password, create_access_token  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.models.site import Site  # noqa: E402
from main import app  # noqa: E402  (imported after env is set)


def _unique_db_url():
    """Each test gets its own in-memory SQLite DB (unique shared cache name)."""
    name = f"testdb_{uuid.uuid4().hex}"
    return f"sqlite+aiosqlite:///file:{name}?mode=memory&cache=shared&uri=true"


@pytest.fixture(scope="function")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def engine():
    url = _unique_db_url()
    os.environ["DATABASE_URL"] = url  # keep settings.DATABASE_URL in sync for app
    eng = create_async_engine(url, connect_args={"check_same_thread": False})
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture(scope="function")
async def session_factory(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory


@pytest_asyncio.fixture(scope="function")
async def db(session_factory):
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture(scope="function")
async def seeded(session_factory):
    """Default site + admin user."""
    async with session_factory() as s:
        site = Site(name="Тестовый объект", code="TEST", is_active=True)
        s.add(site)
        await s.flush()
        admin = User(
            username="admin",
            display_name="Admin",
            role=UserRole.admin,
            max_user_id=-1,
            site_id=site.id,
            hashed_password=hash_password("admin123"),
        )
        s.add(admin)
        await s.commit()
    return {"site_id": site.id, "admin_id": admin.id}


@pytest.fixture(scope="function")
def client(session_factory):
    """TestClient with get_db overridden to use the test engine (unseeded DB)."""

    async def _override_get_db():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def seeded_client(session_factory, seeded):
    """TestClient with a pre-seeded admin user (for authenticated calls)."""

    async def _override_get_db():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_token(seeded):
    token = create_access_token({"sub": str(seeded["admin_id"])})
    return token


@pytest.fixture(scope="function")
def auth_header(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="function")
def make_future_date():
    def _make(days: int) -> str:
        return (date.today() + timedelta(days=days)).isoformat()
    return _make
