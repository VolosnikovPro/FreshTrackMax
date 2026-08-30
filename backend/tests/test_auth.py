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


def test_role_isolation_manager_cannot_read_admin_summary(seeded_client, auth_header):
    """UPP does not access the administrative dashboard endpoint."""
    _create_user_via_api(seeded_client, auth_header, "mgr", "manager")
    h = {"Authorization": f"Bearer {_token_for(seeded_client, 'mgr')}"}
    resp = seeded_client.get("/api/admin/summary", headers=h)
    assert resp.status_code == 403


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


def test_storekeeper_site_query_is_rejected(seeded_client, auth_header, session_factory):
    """A storekeeper cannot even request another site's context."""
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
    assert resp.status_code == 403, resp.text


def test_lower_role_is_forbidden_from_requesting_another_site(seeded_client, auth_header, session_factory):
    """A caller below administrator must receive 403, never a silently scoped result."""
    async def _seed():
        async with session_factory() as s:
            site2 = Site(name="Чужой объект", code="OTHER", is_active=True)
            s.add(site2)
            await s.commit()
            return site2.id

    other_site_id = asyncio.get_event_loop().run_until_complete(_seed())
    _create_user_via_api(seeded_client, auth_header, "klad403", "storekeeper")
    header = {"Authorization": f"Bearer {_token_for(seeded_client, 'klad403')}"}

    response = seeded_client.get(f"/api/products/?site_id={other_site_id}", headers=header)

    assert response.status_code == 403, response.text


def test_manager_cannot_switch_site(seeded_client, auth_header, session_factory):
    """UPP (manager) is bound to its own site despite a supplied site_id."""
    async def _seed():
        async with session_factory() as s:
            site2 = Site(name="Другой объект УПП", code="MGR2", is_active=True)
            s.add(site2)
            await s.commit()
            return site2.id

    other_site_id = asyncio.get_event_loop().run_until_complete(_seed())
    _create_user_via_api(seeded_client, auth_header, "mgr403", "manager")
    header = {"Authorization": f"Bearer {_token_for(seeded_client, 'mgr403')}"}

    response = seeded_client.get(f"/api/products/?site_id={other_site_id}", headers=header)

    assert response.status_code == 403, response.text


def test_admin_cannot_select_inactive_site(seeded_client, auth_header, session_factory):
    """Administrative switching still rejects an inactive object."""
    async def _seed():
        async with session_factory() as s:
            site = Site(name="Отключенный объект", code="OFF", is_active=False)
            s.add(site)
            await s.commit()
            return site.id

    inactive_site_id = asyncio.get_event_loop().run_until_complete(_seed())
    response = seeded_client.get(f"/api/products/?site_id={inactive_site_id}", headers=auth_header)

    assert response.status_code == 409, response.text


def test_existing_product_cannot_be_changed_or_deleted(seeded_client, auth_header):
    """Product master data is immutable after creation."""
    created = seeded_client.post(
        "/api/products/", headers=auth_header,
        json={"name": "Неизменяемый", "unit": "кг"},
    )
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]

    updated = seeded_client.put(
        f"/api/products/{product_id}", headers=auth_header, json={"name": "Новое имя"},
    )
    deleted = seeded_client.delete(f"/api/products/{product_id}", headers=auth_header)

    assert updated.status_code == 409, updated.text
    assert deleted.status_code == 409, deleted.text
    current = seeded_client.get(f"/api/products/{product_id}", headers=auth_header)
    assert current.json()["name"] == "Неизменяемый"


def test_expiring_endpoints_honor_admin_selected_site(seeded_client, auth_header, session_factory):
    """Dashboard expiry lists must use the site selected by an admin."""
    from app.models.batch import Batch
    from app.models.product import Product
    from app.models.site import Site
    from datetime import date, timedelta

    async def _seed():
        async with session_factory() as session:
            source_product = (await session.execute(select(Product).where(Product.name == "Молоко"))).scalar_one_or_none()
            if source_product is None:
                source_product = Product(site_id=1, name="Молоко", unit="кг", is_active=True)
                session.add(source_product)
                await session.flush()
            other = Site(name="Объект сроков", code="EXP", is_active=True)
            session.add(other)
            await session.flush()
            other_product = Product(site_id=other.id, name="Только другой объект", unit="кг", is_active=True)
            session.add(other_product)
            await session.flush()
            session.add(Batch(site_id=other.id, product_id=other_product.id, quantity=1, unit="кг", expiry_date=date.today() + timedelta(days=2)))
            await session.commit()
            return other.id

    import asyncio
    selected_site_id = asyncio.get_event_loop().run_until_complete(_seed())

    response = seeded_client.get(f"/api/batches/expiring/urgent?site_id={selected_site_id}", headers=auth_header)

    assert response.status_code == 200, response.text
    assert [row["product_name"] for row in response.json()] == ["Только другой объект"]


def test_storekeeper_cannot_create_manual_consumption(seeded_client, auth_header, make_future_date):
    """Storekeepers write off stock only through an imported consumption file."""
    _create_user_via_api(seeded_client, auth_header, "klad-manual", "storekeeper")
    header = {"Authorization": f"Bearer {_token_for(seeded_client, 'klad-manual')}"}
    product = seeded_client.post("/api/products/", headers=header, json={"name": "Расход только файлом", "unit": "кг"}).json()
    seeded_client.post("/api/batches/", headers=header, json={"product_id": product["id"], "quantity": 3, "unit": "кг", "expiry_date": make_future_date(10)})

    response = seeded_client.post("/api/consumption/", headers=header, json={"product_id": product["id"], "quantity_used": 1, "unit": "кг", "date": make_future_date(0)})

    assert response.status_code == 403, response.text


async def _make_product(session, site_id, name):
    from app.models.product import Product
    p = Product(site_id=site_id, name=name, unit="кг", is_active=True)
    session.add(p)
    await session.flush()
    return p.id
