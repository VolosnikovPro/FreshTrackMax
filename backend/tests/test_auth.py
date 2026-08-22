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


def test_sites_endpoints_registered_and_crud(seeded_client, auth_header):
    """Sites CRUD is wired into the app router and admin can manage sites."""
    # list
    resp = seeded_client.get("/api/sites/", headers=auth_header)
    assert resp.status_code in (200, 201), resp.text
    assert any(s["code"] == "TEST" for s in resp.json())

    # create
    resp = seeded_client.post(
        "/api/sites/",
        headers=auth_header,
        json={"name": "Филиал 2", "code": "BR2", "is_active": True},
    )
    assert resp.status_code in (200, 201), resp.text
    site_id = resp.json()["id"]
    assert resp.json()["code"] == "BR2"

    # get
    resp = seeded_client.get(f"/api/sites/{site_id}", headers=auth_header)
    assert resp.status_code in (200, 201)

    # update
    resp = seeded_client.put(
        f"/api/sites/{site_id}", headers=auth_header, json={"name": "Филиал 2 (изменён)"}
    )
    assert resp.status_code in (200, 201)
    assert resp.json()["name"] == "Филиал 2 (изменён)"

    # delete
    resp = seeded_client.delete(f"/api/sites/{site_id}", headers=auth_header)
    assert resp.status_code in (200, 201, 204)


def test_admin_can_switch_site_via_query(seeded_client, auth_header, session_factory):
    """Admin/manager may pass site_id to list another site's data; a
    storekeeper's site_id query is ignored (scoped to own site)."""
    from sqlalchemy import select
    from app.models.site import Site

    # Create a second site and a product in it
    async def _seed():
        async with session_factory() as s:
            site2 = Site(name="Второй объект", code="SEC", is_active=True)
            s.add(site2)
            await s.flush()
            site1 = (await s.execute(select(Site).where(Site.code == "TEST"))).scalar_one()
            p2 = (await _make_product(s, site2.id, "ТоварB"))
            p1 = (await _make_product(s, site1.id, "ТоварA"))
            await s.commit()
            return site1.id, site2.id, p1, p2
    import asyncio
    site1_id, site2_id, p1, p2 = asyncio.get_event_loop().run_until_complete(_seed())

    # Admin lists with site_id=site2 -> should see only ТоварB
    resp = seeded_client.get(f"/api/products/?site_id={site2_id}", headers=auth_header)
    assert resp.status_code in (200, 201), resp.text
    names = {p["name"] for p in resp.json()}
    assert "ТоварB" in names
    assert "ТоварA" not in names

    # Without site_id -> admin's own site (site1) -> ТоварA
    resp = seeded_client.get("/api/products/", headers=auth_header)
    names = {p["name"] for p in resp.json()}
    assert "ТоварA" in names


def test_storekeeper_site_query_ignored(seeded_client, auth_header, session_factory):
    """A storekeeper's site_id query is ignored; they only see their own site."""
    from sqlalchemy import select
    from app.models.site import Site
    from app.models.product import Product

    async def _seed():
        async with session_factory() as s:
            site2 = Site(name="Третий объект", code="THD", is_active=True)
            s.add(site2)
            await s.flush()
            site1 = (await s.execute(select(Site).where(Site.code == "TEST"))).scalar_one()
            p1 = Product(site_id=site1.id, name="ТоварX", unit="кг", is_active=True)
            p2 = Product(site_id=site2.id, name="ТоварY", unit="кг", is_active=True)
            s.add_all([p1, p2])
            await s.commit()
            return site1.id, site2.id
    import asyncio
    site1_id, site2_id = asyncio.get_event_loop().run_until_complete(_seed())

    # Create a storekeeper bound to site1
    _create_user_via_api(seeded_client, auth_header, "klad2", "storekeeper")
    h = {"Authorization": f"Bearer {_token_for(seeded_client, 'klad2')}"}
    # Even if they try site_id=site2, they must only see their own site (ТоварX)
    resp = seeded_client.get(f"/api/products/?site_id={site2_id}", headers=h)
    assert resp.status_code in (200, 201), resp.text
    names = {p["name"] for p in resp.json()}
    assert "ТоварX" in names
    assert "ТоварY" not in names


async def _make_product(session, site_id, name):
    from app.models.product import Product
    p = Product(site_id=site_id, name=name, unit="кг", is_active=True)
    session.add(p)
    await session.flush()
    return p.id
