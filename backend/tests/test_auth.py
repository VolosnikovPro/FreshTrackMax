"""Tests for auth: seed-admin, login, and role-guarded access."""
from sqlalchemy import select

from app.models.user import User, UserRole
from app.models.site import Site


def test_seed_admin_creates_site_and_admin(client, session_factory):
    """seed-admin must create a DEFAULT site and bind the admin to it."""
    resp = client.post("/api/auth/seed-admin")
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    assert body["detail"] == "Admin created"
    assert body["username"] == "admin"

    # Verify in DB using a fresh session against the same shared DB
    async def _check():
        async with session_factory() as s:
            users = (await s.execute(select(User))).scalars().all()
            admin = next((u for u in users if u.username == "admin"), None)
            assert admin is not None
            assert admin.role == UserRole.admin
            assert admin.site_id is not None
            assert admin.max_user_id == -1  # integer placeholder, not a string
            site = await s.get(Site, admin.site_id)
            assert site is not None
            return True
    import asyncio
    assert asyncio.get_event_loop().run_until_complete(_check())


def test_seed_admin_idempotent(client):
    r1 = client.post("/api/auth/seed-admin")
    r2 = client.post("/api/auth/seed-admin")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["detail"] == "Admin already exists"


def test_login_with_seeded_admin(seeded_client):
    resp = seeded_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["username"] == "admin"
    assert data["user"]["site_id"] not in (0, None)


def test_login_wrong_password(seeded_client):
    resp = seeded_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_protected_route_requires_auth(client):
    resp = client.get("/api/products/")
    assert resp.status_code in (401, 403)


def test_protected_route_with_token(seeded_client, auth_header):
    resp = seeded_client.get("/api/products/", headers=auth_header)
    assert resp.status_code in (200, 201)


import asyncio


def _create_user_via_api(client, auth_header, username, role):
    resp = client.post(
        "/api/admin/users",
        headers=auth_header,
        json={"username": username, "display_name": username, "role": role, "password": "pass123"},
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


def _token_for(client, username):
    data = client.post(
        "/api/auth/login", json={"username": username, "password": "pass123"}
    ).json()
    return data["access_token"]


def test_role_isolation_storekeeper_blocked_from_admin(seeded_client, auth_header):
    """A storekeeper must NOT access admin-only endpoints (403)."""
    _create_user_via_api(seeded_client, auth_header, "klad", "storekeeper")
    h = {"Authorization": f"Bearer {_token_for(seeded_client, 'klad')}"}
    resp = seeded_client.get("/api/admin/users", headers=h)
    assert resp.status_code == 403


def test_role_isolation_manager_can_read_admin_summary(seeded_client, auth_header):
    """A manager CAN access admin_or_manager endpoints (e.g. /admin/summary)."""
    _create_user_via_api(seeded_client, auth_header, "mgr", "manager")
    h = {"Authorization": f"Bearer {_token_for(seeded_client, 'mgr')}"}
    resp = seeded_client.get("/api/admin/summary", headers=h)
    assert resp.status_code in (200, 201)


def test_admin_can_create_user(seeded_client, auth_header):
    """Admin can create a new user via /api/admin/users."""
    resp = seeded_client.post(
        "/api/admin/users",
        headers=auth_header,
        json={"username": "newuser", "display_name": "Новый", "role": "storekeeper", "password": "pw123"},
    )
    assert resp.status_code in (200, 201), resp.text
    assert resp.json()["username"] == "newuser"
    assert resp.json()["role"] == "storekeeper"
